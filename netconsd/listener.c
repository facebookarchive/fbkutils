/*
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include <unistd.h>
#include <errno.h>
#include <signal.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>

#include "include/common.h"
#include "include/msgbuf-struct.h"
#include "include/threads.h"
#include "include/listener.h"

static void handle_listen_error(int err)
{
	switch(err) {
	case EINTR:
		/*
		 * The fact that we got an error return means that recvmmsg()
		 * hadn't actually done anything, so we can just loop back over
		 * the call no problem.
		 */
		return;
	case 0:
		fatal("Unexpected EOF from recvmmsg()\n");
	default:
		fatal("Unexpected listen error: %m (-%d)\n", errno);
	}
}

static struct msgbuf *msgbuf_from_iovec(struct iovec *vecptr)
{
	return container_of(vecptr, struct msgbuf, iovec);
}

static unsigned long hash_srcaddr(struct in6_addr *addr)
{
	uint32_t *addrptr = (uint32_t *)addr;

	return jhash2(addrptr, sizeof(*addr) / sizeof(*addrptr), LISTEN_SEED);
}

static void prequeue_msgbuf(struct ncrx_listener *listener, struct msgbuf *buf)
{
	struct ncrx_prequeue *prequeue;
	unsigned long hash;

	hash = hash_srcaddr(&buf->src.sin6_addr);
	prequeue = &listener->prequeues[hash % listener->nr_workers];

	if (prequeue->queue_head)
		prequeue->queue_tail->next = buf;
	else
		prequeue->queue_head = buf;

	prequeue->queue_tail = buf;
	prequeue->count++;
}

static void reinit_mmsghdr_vec(struct mmsghdr *vec, int nr, int rcvbufsz)
{
	struct msgbuf *cur;
	int i;

	memset(vec, 0, sizeof(*vec) * nr);
	for (i = 0; i < nr; i++) {
		cur = malloc(sizeof(*cur) + rcvbufsz);
		if (!cur)
			fatal("-ENOMEM after %d/%d rcvbufs\n", i, nr);

		memset(cur, 0, sizeof(*cur));
		cur->buf[rcvbufsz - 1] = '\0';

		cur->iovec.iov_base = &cur->buf;
		cur->iovec.iov_len = rcvbufsz - 1;

		vec[i].msg_hdr.msg_iov = &cur->iovec;
		vec[i].msg_hdr.msg_iovlen = 1;

		vec[i].msg_hdr.msg_name = &cur->src;
		vec[i].msg_hdr.msg_namelen = sizeof(cur->src);
	}
}

static struct mmsghdr *alloc_mmsghdr_vec(int nr, int rcvbufsz)
{
	struct mmsghdr *mmsgvec;

	mmsgvec = malloc(sizeof(*mmsgvec) * nr);
	if (!mmsgvec)
		fatal("Unable to allocate mmsghdr array\n");

	reinit_mmsghdr_vec(mmsgvec, nr, rcvbufsz);
	return mmsgvec;
}

static void free_mmsghdr_vec(struct mmsghdr *vec, int nr)
{
	struct msgbuf *cur;
	int i;

	for (i = 0; i < nr; i++) {
		cur = msgbuf_from_iovec(vec[i].msg_hdr.msg_iov);
		free(cur);
	}

	free(vec);
}

static int get_listen_socket(struct sockaddr_in6 *bindaddr)
{
	int fd, ret, optval = 1;

	fd = socket(AF_INET6, SOCK_DGRAM, 0);
	if (fd == -1)
		fatal("Couldn't get socket: %m\n");

	ret = setsockopt(fd, SOL_SOCKET, SO_REUSEPORT, &optval, sizeof(optval));
	if (ret == -1)
		fatal("Couldn't set SO_REUSEPORT on socket: %m\n");

	ret = bind(fd, bindaddr, sizeof(*bindaddr));
	if (ret == -1)
		fatal("Couldn't bind: %m\n");

	return fd;
}

void *udp_listener_thread(void *arg)
{
	int fd, nr_recv, i;
	uint64_t now;
	struct ncrx_listener *us = arg;
	struct mmsghdr *vec;
	struct msgbuf *cur;

	fd = get_listen_socket(us->address);
	vec = alloc_mmsghdr_vec(us->batch, RCVBUF_SIZE);

	while (!us->stop) {
		nr_recv = recvmmsg(fd, vec, us->batch, MSG_WAITFORONE, NULL);
		if (nr_recv <= 0) {
			handle_listen_error(errno);
			continue;
		}

		debug("recvmmsg() got %d packets\n", nr_recv);

		now = now_real_ms();
		for (i = 0; i < nr_recv; i++) {
			cur = msgbuf_from_iovec(vec[i].msg_hdr.msg_iov);

			cur->rcv_flags = vec[i].msg_hdr.msg_flags;
			cur->rcv_bytes = vec[i].msg_len;
			cur->rcv_time = now;

			prequeue_msgbuf(us, cur);
			us->processed++;
		}

		enqueue_and_wake_all(us);
		reinit_mmsghdr_vec(vec, nr_recv, RCVBUF_SIZE);
	}

	free_mmsghdr_vec(vec, us->batch);

	return NULL;
}
