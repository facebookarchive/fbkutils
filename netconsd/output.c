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
	int (*mod_init)(void);

	if (nr_outputs == MAXOUTS)
		return -1;

	dl = dlopen(path, RTLD_NOW|RTLD_LOCAL);
	if (!dl)
		return -1;

	dlsym_addr = dlsym(dl, "netconsd_output_handler");
	if (!dlsym_addr)
		goto err_close;

	mod_init = dlsym(dl, "netconsd_output_init");
	if (mod_init && mod_init())
		goto err_close;

	output_dlhandles[nr_outputs] = dl;
	outputs[nr_outputs] = dlsym_addr;
	nr_outputs++;
	return 0;

err_close:
	dlclose(dl);
	return -1;
}

void destroy_output_modules(void)
{
	int i, ret;
	void (*mod_exit)(void);

	for (i = 0; i < nr_outputs; i++) {
		mod_exit = dlsym(output_dlhandles[i], "netconsd_output_exit");

		if (mod_exit)
			mod_exit();

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
