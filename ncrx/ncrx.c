/*
 * ncrx - simple extended netconsole receiver
 *
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <poll.h>
#include <ctype.h>
#include <errno.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/udp.h>

#include "ncrx.h"

int main(int argc, char **argv)
{
	char buf[NCRX_LINE_MAX + 1];
	struct ncrx *ncrx;
	struct sockaddr_in6 laddr = { };
	uint64_t next_seq = 0, next_at = UINT64_MAX, now;
	int prev_cont = 0;
	int fd;

	if (argc != 2) {
		fprintf(stderr, "Usage: ncrx PORT\n");
		return 1;
	}

	fd = socket(AF_INET6, SOCK_DGRAM, 0);
	if (fd < 0) {
		perror("socket");
		return 1;
	}

	laddr.sin6_family = AF_INET6;
	laddr.sin6_addr = in6addr_any;
	laddr.sin6_port = htons(atoi(argv[1]));

	if (bind(fd, (struct sockaddr *)&laddr, sizeof(laddr)) < 0) {
		perror("bind");
		return 1;
	}

	ncrx = ncrx_create(NULL);
	if (!ncrx) {
		perror("ncrx_create");
		return 1;
	}

	while (1) {
		struct pollfd pfd = { .fd = fd, .events = POLLIN };
		struct sockaddr_in raddr;
		struct ncrx_msg *msg;
		struct timespec ts;
		socklen_t raddr_len = sizeof(raddr);
		char *payload = NULL;
		const char *resp;
		int timeout;
		int len;

		/* determine sleep interval and poll */
		timeout = -1;
		if (next_at != UINT64_MAX) {
			timeout = 0;
			if (next_at > now)
				timeout = next_at - now;
		}

		if (poll(&pfd, 1, timeout) < 0) {
			perror("poll");
			return 1;
		}

		/* receive message */
		len = recvfrom(fd, buf, sizeof(buf) - 1, MSG_DONTWAIT,
			       (struct sockaddr *)&raddr, &raddr_len);

		payload = NULL;
		if (len >= 0) {
			buf[len] = '\0';
			payload = buf;
		} else if (errno != EAGAIN) {
			perror("recv");
			return 1;
		}

		/* determine the current time */
		if (clock_gettime(CLOCK_MONOTONIC, &ts)) {
			perror("clock_gettime");
			return 1;
		}
		now = ts.tv_sec * 1000 + ts.tv_nsec / 1000000;

		/* process the payload and perform rx operations */
		if (ncrx_process(payload, now, 0, ncrx) && errno != ENOENT) {
			if (errno == EINVAL) {
				while (len && isspace(payload[len - 1]))
					payload[--len] = '\0';
				printf("[%12s] %s\n", "INVAL", payload);
			} else {
				perror("ncrx_process");
			}
		}

		resp = ncrx_response(ncrx, &len);
		if (resp && sendto(fd, resp, len, 0,
				   (struct sockaddr *)&raddr, raddr_len) < 0)
			perror("sendto");

		while ((msg = ncrx_next_msg(ncrx))) {
			const char *pnl = prev_cont ? "\n" : "";

			if (msg->oos) {
				printf("%s[%12s] %s\n", pnl, "OOS", msg->text);
				prev_cont = 0;
				continue;
			}
			if (msg->seq_reset) {
				printf("%s[%12s] seq=%"PRIu64"\n",
				       pnl, "SEQ RESET", msg->seq);
				next_seq = msg->seq;
			}
			if (msg->seq != next_seq) {
				printf("%s[%12s] %"PRIu64" messages skipped\n",
				       pnl, "SEQ SKIPPED", msg->seq - next_seq);
			}

			next_seq = msg->seq + 1;

			if (!msg->cont || !prev_cont)
				printf("%s[%5"PRIu64".%06"PRIu64"] ", pnl,
				       msg->ts_usec / 1000000,
				       msg->ts_usec % 1000000);

			printf("%s", msg->text);

			prev_cont = msg->cont_start || msg->cont;
			if (!prev_cont)
				printf("\n");
		}

		next_at = ncrx_invoke_process_at(ncrx);
	}

	return 0;
}
