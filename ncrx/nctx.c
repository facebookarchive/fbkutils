/*
 * nctx - extended netconsole sender
 *
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <time.h>
#include <poll.h>
#include <ctype.h>
#include <errno.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/udp.h>

#include "ncrx.h"

/* in msecs */
#define ACK_TIMEOUT		10000
#define EMG_TX_MAX_INTV		1000
#define EMG_TX_MIN_INTV		100

union sockaddr_in46 {
	struct sockaddr		addr;
	struct sockaddr_in6	in6;
	struct sockaddr_in	in4;
};

struct kmsg_slot {
	char			*msg;
	uint64_t		ts;
};

struct kmsg_ring {
	int			head;
	int			tail;
	int			nr_slots;
	uint64_t		head_seq;
	union sockaddr_in46	raddr;
	int			raddr_len;
	int			emg_tx_intv;
	uint64_t		emg_tx_seq;
	uint64_t		emg_tx_ts;
	struct kmsg_slot	*slots;
};

/* relative time in msecs */
static uint64_t current_msec(void)
{
	struct timespec ts;

	if (clock_gettime(CLOCK_MONOTONIC, &ts)) {
		perror("clock_gettime");
		exit(1);
	}
	return ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static int kmsg_ring_init(struct kmsg_ring *ring, int nr_slots)
{
	memset(ring, 0, sizeof(*ring));

	ring->slots = malloc(sizeof(ring->slots[0]) * nr_slots);
	if (!ring->slots)
		return -1;

	ring->nr_slots = nr_slots;
	return 0;
}

/* advance @ring's head by one, if head catches up with tail, clip it */
static void kmsg_ring_advance(struct kmsg_ring *ring)
{
	struct kmsg_slot *slot;

	ring->head_seq++;
	ring->head = (ring->head + 1) % ring->nr_slots;
	slot = &ring->slots[ring->head];

	if (ring->tail == ring->head) {
		free(slot->msg);
		memset(slot, 0, sizeof(*slot));
		ring->tail = (ring->tail + 1) % ring->nr_slots;
	}
}

/* fill @ring with kmsgs from @devkmsg, returns 0 on success, -1 on failure */
static int kmsg_ring_fill(struct kmsg_ring *ring, int devkmsg)
{
	char buf[NCRX_LINE_MAX];
	struct kmsg_slot *slot;
	int level;
	uint64_t seq;
	ssize_t len;

next_line:
	do {
		len = read(devkmsg, buf, sizeof(buf) - 1);
		/*
		 * EPIPE indicates skipped messages.  kmsgs are always
		 * stored according to their sequence numbers, so we don't
		 * need to do anything special on EPIPE.  Keep reading.
		 */
	} while (len < 0 && errno == EPIPE);

	if (len < 0) {
		if (errno == EAGAIN)
			return 0;
		return -1;
	}

	/* read seq and see if it makes sense */
	buf[len] = '\0';
	if (sscanf(buf, "%d,%"SCNu64",", &level, &seq) != 2 ||
	    seq < ring->head_seq) {
		fprintf(stderr, "Warning: malformed kmsg \"%s\"\n", buf);
		goto next_line;
	}

	/* wind ring till head is at the right slot and store */
	while (ring->head_seq < seq)
		kmsg_ring_advance(ring);

	slot = &ring->slots[ring->head];
	slot->msg = strdup(buf);
	if (!slot->msg)
		return -1;

	slot->ts = current_msec();
	kmsg_ring_advance(ring);
	goto next_line;
}

/* sequence number of the oldest occupied slot in @ring */
static uint64_t kmsg_ring_tail_seq(struct kmsg_ring *ring)
{
	int nr;

	nr = ring->head - ring->tail;
	if (nr < 0)
		nr += ring->nr_slots;
	return ring->head_seq - nr;
}

/* peek kmsg matching @seq, NULL if not found */
static char *kmsg_ring_peek(struct kmsg_ring *ring, uint64_t seq)
{
	int idx;

	if (seq < kmsg_ring_tail_seq(ring) || seq >= ring->head_seq)
		return NULL;

	idx = ring->head - (int)(ring->head_seq - seq);
	if (idx < 0)
		idx += ring->nr_slots;

	return ring->slots[idx].msg;
}

/* free slots upto @upto_seq, tail_seq is @upto_seq + 1 afterwards */
static void kmsg_ring_consume(struct kmsg_ring *ring, uint64_t upto_seq)
{
	uint64_t tail_seq = kmsg_ring_tail_seq(ring);
	int tail = ring->tail;

	if (!ring->head_seq || upto_seq < tail_seq)
		return;

	if (upto_seq >= ring->head_seq)
		upto_seq = ring->head_seq - 1;

	while (tail_seq <= upto_seq) {
		struct kmsg_slot *slot = &ring->slots[ring->head];

		free(slot->msg);
		memset(slot, 0, sizeof(*slot));
		tail_seq++;
		tail = (tail + 1) % ring->nr_slots;

		/* made progress, reset emergency tx */
		ring->emg_tx_intv = 0;
	}

	ring->tail = tail;
}

/*
 * Send @msg to @addr via @sock.  If @msg is too long, split into
 * NCRX_PKT_MAX byte chunks with ncfrag header added.  If @is_emg_tx is
 * set, add ncemg header.
 */
static void send_kmsg(int sock, char *msg, int is_emg_tx,
		      struct sockaddr *addr, int addr_len)
{
	char buf[NCRX_PKT_MAX + 1];
	const int max_extra_len = sizeof(",ncemg=1,ncfrag=0000/0000");
	const char *header, *body;
	int msg_len = strlen(msg);
	int header_len = msg_len, body_len = 0;
	int chunk_len, nr_chunks, i;

	if (!is_emg_tx && msg_len <= NCRX_PKT_MAX) {
		sendto(sock, msg, msg_len, 0, addr, addr_len);
		return;
	}

	/* need to insert extra header fields, detect header and body */
	header = msg;
	body = memchr(msg, ';', msg_len);
	if (body) {
		header_len = body - header;
		body_len = msg_len - header_len - 1;
		body++;
	}

	chunk_len = NCRX_PKT_MAX - header_len - max_extra_len;
	if (chunk_len <= 0) {
		fprintf(stderr, "Error: invalid chunk_len %d in send_kmsg()\n",
			chunk_len);
		return;
	}

	/*
	 * Transfer possibly multiple chunks with extra header fields.
	 *
	 * For emergency transfers due to missing acks, add "emg=1".
	 *
	 * If @msg needs to be split to fit NCRX_PKT_MAX, add
	 * "ncfrag=<byte-offset>/<total-bytes>" to identify each chunk.
	 */
	memcpy(buf, header, header_len);
	nr_chunks = (body_len + chunk_len - 1) / chunk_len;

	for (i = 0; i < nr_chunks; i++) {
		int offset = i * chunk_len;
		int this_header = header_len;
		int this_chunk;

		this_chunk = body_len - offset;
		if (this_chunk > chunk_len)
			this_chunk = chunk_len;

		if (is_emg_tx && this_header < sizeof(buf))
			this_header += snprintf(buf + this_header,
						sizeof(buf) - this_header,
						",ncemg=1");
		if (nr_chunks > 1 && this_header < sizeof(buf))
			this_header += snprintf(buf + this_header,
						sizeof(buf) - this_header,
						",ncfrag=%d/%d",
						offset, body_len);
		if (this_header < sizeof(buf))
			this_header += snprintf(buf + this_header,
						sizeof(buf) - this_header, ";");

		if (this_header + chunk_len > NCRX_PKT_MAX) {
			fprintf(stderr, "Error: this_header %d is too large for chunk_len %d in send_kmsg()\n",
				this_header, chunk_len);
			return;
		}

		memcpy(buf + this_header, body, this_chunk);

		sendto(sock, buf, this_header + this_chunk, 0, addr, addr_len);

		body += this_chunk;
	}
}

/* rx and handle response packets from @sock, returns 0 on success, -1 on err */
static int kmsg_ring_process_resps(struct kmsg_ring *ring, int sock)
{
	char rx_buf[NCRX_PKT_MAX + 1];
	union sockaddr_in46 raddr;
	struct iovec iov = { .iov_base = rx_buf, .iov_len = NCRX_PKT_MAX };
	struct msghdr msgh = { .msg_name = &raddr.addr, .msg_iov = &iov,
			       .msg_iovlen = 1 };
	ssize_t len;
	char *pos, *tok;
	uint64_t seq;

next_packet:
	msgh.msg_namelen = sizeof(raddr);
	len = recvmsg(sock, &msgh, MSG_DONTWAIT);
	if (len < 0) {
		if (errno == EAGAIN)
			return 0;
		return -1;
	}

	rx_buf[len] = '\0';
	pos = rx_buf;
	tok = strsep(&pos, " ");

	/* "ncrx" header */
	if (strncmp(tok, "ncrx", 4)) {
		char addr_str[INET6_ADDRSTRLEN];

		if (raddr.addr.sa_family == AF_INET6)
			inet_ntop(AF_INET6, &raddr.in6.sin6_addr,
				  addr_str, sizeof(addr_str));
		else
			inet_ntop(AF_INET, &raddr.in4.sin_addr,
				  addr_str, sizeof(addr_str));

		fprintf(stderr, "Warning: malformed packet from [%s]:%u\n",
			addr_str, ntohs(raddr.in4.sin_port));
		goto next_packet;
	}
	tok += 4;

	/* <ack-seq> */
	if (sscanf(tok, "%"SCNu64, &seq))
		kmsg_ring_consume(ring, seq);

	/* <missing-seq>... */
	while ((tok = strsep(&pos, " "))) {
		if (sscanf(tok, "%"SCNu64, &seq)) {
			char *msg = kmsg_ring_peek(ring, seq);
			if (msg)
				send_kmsg(sock, msg, 0,
					  &raddr.addr, msgh.msg_namelen);
		}
	}

	/* stash remote address for emergency tx */
	ring->raddr = raddr;
	ring->raddr_len = msgh.msg_namelen;

	goto next_packet;
}

/*
 * Perform emergency tx if necessary.  Must be called after @ring is filled
 * and responses are processed.  Returns the duration in msecs after which
 * this function should be invoked again.  If -1, timeout isn't necessary.
 */
static int kmsg_ring_emg_tx(struct kmsg_ring *ring, int sock)
{
	struct kmsg_slot *slot = &ring->slots[ring->tail];
	uint64_t target, now;
	uint64_t tail_seq;
	char *msg;

	/* if @ring is empty or remote site is not established, nothing to do */
	if (ring->head == ring->tail || !ring->raddr_len) {
		ring->emg_tx_intv = 0;
		return -1;
	}

	/* calculate the next deadline, if in the future, return the diff */
	if (!ring->emg_tx_intv)
		target = slot->ts + ACK_TIMEOUT;
	else
		target = ring->emg_tx_ts + ring->emg_tx_intv;

	now = current_msec();

	if (target > now)
		return target - now;

	tail_seq = kmsg_ring_tail_seq(ring);

	if (!ring->emg_tx_intv) {
		/* new emg tx session */
		ring->emg_tx_intv = EMG_TX_MIN_INTV;
		ring->emg_tx_seq = tail_seq;
	} else if (ring->emg_tx_seq < ring->head_seq) {
		/* in the middle of emg tx session */
		ring->emg_tx_seq++;
		if (ring->emg_tx_seq < tail_seq)
			ring->emg_tx_seq = tail_seq;
	} else {
		/* finished one session, increase intv and repeat */
		ring->emg_tx_intv *= 2;
		if (ring->emg_tx_intv < EMG_TX_MAX_INTV)
			ring->emg_tx_intv = EMG_TX_MAX_INTV;
		ring->emg_tx_seq = tail_seq;
	}

	msg = kmsg_ring_peek(ring, ring->emg_tx_seq);
	if (msg)
		send_kmsg(sock, msg, 1, &ring->raddr.addr, ring->raddr_len);

	ring->emg_tx_ts = now;

	return ring->emg_tx_intv;
}

static void usage_err(const char *err)
{
	if (err)
		fprintf(stderr, "Error: %s\n", err);
	fprintf(stderr, "Usage: nctx [-n nr_slots] [-k devkmsg_path] ip port\n");
	exit(1);
}

int main(int argc, char **argv)
{
	union sockaddr_in46 laddr = { };
	struct pollfd pfds[2] = { };
	struct kmsg_ring kmsg_ring;
	const char *devkmsg_path = "/dev/kmsg";
	int nr_slots = NCRX_DFL_NR_SLOTS;
	int sleep_dur = -1;
	int opt, port, sock, devkmsg;
	socklen_t addrlen;

	while ((opt = getopt(argc, argv, "n:k:h?")) != -1) {
		switch (opt) {
		case 'n':
			nr_slots = atoi(optarg);
			if (nr_slots <= 0)
				usage_err("nr_slots must be a positive number");
			break;
		case 'k':
			devkmsg_path = optarg;
			break;
		default:
			usage_err(NULL);
		}
	}

	if (optind + 2 != argc)
		usage_err(NULL);

	if (inet_pton(AF_INET6, argv[optind], &laddr.in6.sin6_addr)) {
		laddr.addr.sa_family = AF_INET6;
		addrlen = sizeof(laddr.in6);
	} else if (inet_pton(AF_INET, argv[optind], &laddr.in4.sin_addr)) {
		laddr.addr.sa_family = AF_INET;
		addrlen = sizeof(laddr.in4);
	} else {
		usage_err("invalid IP address");
	}

	port = atoi(argv[optind + 1]);
	if (port <= 0 || port > 65535)
		usage_err("invalid port number");

	laddr.in4.sin_port = htons(port);

	sock = socket(laddr.addr.sa_family, SOCK_DGRAM, 0);
	if (sock < 0) {
		perror("socket");
		return 1;
	}

	if (bind(sock, &laddr.addr, addrlen)) {
		perror("bind");
		return 1;
	}

	devkmsg = open(devkmsg_path, O_RDONLY | O_NONBLOCK);
	if (devkmsg < 0) {
		perror("open");
		return 1;
	}

	if (kmsg_ring_init(&kmsg_ring, nr_slots)) {
		perror("kmsg_ring_init");
		return 1;
	}

	pfds[0].events = POLLIN;
	pfds[1].events = POLLIN;
	pfds[0].fd = devkmsg;
	pfds[1].fd = sock;

	while (poll(pfds, 2, sleep_dur) >= 0) {
		if (kmsg_ring_fill(&kmsg_ring, devkmsg)) {
			perror("kmsg_ring_fill");
			return 1;
		}

		if (kmsg_ring_process_resps(&kmsg_ring, sock)) {
			perror("kmsg_ring_process_resps");
			return 1;
		}

		sleep_dur = kmsg_ring_emg_tx(&kmsg_ring, sock);
	}
	perror("poll");
	return 1;
}
