/*
 * netconsblaster: A test excerciser for netconsd and libncrx
 *
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#include <stdlib.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <pthread.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/ip6.h>
#include <netinet/udp.h>

#define fatal(...) \
do { \
	printf(__VA_ARGS__); \
	abort(); \
} while (0)

#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "Sorry, IPv6 address permutation code assumes a little-endian CPU"
#endif

/*
 * The canonical "fuck it" RNG: just use the low bits of the TSC
 */
static unsigned long rand64(void)
{
	unsigned long ret;
	asm volatile ("rdtsc" : "=a" (ret) :: "rdx");
	return ret;
}

static unsigned long now_epoch_ms(void)
{
	struct timespec t;

	clock_gettime(CLOCK_MONOTONIC, &t);
	return t.tv_sec * 1000 + t.tv_nsec / 1000000L;
}

static int ones_complement_sum(unsigned short *data, int len, int sum)
{
	unsigned int tmp;
	int i;

	for (i = 0; i < len / 2; i++) {
		tmp = ntohs(data[i]);

		/*
		 * Kill -0
		 */
		if (tmp == 65535)
			tmp = 0;

		sum += tmp;
		if (sum >= 65536) {
			sum &= 65535;
			sum++;
		}
	}

	if (len & 1)
		fatal("Calvin is lazy\n");

	return sum;
}

/*
 * From RFC768: "Checksum is the 16-bit one's complement of the one's
 * complement sum of a pseudo header of information from the IP header, the UDP
 * header, and the data, padded with zero octets at the end (if necessary) to
 * make a multiple of two octets."
 *
 * See RFC2460 section 8.1 for definition of pseudoheader for IPv6.
 *
 * In case you're wondering why I bothered with this: "Unlike IPv4, when UDP
 * packets are originated by an IPv6 node, the UDP checksum is NOT optional.
 * IPv6 receivers MUST discard packets containing a zero checksum."
 *
 * @addrs: Pointer to the begnning of the src/dst addresses in the ipv6hdr
 * @udppkt: Pointer to the udphdr
 * @len: Length of the udphdr and its payload
 */
static int udp_csum(void *addrptr, void *udppkt, int len)
{
	unsigned int sum = 0;
	unsigned short *addrs = addrptr;
	unsigned short pseudohdr[4] = {0, htons(len), 0, htons(IPPROTO_UDP)};

	sum = ones_complement_sum(addrs, 32, 0);
	sum = ones_complement_sum(pseudohdr, 8, sum);
	sum = ones_complement_sum(udppkt, len, sum);
	sum = ~sum;

	/*
	 * From RFC768: "If the computed checksum is zero, it is transmitted as
	 * all ones. An all zero transmitted checksum value means that the
	 * transmitter generated no checksum"
	 */
	if (sum == 0)
		sum = 65535;

	return sum;
}

/*
 * Length of payload to send with every netconsole packet
 */
#define NETCONSLEN 64

/*
 * Layout of a raw netconsole packet
 */
struct netcons_packet {
	struct ip6_hdr l3;
	struct udphdr l4;
	char payload[];
} __attribute__((packed));

/*
 * Metadata for extended netconsole packets
 */
struct netcons_metadata {
	uint64_t seq;
	uint64_t ts;
	uint8_t cont;
	uint8_t lvl;
};

static void bump_metadata(struct netcons_metadata *md)
{
	md->seq++;
	md->ts += 1337;
}

/*
 * Filler text for packets. Wallow in my patriotism.
 */
static const char *filler = "When, in the course of human events, it becomes "
	"necessary for one people to dissolve the political bonds which have "
	"connected them with another, and to assume among the powers of the "
	"earth, the separate and equal station to which the laws of nature and "
	"of nature's God entitle them, a decent respect to the opinions of "
	"mankind requires that they should declare the causes which impel them "
	"to the separation.";

/*
 * Numeric to symbol for the CONT flag
 */
static const char *contflag(int cont)
{
	switch (cont) {
	case 0:
		/*
		 * No CONT flag present
		 */
		return "-";
	case 1:
		/*
		 * CONT_START
		 */
		return "c";
	case 2:
		/*
		 * CONT
		 */
		return "+";
	default:
		fatal("CONT value %d invalid?\n", cont);
	};
}

static void make_packet(struct netcons_packet *pkt, const struct in6_addr *src,
		const struct in6_addr *dst, const struct netcons_metadata *md)
{
	const int len = NETCONSLEN;

	memset(pkt, 0, sizeof(pkt->l3) + sizeof(pkt->l4));

	memcpy(&pkt->l3.ip6_src, src, sizeof(*src));
	memcpy(&pkt->l3.ip6_dst, dst, sizeof(*dst));
	pkt->l3.ip6_vfc |= (6 << 4);
	pkt->l3.ip6_nxt = IPPROTO_UDP;
	pkt->l3.ip6_plen = htons(sizeof(pkt->l4) + len);
	pkt->l3.ip6_hlim = 64;

	snprintf(pkt->payload, len - 1, "%d,%lu,%lu,%s;%s", md->lvl, md->seq,
			md->ts, contflag(md->cont), filler);
	pkt->payload[len - 1] = '\n';

	pkt->l4.source = htons(6666);
	pkt->l4.dest = htons(1514);
	pkt->l4.len = htons(sizeof(pkt->l4) + len);
	pkt->l4.check = htons(udp_csum(&pkt->l3.ip6_src, &pkt->l4,
			sizeof(pkt->l4) + len));
}

static int write_packet(int sockfd, struct netcons_packet *pkt)
{
	const int len = sizeof(pkt->l3) + sizeof(pkt->l4) + NETCONSLEN;
	struct sockaddr_in6 bogus = {
		.sin6_family = AF_INET6,
	};

	memcpy(&bogus.sin6_addr, &pkt->l3.ip6_dst, sizeof(pkt->l3.ip6_dst));
	return sendto(sockfd, pkt, len, 0, &bogus, sizeof(bogus)) != len;
}

static int get_raw_socket(void)
{
	int fd;

	fd = socket(AF_INET6, SOCK_RAW, IPPROTO_RAW);
	if (fd == -1)
		fatal("Couldn't get raw socket: %m\n");

	return fd;
}

static struct netcons_packet *alloc_packet(void)
{
	struct netcons_packet *ret;

	ret = malloc(sizeof(struct netcons_packet) + NETCONSLEN);
	if (!ret)
		fatal("ENOMEM allocating packet\n");

	return ret;
}

static struct netcons_metadata *alloc_metadata_array(int bits)
{
	struct netcons_metadata *ret;

	ret = calloc(1 << bits, sizeof(*ret));
	if (!ret)
		fatal("ENOMEM allocating metadata\n");

	return ret;
}

static unsigned long mask_long(unsigned long val, int bits)
{
	unsigned long mask = (1UL << bits) - 1;
	return val & mask;
}

static unsigned long permute_addr(struct in6_addr *addr, int bits)
{
	unsigned long *punned;

	punned = (unsigned long *)&addr->s6_addr[16 - sizeof(unsigned long)];
	*punned ^= mask_long(rand64(), bits);
	return mask_long(*punned, bits);
}

struct blaster_state {
	pthread_t id;
	int nr;

	struct in6_addr dst;
	struct in6_addr src;
	long blastcount;
	int *stopptr;
	int bits;
};

static void *blaster_thread(void *arg)
{
	const struct blaster_state *s = arg;
	struct netcons_metadata *mdarr;
	struct netcons_packet *pkt;
	struct in6_addr src;
	long idx, count = 0;
	int fd;

	fd = get_raw_socket();
	pkt = alloc_packet();
	mdarr = alloc_metadata_array(s->bits);
	memcpy(&src, &s->src, sizeof(src));

	while (!*s->stopptr) {
		idx = permute_addr(&src, s->bits);
		make_packet(pkt, &src, &s->dst, &mdarr[idx]);
		bump_metadata(&mdarr[idx]);

		if (!write_packet(fd, pkt))
			count++;

		if (s->blastcount && count == s->blastcount)
			break;
	}

	return (void*)count;
}

static struct params {
	int srcaddr_order;
	int thread_order;
	struct in6_addr src;
	struct in6_addr dst;
	long blastcount;

	int stop_blasting;
} params;

static void parse_arguments(int argc, char **argv, struct params *p)
{
	int i;

	/*
	 * Defaults
	 */
	p->srcaddr_order = 16;
	p->thread_order = 0;
	memcpy(&p->src, &in6addr_loopback, sizeof(in6addr_loopback));
	memcpy(&p->dst, &in6addr_loopback, sizeof(in6addr_loopback));
	p->blastcount = 0;

	p->stop_blasting = 0;

	while ((i = getopt(argc, argv, "o:s:d:t:n:")) != -1) {
		switch(i) {
		case 'o':
			/*
			 * Controls the number of bits to randomly flip in the
			 * actual IPv6 address of this machine. So the program
			 * will effectively simulate 2^N clients.
			 */
			p->srcaddr_order = atoi(optarg);
			if (p->srcaddr_order > LONG_BIT - 8)
				fatal("Source address order too large\n");
			break;
		case 't':
			/*
			 * Split the work among 2^N worker threads.
			 */
			p->thread_order = atoi(optarg);
			if (p->thread_order > 8)
				fatal("Largest supported thread order is 8\n");
			break;
		case 's':
			/*
			 * Source address to permute the low N bits of.
			 */
			if (inet_pton(AF_INET6, optarg, &p->src) != 1)
				fatal("Bad src '%s': %m\n", optarg);
			break;
		case 'd':
			/*
			 * Destination address for all generated packets.
			 */
			if (inet_pton(AF_INET6, optarg, &p->dst) != 1)
				fatal("Bad dst '%s': %m\n", optarg);
			break;
		case 'n':
			/*
			 * Write N packets from each worker thread and exit.
			 */
			p->blastcount = atol(optarg);
			break;
		default:
			fatal("Invalid command line parameters\n");
		}
	}
}

static void stop_signal(int signum)
{
	params.stop_blasting = 1;
}

int main(int argc, char **argv)
{
	int i, nr_threads, srcaddr_per_thread;
	unsigned long tmp, count, start, finish;
	struct blaster_state *threadstates, *cur;
	struct sigaction stopper = {
		.sa_handler = stop_signal,
	};

	parse_arguments(argc, argv, &params);

	nr_threads = 1 << params.thread_order;
	srcaddr_per_thread = params.srcaddr_order - params.thread_order;

	if (srcaddr_per_thread <= 0)
		fatal("More thread bits than srcaddr bits\n");

	threadstates = calloc(nr_threads, sizeof(*threadstates));
	if (!threadstates)
		fatal("ENOMEM allocating state for threads\n");

	sigaction(SIGINT, &stopper, NULL);

	for (i = 0; i < nr_threads; i++) {
		cur = &threadstates[i];

		memcpy(&cur->src, &params.src, sizeof(cur->src));
		memcpy(&cur->dst, &params.dst, sizeof(cur->dst));
		cur->blastcount = params.blastcount;
		cur->stopptr = &params.stop_blasting;
		cur->bits = srcaddr_per_thread;

		cur->src.s6_addr[15] = (unsigned char)i;
		cur->nr = i;

		if (pthread_create(&cur->id, NULL, blaster_thread, cur))
			fatal("Thread %d/%d failed: %m\n", i, nr_threads);
	}

	count = 0;

	start = now_epoch_ms();
	for (i = 0; i < nr_threads; i++) {
		pthread_join(threadstates[i].id, (void**)&tmp);
		count += tmp;
	}
	finish = now_epoch_ms();

	printf("Wrote %lu packets (%lu pkts/sec)\n", count,
			count / (finish - start) * 1000UL);
	return 0;
}
