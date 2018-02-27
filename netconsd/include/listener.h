/*
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#ifndef __LISTENER_H__
#define __LISTENER_H__

#include "threads.h"

#define RCVBUF_SIZE	1024

struct ncrx_worker;

struct ncrx_prequeue {
	struct msgbuf *queue_head;
	struct msgbuf *queue_tail;
	int count;
};

struct ncrx_listener {
	pthread_t id;
	int thread_nr;
	struct ncrx_prequeue *prequeues;
	struct ncrx_worker *workers;
	int nr_workers;
	int batch;
	uint64_t processed;
	struct sockaddr_in6 *address;

	/*
	 * Flags
	 */
	unsigned stop:1;
};

void *udp_listener_thread(void *arg);

#endif /* __LISTENER_H__ */
