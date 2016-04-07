/*
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#ifndef __NCRX_THREADS_H__
#define __NCRX_THREADS_H__

#include "msgbuf-struct.h"
#include "common.h"

struct tctl;
struct ncrx_listener;

void enqueue_and_wake_all(struct ncrx_listener *listener);
struct tctl *create_threads(struct netconsd_params *p);
void destroy_threads(struct tctl *ctl);

#endif /* __NCRX_THREADS_H__ */
