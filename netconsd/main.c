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

#include "include/common.h"
#include "include/output.h"
#include "include/threads.h"
#include "include/listener.h"

static void parse_arguments(int argc, char **argv, struct netconsd_params *p)
{
	int i;
	char *tmp;

	while ((i = getopt(argc, argv, "w:l:b:u:g:")) != -1) {
		switch(i) {
		case 'w':
			p->nr_workers = atoi(optarg);
			break;
		case 'l':
			p->nr_listeners = atoi(optarg);
			break;
		case 'b':
			p->mmsg_batch = atoi(optarg);
			break;
		case 'u':
			p->udp_listen_port = atoi(optarg);
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
		default:
			fatal("Invalid command line parameters\n");
		}
	}

	/*
	 * Register output modules
	 */
	if (optind == argc)
		warn("You passed no output modules, which is sort of silly\n");

	for (i = optind; i < argc; i++)
		if (register_output_module(argv[i]))
			fatal("Can't register %s\n", dlerror());
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
	sigaddset(set, SIGQUIT);
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
		.udp_listen_port = 1514,
		.gc_int_ms = 0,
		.gc_age_ms = 0,
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
