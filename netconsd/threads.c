/*
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include <signal.h>
#include <pthread.h>
#include <unistd.h>
#include <sys/socket.h>

#include "include/common.h"
#include "include/msgbuf-struct.h"
#include "include/listener.h"
#include "include/worker.h"
#include "include/threads.h"

struct tctl {
	int nr_listeners;
	int nr_workers;
	struct ncrx_listener *listeners;
	struct ncrx_worker *workers;
};

static void wake_thread(struct ncrx_listener *listener, int worker)
{
	struct ncrx_worker *tgt = &listener->workers[worker];

	debug("Waking thread %d\n", worker);
	pthread_cond_signal(&tgt->cond);
}

static void push_prequeue_to_worker(struct ncrx_listener *listener, int worker)
{
	struct ncrx_worker *tgt = &listener->workers[worker];
	struct ncrx_prequeue *prequeue = &listener->prequeues[worker];

	assert_pthread_mutex_locked(&tgt->queuelock);

	if (tgt->queue_head)
		tgt->queue_tail->next = prequeue->queue_head;
	else
		tgt->queue_head = prequeue->queue_head;

	tgt->queue_tail = prequeue->queue_tail;
	prequeue->queue_head = NULL;

	debug("Listener %d pushed %d pkts to worker %d (backlog: %d)\n",
		listener, prequeue->count, worker, tgt->nr_queued);

	tgt->nr_queued += prequeue->count;
	prequeue->count = 0;
}

static void enqueue_and_wake_worker(struct ncrx_listener *listener, int worker)
{
	struct ncrx_worker *tgt = &listener->workers[worker];

	pthread_mutex_lock(&tgt->queuelock);
	push_prequeue_to_worker(listener, worker);
	pthread_mutex_unlock(&tgt->queuelock);

	wake_thread(listener, worker);
}

static int prequeue_is_empty(struct ncrx_listener *listener, int worker)
{
	struct ncrx_prequeue *prequeue = &listener->prequeues[worker];
	return prequeue->queue_head == NULL;
}

void enqueue_and_wake_all(struct ncrx_listener *listener)
{
	int i;

	for (i = 0; i < listener->nr_workers; i++)
		if (!prequeue_is_empty(listener, i))
			enqueue_and_wake_worker(listener, i);
}

static void stop_and_wait_for_workers(struct tctl *ctl)
{
	int i;
	uint64_t total_processed = 0, total_hosts = 0;

	for (i = 0; i < ctl->nr_workers; i++) {
		ctl->workers[i].stop = 1;
		pthread_cond_signal(&ctl->workers[i].cond);
		pthread_join(ctl->workers[i].id, NULL);

		pthread_mutex_destroy(&ctl->workers[i].queuelock);
		pthread_cond_destroy(&ctl->workers[i].cond);
		pthread_condattr_destroy(&ctl->workers[i].condattr);

		total_processed += ctl->workers[i].processed;
		total_hosts += ctl->workers[i].hosts_seen;
		log("Exiting worker %d got %" PRIu64 " msgs from %" PRIu64 " hosts\n",
				i, ctl->workers[i].processed,
				ctl->workers[i].hosts_seen);
	}

	log("Total messages processed by workers: %" PRIu64 " from %" PRIu64 " hosts\n",
			total_processed, total_hosts);
	free(ctl->workers);
}

static void stop_and_wait_for_listeners(struct tctl *ctl)
{
	int i;
	uint64_t total_processed = 0;

	for (i = 0; i < ctl->nr_listeners; i++) {
		ctl->listeners[i].stop = 1;
		pthread_kill(ctl->listeners[i].id, SIGUSR1);
		pthread_join(ctl->listeners[i].id, NULL);

		free(ctl->listeners[i].prequeues);

		total_processed += ctl->listeners[i].processed;
		log("Exiting listener %d queued %" PRIu64 " messages\n", i,
				ctl->listeners[i].processed);
	}

	log("Total messages processed by listeners: %" PRIu64 "\n",
			total_processed);
	free(ctl->listeners);
}

static void create_worker_threads(struct tctl *ctl, struct netconsd_params *p)
{
	struct ncrx_worker *cur, *workers;
	int i, r;

	workers = calloc(p->nr_workers, sizeof(*workers));
	if (!workers)
		fatal("Couldn't allocate thread structures\n");

	for (i = 0; i < p->nr_workers; i++) {
		cur = &workers[i];

		pthread_mutex_init(&cur->queuelock, NULL);
		pthread_condattr_init(&cur->condattr);
		pthread_condattr_setclock(&cur->condattr, CLOCK_MONOTONIC);
		pthread_cond_init(&cur->cond, &cur->condattr);
		cur->queue_head = NULL;
		cur->thread_nr = i;

		cur->gc_int_ms = p->gc_int_ms;
		cur->gc_age_ms = p->gc_age_ms;
		cur->lastgc = p->gc_int_ms ? now_mono_ms() / p->gc_int_ms : 0;

		r = pthread_create(&cur->id, NULL, ncrx_worker_thread, cur);
		if (r)
			fatal("%d/%d failed: -%d\n", i, p->nr_workers, r);
	}

	ctl->nr_workers = p->nr_workers;
	ctl->workers = workers;
}

static void create_listener_threads(struct tctl *ctl, struct netconsd_params *p)
{
	struct ncrx_prequeue *prequeues;
	struct ncrx_listener *cur, *listeners;
	int i, r;

	listeners = calloc(p->nr_listeners, sizeof(*listeners));
	if (!listeners)
		fatal("Couldn't allocate listeners: %m\n");

	for (i = 0; i < p->nr_listeners; i++) {
		cur = &listeners[i];

		prequeues = calloc(ctl->nr_workers, sizeof(*prequeues));
		if (!prequeues)
			fatal("ENOMEM %d/%d\n", i, p->nr_listeners);

		cur->thread_nr = i;
		cur->prequeues = prequeues;
		cur->workers = ctl->workers;
		cur->nr_workers = ctl->nr_workers;
		cur->batch = p->mmsg_batch;
		cur->address = &p->listen_addr;

		r = pthread_create(&cur->id, NULL, udp_listener_thread, cur);
		if (r)
			fatal("%d/%d failed: -%d\n", i, p->nr_listeners, r);
	}

	ctl->nr_listeners = p->nr_listeners;
	ctl->listeners = listeners;
}

void destroy_threads(struct tctl *ctl)
{
	stop_and_wait_for_listeners(ctl);
	stop_and_wait_for_workers(ctl);
	free(ctl);
}

struct tctl *create_threads(struct netconsd_params *p)
{
	struct tctl *ret;

	ret = calloc(1, sizeof(*ret));
	if (!ret)
		fatal("Couldn't allocate thread structures\n");

	ret->nr_workers = p->nr_workers;

	create_worker_threads(ret, p);
	create_listener_threads(ret, p);

	return ret;
}
