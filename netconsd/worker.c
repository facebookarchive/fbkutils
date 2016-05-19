/*
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#include <stdlib.h>
#include <pthread.h>
#include <string.h>
#include <limits.h>
#include <sys/socket.h>
#include <netinet/in.h>

#include <ncrx.h>

#include "include/common.h"
#include "include/msgbuf-struct.h"
#include "include/output.h"
#include "include/worker.h"

static const struct ncrx_param ncrx_param = {
	.nr_slots = 512,
	.retx_intv = NETCONS_RTO,
	.msg_timeout = NETCONS_RTO,
	.oos_timeout = NETCONS_RTO,
};

/*
 * Keep it simple: just use a boring probing hashtable that resizes.
 */

struct timerlist {
	struct timerlist *prev;
	struct timerlist *next;
	unsigned long when;
};

struct bucket {
	struct in6_addr src;
	struct ncrx *ncrx;
	unsigned long last_seen;
	struct timerlist timernode;
};

struct hashtable {
	unsigned long order;
	unsigned long load;
	struct bucket *table;
};

static unsigned long hash_srcaddr(struct in6_addr *addr)
{
	return jhash2((uint32_t *)addr, sizeof(*addr) / sizeof(uint32_t),
			0xbeefdead);
}

static unsigned long order_mask(int order)
{
	return (1UL << order) - 1;
}

static unsigned long htable_mask(unsigned long hash, int order)
{
	return hash & order_mask(order);
}

static unsigned long htable_hash(struct hashtable *h, struct in6_addr *s)
{
	return htable_mask(hash_srcaddr(s), h->order);
}

static int srcaddr_compar(struct in6_addr *a, struct in6_addr *b)
{
	return memcmp(a, b, sizeof(*a));
}

static struct bucket *hlookup(struct hashtable *h, struct in6_addr *src)
{
	unsigned long origidx, idx;

	origidx = htable_hash(h, src);
	idx = origidx;

	while (h->table[idx].ncrx && srcaddr_compar(&h->table[idx].src, src)) {
		idx = htable_mask(idx + 1, h->order);
		fatal_on(idx == origidx, "Worker hashtable is full\n");
	}

	return &h->table[idx];
}


static void reset_waketime(struct ncrx_worker *cur)
{
	/*
	 * Use a large value, but one that won't overflow in the subsequent
	 * multiplication by 1000 in maybe_update_wake() below.
	 */
	cur->wake.tv_sec = 1L << 48;
	cur->wake.tv_nsec = 0;
}

static unsigned long ms_from_timespec(struct timespec *t)
{
	return t->tv_sec * 1000 + t->tv_nsec / 1000000L;
}

/*
 * We may need to make the wakeup time for pthread_cond_timedwait() sooner.
 */
static void maybe_update_wake(struct ncrx_worker *cur, unsigned long when)
{
	if (ms_from_timespec(&cur->wake) <= when)
		return;

	cur->wake.tv_sec = when / 1000;
	cur->wake.tv_nsec = (when % 1000) * 1000000L;
}

static struct bucket *bucket_from_timernode(struct timerlist *node)
{
	return container_of(node, struct bucket, timernode);
}

static void timerlist_init(struct timerlist *node)
{
	node->next = node;
	node->prev = node;
	node->when = 0;
}

static int timerlist_empty(struct timerlist *node)
{
	return node->next == node;
}

static void timerlist_append(struct timerlist *node, struct timerlist *list)
{
	struct timerlist *prev = list->prev;

	fatal_on(!timerlist_empty(node), "Queueing node already on list\n");

	node->next = list;
	node->prev = prev;
	prev->next = node;
	list->prev = node;
}

static void timerlist_del(struct timerlist *node)
{
	struct timerlist *prev = node->prev;
	struct timerlist *next = node->next;

	prev->next = next;
	next->prev = prev;
	timerlist_init(node);
}

/*
 * Return the callback time of the newest item on the list
 */
static unsigned long timerlist_peek(struct timerlist *list)
{
	if (timerlist_empty(list))
		return 0;

	return list->prev->when;
}

#define timerlist_for_each(this, n, thead) \
	for (this = (thead)->next, n = this->next; this != (thead); \
		this = n, n = this->next)

static struct timerlist *create_timerlists(void)
{
	struct timerlist *ret;
	int i;

	ret = calloc(NETCONS_RTO, sizeof(*ret));
	if (!ret)
		fatal("Unable to allocate timerlist\n");

	for (i = 0; i < NETCONS_RTO; i++)
		timerlist_init(&ret[i]);

	return ret;
}

static void destroy_timerlists(struct timerlist *timerlist)
{
	free(timerlist);
}

static struct hashtable *create_hashtable(int order, struct hashtable *old)
{
	struct hashtable *new;
	struct bucket *bkt;
	unsigned long i;

	new = calloc(1, sizeof(*new));
	if (!new)
		fatal("Unable to allocate hashtable\n");

	new->table = calloc(1UL << order, sizeof(struct bucket));
	if (!new->table)
		fatal("Unable to allocate hashtable\n");

	new->order = order;

	if (!old)
		return new;

	for (i = 0; i < (1UL << old->order); i++) {
		if (old->table[i].ncrx) {
			bkt = hlookup(new, &old->table[i].src);
			memcpy(bkt, &old->table[i], sizeof(*bkt));

			/*
			 * If the timernode wasn't on a list, initialize it as
			 * empty for the new bucket. If it was, update its
			 * neighbors to point to the new bucket.
			 */
			if (bkt->timernode.next == &old->table[i].timernode) {
				timerlist_init(&bkt->timernode);
			} else {
				bkt->timernode.next->prev = &bkt->timernode;
				bkt->timernode.prev->next = &bkt->timernode;
			}
		}
	}

	new->load = old->load;

	free(old->table);
	free(old);
	return new;
}

static void destroy_hashtable(struct hashtable *ht)
{
	unsigned long i;

	for (i = 0; i < (1UL << ht->order); i++)
		if (ht->table[i].ncrx)
			ncrx_destroy(ht->table[i].ncrx);

	free(ht->table);
	free(ht);
}

static void maybe_resize_hashtable(struct ncrx_worker *cur, unsigned long new)
{
	unsigned long neworder;

	if ((cur->ht->load + new) >> (cur->ht->order - 2) < 3)
		return;

	/*
	 * The hashtable is more than 75% full. Resize it such that it can take
	 * @new additional client hosts and be less than 50% full.
	 */
	neworder = LONG_BIT - __builtin_clzl(cur->ht->load + new) + 1;
	cur->ht = create_hashtable(neworder, cur->ht);
}

static void hdelete(struct hashtable *h, struct bucket *victim)
{
	struct bucket *old, *new;
	unsigned long origidx, idx;

	fatal_on(!victim->ncrx, "Attempt to delete free bucket\n");

	if (!timerlist_empty(&victim->timernode))
		timerlist_del(&victim->timernode);

	h->load--;
	ncrx_destroy(victim->ncrx);
	memset(victim, 0, sizeof(*victim));

	/*
	 * There's potential to be clever here, but for now just be pedantic and
	 * rebucket any potentially probed entries.
	 */

	origidx = victim - h->table;
	idx = origidx;
	while (h->table[idx].ncrx) {
		old = &h->table[idx];
		new = hlookup(h, &old->src);
		if (new != old) {
			memcpy(new, old, sizeof(*new));
			memset(old, 0, sizeof(*old));

			/*
			 * If the timernode wasn't on a list, initialize it as
			 * empty for the new bucket. If it was, update its
			 * neighbors to point to the new bucket.
			 */
			if (new->timernode.next == &old->timernode) {
				timerlist_init(&new->timernode);
			} else {
				new->timernode.next->prev = &new->timernode;
				new->timernode.prev->next = &new->timernode;
			}
		}

		idx = htable_mask(idx + 1, h->order);
		fatal_on(idx == origidx, "Infinite loop in hdelete()\n");
	}
}

/*
 * Simple garbage collection. This is meant to be rare (on the order of once per
 * hour), so maintaining an LRU list isn't worth the overhead: just blow through
 * the whole table. Worst case it's ~50MB.
 */
static void try_to_garbage_collect(struct ncrx_worker *cur)
{
	unsigned long i, now, end, count = 0;
	struct bucket *bkt;

	now = now_epoch_ms();
	for (i = 0; i < (1UL << cur->ht->order); i++) {
		bkt = &cur->ht->table[i];

		if (bkt->ncrx && now - bkt->last_seen > cur->gc_age_ms) {
			hdelete(cur->ht, bkt);
			count++;
		}
	}
	end = now_epoch_ms();

	log("Worker %d GC'd %lu in %lums\n", cur->thread_nr, count, end - now);
}

static void maybe_garbage_collect(struct ncrx_worker *cur)
{
	unsigned long nowgc;

	if (!cur->gc_int_ms)
		return;

	nowgc = now_epoch_ms() / cur->gc_int_ms;
	if (nowgc > cur->lastgc) {
		try_to_garbage_collect(cur);
		cur->lastgc = nowgc;
	}
}

static void schedule_ncrx_callback(struct ncrx_worker *cur, struct bucket *bkt,
		unsigned long when)
{
	struct timerlist *tgtlist;
	unsigned long now;

	if (when == UINT64_MAX) {
		/*
		 * No callback needed. If we had one we no longer need it, so
		 * just remove ourselves from the timerlist.
		 */
		if (!timerlist_empty(&bkt->timernode))
			timerlist_del(&bkt->timernode);

		return;
	}

	/*
	 * Never queue messages outside the current window. This clamp() is what
	 * guarantees that the callbacks in the timerlists are strictly ordered
	 * from least to most recent: at any given moment only one callback time
	 * corresponds to each bucket, and time cannot go backwards.
	 */
	now = now_epoch_ms();
	when = clamp(when, now + 1, now + NETCONS_RTO);

	/*
	 * If the bucket is already on a timerlist, we only requeue it if the
	 * callback needs to happen earlier than the one currently queued.
	 */
	if (!timerlist_empty(&bkt->timernode)) {
		if (when > bkt->timernode.when)
			return;

		timerlist_del(&bkt->timernode);
	}

	tgtlist = &cur->tlist[when % NETCONS_RTO];
	fatal_on(when < timerlist_peek(tgtlist), "Timerlist ordering broken\n");

	bkt->timernode.when = when;
	timerlist_append(&bkt->timernode, tgtlist);
	maybe_update_wake(cur, when);
}

/*
 * Read any pending messages out of the bucket, and invoke the output pipeline
 * with the extended metadata.
 */
static void drain_bucket_ncrx(struct ncrx_worker *cur, struct bucket *bkt)
{
	struct ncrx_msg *out;
	unsigned long when;

	while ((out = ncrx_next_msg(bkt->ncrx))) {
		execute_output_pipeline(cur->thread_nr, &bkt->src, NULL, out);
		free(out);
	}

	when = ncrx_invoke_process_at(bkt->ncrx);
	schedule_ncrx_callback(cur, bkt, when);
}

/*
 * Execute callbacks for a specific timerlist, until either the list is empty or
 * we reach an entry that was queued for a time in the future.
 */
static void do_ncrx_callbacks(struct ncrx_worker *cur,
		struct timerlist *list, unsigned long now)
{
	struct timerlist *tnode, *tmp;
	struct bucket *bkt;

	timerlist_for_each(tnode, tmp, list) {
		if (tnode->when > now)
			break;

		/*
		 * Remove the bucket from the list first, since it might end up
		 * being re-added to another timerlist by drain_bucket_ncrx().
		 */
		timerlist_del(tnode);

		bkt = bucket_from_timernode(tnode);
		ncrx_process(NULL, now, bkt->ncrx);
		drain_bucket_ncrx(cur, bkt);
	}
}

/*
 * We have no idea how large the queue we just processed was: it could have
 * taken tens of seconds. So we must handle wraparound in the tlist array.
 *
 * There are three cases:
 *
 * 1) lastrun == now
 *	In this case, we don't need to do anything, just return.
 *
 * 2) (now - lastrun) < NETCONS_RTO
 *	In this case we know we haven't wrapped, so we only need to process any
 *	timerslots in the interval since our last run and return.
 *
 * 3) (now - lastrun) >= NETCONS_RTO
 *	We wrapped, so just iterate over the entire wheel and drain until we see
 *	a callback where ->when is later than NOW.
 */
static unsigned long run_ncrx_callbacks(struct ncrx_worker *cur,
		unsigned long lastrun)
{
	unsigned long i, now = now_epoch_ms();

	if (now == lastrun)
		goto out;

	fatal_on(now < lastrun, "Time went backwards\n");

	if (now - lastrun < NETCONS_RTO) {
		for (i = lastrun; i <= now; i++)
			do_ncrx_callbacks(cur, &cur->tlist[i % NETCONS_RTO], i);

		goto out;
	}

	/*
	 * We wrapped, need to check them all.
	 */
	for (i = 0; i < NETCONS_RTO; i++)
		do_ncrx_callbacks(cur, &cur->tlist[i], now);

out:
	return now;
}

static void consume_msgbuf(struct ncrx_worker *cur, struct msgbuf *buf)
{
	struct bucket *ncrx_bucket;

	ncrx_bucket = hlookup(cur->ht, &buf->src.sin6_addr);
	if (!ncrx_bucket->ncrx) {
		ncrx_bucket->ncrx = ncrx_create(&ncrx_param);
		timerlist_init(&ncrx_bucket->timernode);
		memcpy(&ncrx_bucket->src, &buf->src.sin6_addr,
				sizeof(ncrx_bucket->src));
		cur->ht->load++;
	}

	ncrx_bucket->last_seen = buf->rcv_time;

	buf->buf[buf->rcv_bytes] = '\0';
	if (!ncrx_process(buf->buf, buf->rcv_time, ncrx_bucket->ncrx)) {
		drain_bucket_ncrx(cur, ncrx_bucket);
		return;
	}

	execute_output_pipeline(cur->thread_nr, &ncrx_bucket->src, buf, NULL);
}

static struct msgbuf *grab_prequeue(struct ncrx_worker *cur)
{
	struct msgbuf *ret;

	assert_pthread_mutex_locked(&cur->queuelock);
	ret = cur->queue_head;
	cur->queue_head = NULL;

	return ret;
}

void *ncrx_worker_thread(void *arg)
{
	struct ncrx_worker *cur = arg;
	struct msgbuf *curbuf, *tmp;
	unsigned long lastrun = now_epoch_ms();
	int nr_dequeued;

	cur->ht = create_hashtable(16, NULL);
	cur->tlist = create_timerlists();

	reset_waketime(cur);
	pthread_mutex_lock(&cur->queuelock);
	while (!cur->stop) {
		pthread_cond_timedwait(&cur->cond, &cur->queuelock, &cur->wake);
		reset_waketime(cur);
morework:
		curbuf = grab_prequeue(cur);
		nr_dequeued = cur->nr_queued;
		cur->nr_queued = 0;
		pthread_mutex_unlock(&cur->queuelock);

		maybe_resize_hashtable(cur, nr_dequeued);

		while ((tmp = curbuf)) {
			consume_msgbuf(cur, curbuf);
			curbuf = curbuf->next;
			free(tmp);

			cur->processed++;
		}

		if (!cur->stop) {
			maybe_garbage_collect(cur);
			lastrun = run_ncrx_callbacks(cur, lastrun);
		}

		pthread_mutex_lock(&cur->queuelock);
		if (cur->queue_head)
			goto morework;
	}

	assert_pthread_mutex_locked(&cur->queuelock);
	fatal_on(cur->queue_head != NULL, "Worker queue not empty at exit\n");

	cur->hosts_seen = cur->ht->load;
	destroy_timerlists(cur->tlist);
	destroy_hashtable(cur->ht);
	return NULL;
}
