/*
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <pthread.h>
#include <dlfcn.h>
#include <sys/socket.h>
#include <netinet/in.h>

#include <ncrx.h>

#include "include/common.h"
#include "include/msgbuf-struct.h"
#include "include/output.h"

#define MAXOUTS 32

static void *output_dlhandles[MAXOUTS];
static void (*outputs[MAXOUTS])(int, struct in6_addr *, struct msgbuf *,
		struct ncrx_msg *);
static int nr_outputs;

int register_output_module(char *path)
{
	void *dl, *dlsym_addr;

	if (nr_outputs == MAXOUTS)
		return -1;

	dl = dlopen(path, RTLD_NOW|RTLD_LOCAL);
	if (!dl)
		return -1;

	dlsym_addr = dlsym(dl, "netconsd_output_handler");
	if (!dlsym_addr) {
		dlclose(dl);
		return -1;
	}

	output_dlhandles[nr_outputs] = dl;
	outputs[nr_outputs] = dlsym_addr;
	nr_outputs++;
	return 0;
}

void destroy_output_modules(void)
{
	int i, ret;

	for (i = 0; i < nr_outputs; i++) {
		ret = dlclose(output_dlhandles[i]);
		if (ret)
			warn("dlclose() failed: %s\n", dlerror());
	}
}

void execute_output_pipeline(int thread_nr, struct in6_addr *src,
		struct msgbuf *buf, struct ncrx_msg *msg)
{
	int i;

	for (i = 0; i < nr_outputs; i++)
		outputs[i](thread_nr, src, buf, msg);
}
