/*
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */
#ifndef __LOG_H__
#define __LOG_H__

#include <stdio.h>
#include <errno.h>

#define LOGPFX "[fb-netconsd] "

#define S(x) #x
#define S_(x) S(x)
#define S__LINE__ S_(__LINE__)

#define __log(pfx, ...) \
do { \
	printf(LOGPFX __FILE__ ":" S__LINE__ ": " pfx __VA_ARGS__); \
	fflush(stdout); \
} while (0)

#define fatal(...) \
do { \
	__log("FATAL: ", __VA_ARGS__); \
	abort(); \
} while (0)

#define warn(...) \
do { \
	__log("WARNING: ", __VA_ARGS__); \
} while (0)

#define log(...) \
do { \
	__log("INFO: ", __VA_ARGS__); \
} while (0)

#ifdef DEBUG
#define debug(...) \
do { \
	__log("DEBUG: ", __VA_ARGS__); \
} while (0)
#else
#define debug(...) do {} while (0)
#endif

#define fatal_on(cond, ...) \
do { \
	if (__builtin_expect(cond, 0)) { \
		fatal(__VA_ARGS__); \
	} \
} while (0)

#define log_once(...) \
do { \
	static int _t; \
	if (__builtin_expect(!_t, 0)) { \
		log(__VA_ARGS__); \
		_t = -1; \
	} \
} while (0)

#define log_every(n, ...) \
do { \
	static int _t = 1; \
	if (!(_t % n), 0) \
		log(__VA_ARGS__); \
	_t++; \
} while (0)

#endif /* __LOG_H__ */
