/* printer.c: Very simple example C netconsd module
 *
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#include <stdlib.h>
#include <stdio.h>
#include <arpa/inet.h>

#include <msgbuf-struct.h>
#include <ncrx-struct.h>

int netconsd_output_init(int nr_workers)
{
	printf("From init hook: %d worker threads", nr_workers);
	return 0;
}

void netconsd_output_exit(void)
{
	puts("From exit hook");
}

/*
 * This is the actual function called by netconsd.
 */
void netconsd_output_handler(int t, struct in6_addr *src, struct msgbuf *buf,
		struct ncrx_msg *msg)
{
	char addr[INET6_ADDRSTRLEN] = {0};

	inet_ntop(AF_INET6, src, addr, INET6_ADDRSTRLEN);
	if (!msg)
		printf("%40s: %s\n", addr, buf->buf);
	else
		printf("%40s: S%06lu T%014lu F%d/L%d %s%s%s%s%s\n", addr,
			msg->seq, msg->ts_usec, msg->facility, msg->level,
			msg->cont_start ? "[CONT START] " : "",
			msg->cont ? "[CONT] " : "",
			msg->oos ? "[OOS] ": "",
			msg->seq_reset ? "[SEQ RESET] " : "",
			msg->text);
}
