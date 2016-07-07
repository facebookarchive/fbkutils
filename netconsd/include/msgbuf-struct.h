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

#define NETCONSD_MAX_WORKER_NUM 64

struct msgbuf {
	struct msgbuf *next;

	struct iovec iovec;
	struct sockaddr_in6 src;
	uint64_t rcv_time;
	int rcv_flags;
	int rcv_bytes;

	char buf[];
};

#endif /* __MSGBUF_STRUCT_H__ */
