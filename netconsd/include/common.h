/*
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#ifndef __COMMON_H__
#define __COMMON_H__

#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>

#include "log.h"
#include "jhash.h"

#define min(x, y) ({							\
	typeof(x) _min1 = (x);						\
	typeof(y) _min2 = (y);						\
	(void) (&_min1 == &_min2);					\
	_min1 < _min2 ? _min1 : _min2; })

#define max(x, y) ({							\
	typeof(x) _max1 = (x);						\
	typeof(y) _max2 = (y);						\
	(void) (&_max1 == &_max2);					\
	_max1 > _max2 ? _max1 : _max2; })

#define clamp(val, lo, hi) min((typeof(val))max(val, lo), hi)

#define container_of(ptr, type, member) ({			\
	const typeof( ((type *)0)->member ) *__mptr = (ptr);	\
	(type *)( (char *)__mptr - __builtin_offsetof(type,member) );})

static inline void *zalloc(size_t n)
{
	return calloc(1, n);
}

#define assert_pthread_mutex_locked(m)					\
do {									\
	fatal_on(pthread_mutex_trylock(m) != EBUSY, "UNLOCKED!\n");	\
} while (0)

static inline uint64_t now_ms(clockid_t clock)
{
	struct timespec t;
	int ret;

	ret = clock_gettime(clock, &t);
	fatal_on(ret, "Oops, clock_gettime() barfed: %m (-%d)\n", errno);

	return t.tv_sec * 1000LL + t.tv_nsec / 1000000L;
}

static inline uint64_t now_mono_ms(void)
{
	return now_ms(CLOCK_MONOTONIC);
}

static inline uint64_t now_real_ms(void)
{
	return now_ms(CLOCK_REALTIME);
}

struct netconsd_params {
	int nr_workers;
	int nr_listeners;
	int mmsg_batch;
	unsigned int gc_int_ms;
	unsigned int gc_age_ms;
	struct sockaddr_in6 listen_addr;
};

#endif /* __COMMON_H__ */
