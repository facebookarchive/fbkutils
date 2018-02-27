/*
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#include <stdlib.h>
#include <signal.h>
#include <dlfcn.h>
#include <arpa/inet.h>
#include <getopt.h>

#include "include/common.h"
#include "include/output.h"
#include "include/threads.h"
#include "include/listener.h"

static void parse_arguments(int argc, char **argv, struct netconsd_params *p)
{
	int i;
	char *tmp;
	static const char *optstr = "hw:l:b:a:u:g:";
	static const struct option optlong[] = {
		{
			.name = "help",
			.has_arg = no_argument,
			.val = 'h',
		},
		{
			.name = NULL,
		},
	};

	while (1) {
		i = getopt_long(argc, argv, optstr, optlong, NULL);

		switch (i) {
		case 'w':
			p->nr_workers = atoi(optarg);
			break;
		case 'l':
			p->nr_listeners = atoi(optarg);
			break;
		case 'b':
			p->mmsg_batch = atoi(optarg);
			break;
		case 'a':
			if (!inet_pton(AF_INET6, optarg, &p->listen_addr.sin6_addr))
				fatal("invalid listen address\n");
			debug("listening for address %s\n", optarg);
			break;
		case 'u':
			p->listen_addr.sin6_port = htons(atoi(optarg));
			break;
		case 'g':
			tmp = index(optarg, '/');
			if (!tmp)
				fatal("'-g' expects 'INTERVAL/AGE' in ms\n");

			p->gc_int_ms = atoi(optarg);
			p->gc_age_ms = atoi(tmp + 1);

			if (p->gc_age_ms < p->gc_int_ms)
				fatal("GC age must be >= GC interval\n");

			break;
		case -1:
			goto done;
		case 'h':
			printf("Usage: %s [-w workers] [-l listeners] "
			     "[-b mmsg_batch] [-p udp_listen_addr] [-u udp_listen_port] "
			     "[-g '${interval}/${age}'] [output module path] "
			     "[another output module path...]\n", argv[0]);

			/*
			 * Fall through
			 */
		default:
			exit(1);
		}
	}

done:

	/*
	 * Register output modules
	 */
	if (optind == argc)
		warn("You passed no output modules, which is sort of silly\n");

	if (argc - optind > MAXOUTS)
		fatal("Too many output mods: %d>%d\n", argc - optind, MAXOUTS);

	for (i = optind; i < argc; i++)
		if (register_output_module(argv[i], p->nr_workers))
			fatal("Can't register '%s'\n", argv[i]);
}

/*
 * This exists to kick the blocking recvmmsg() call in the listener threads, so
 * they get -EINTR, notice the stop flag, and terminate.
 *
 * See also: stop_and_wait_for_listeners() in threads.c
 */
static void interrupter_handler(int sig)
{
	return;
}

/*
 * Initialize the set of signals for which we try to terminate gracefully.
 */
static void init_sigset(sigset_t *set)
{
	sigemptyset(set);
	sigaddset(set, SIGTERM);
	sigaddset(set, SIGINT);
	sigaddset(set, SIGHUP);
}

static void init_sighandlers(void)
{
	struct sigaction ignorer = {
		.sa_handler = SIG_IGN,
	};
	struct sigaction interrupter = {
		.sa_handler = interrupter_handler,
		.sa_flags = SA_NODEFER,
	};

	sigaction(SIGUSR1, &interrupter, NULL);
	sigaction(SIGPIPE, &ignorer, NULL);
}

int main(int argc, char **argv)
{
	int num;
	sigset_t set;
	struct tctl *ctl;
	struct netconsd_params params = {
		.nr_workers = 2,
		.nr_listeners = 1,
		.mmsg_batch = 512,
		.gc_int_ms = 0,
		.gc_age_ms = 0,
		.listen_addr = {
			.sin6_family = AF_INET6,
			.sin6_addr = IN6ADDR_ANY_INIT,
			.sin6_port = htons(1514),
		}
	};

	parse_arguments(argc, argv, &params);

	init_sighandlers();
	init_sigset(&set);
	sigprocmask(SIG_BLOCK, &set, NULL);

	ctl = create_threads(&params);
	sigwait(&set, &num);

	log("Signal: '%s', terminating\n", strsignal(num));
	destroy_threads(ctl);
	destroy_output_modules();

	return 0;
}
