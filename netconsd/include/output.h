/*
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#ifndef __OUTPUT_H__
#define __OUTPUT_H__

#include <ncrx-struct.h>

#include "msgbuf-struct.h"

#define MAXOUTS 32

int register_output_module(char *path, int nr_workers);
void destroy_output_modules(void);

void execute_output_pipeline(int thread_nr, struct in6_addr *src,
		struct msgbuf *buf, struct ncrx_msg *msg);

#endif /* __OUTPUT_H__ */
