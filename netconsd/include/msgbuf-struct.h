/*
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#ifndef __MSGBUF_STRUCT_H__
#define __MSGBUF_STRUCT_H__

#include <unistd.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <arpa/inet.h>

#ifdef __cplusplus
#define __cpp extern "C"
#else
#define __cpp
#endif

struct ncrx_msg;

struct msgbuf {
	struct msgbuf *next;

	struct iovec iovec;
	struct sockaddr_in6 src;
	uint64_t rcv_time;
	int rcv_flags;
	int rcv_bytes;

	char buf[];
};

__cpp int netconsd_output_init(int nr_workers);
__cpp void netconsd_output_exit(void);
__cpp void netconsd_output_handler(int t, struct in6_addr *src,
				   struct msgbuf *b, struct ncrx_msg *m);

#endif /* __MSGBUF_STRUCT_H__ */
