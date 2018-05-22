/*
 * ncrx - extended netconsole receiver library
 *
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <errno.h>
#include <assert.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/udp.h>

#include "ncrx.h"

/* oos history is tracked with a uint32_t */
#define NCRX_OOS_MAX		32

struct ncrx_msg_list {
	struct ncrx_list	head;
	int			nr;		/* number of msgs on the list */
};

struct ncrx_slot {
	struct ncrx_msg		*msg;
	uint64_t		timestamp;	/* last rx on this slot */
	uint64_t		retx_timestamp;	/* last retransmission */
	struct ncrx_list	hole_node;	/* anchored @ ncrx->hole_list */
};

struct ncrx {
	struct ncrx_param	p;

	uint64_t		now_mono;	/* latest time in msecs */

	int			head;		/* next slot to use */
	int			tail;		/* last slot in use */
	uint64_t		head_seq;	/* next expected seq, unset=0 */
	struct ncrx_slot	*slots;		/* msg slots */
	struct ncrx_list	hole_list;	/* missing or !complete slots */

	uint32_t		oos_history;	/* bit history of oos msgs */
	struct ncrx_msg_list	oos_list;	/* buffered oos msgs */

	struct ncrx_msg_list	retired_list;	/* msgs to be fetched by user */

	uint64_t		acked_seq;	/* last seq acked, unset=max */
	uint64_t		acked_at;	/* and when */

	/* response buffer for ncrx_response() */
	char			resp_buf[NCRX_PKT_MAX + 1];
	int			resp_len;
};

static const struct ncrx_param ncrx_dfl_param = {
	.nr_slots		= NCRX_DFL_NR_SLOTS,

	.ack_intv		= NCRX_DFL_ACK_INTV,
	.retx_intv		= NCRX_DFL_RETX_INTV,
	.retx_stride		= NCRX_DFL_RETX_STRIDE,
	.msg_timeout		= NCRX_DFL_MSG_TIMEOUT,

	.oos_thr		= NCRX_DFL_OOS_THR,
	.oos_intv		= NCRX_DFL_OOS_INTV,
	.oos_timeout		= NCRX_DFL_OOS_TIMEOUT,
};

/* utilities mostly stolen from kernel */
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

#define offsetof(TYPE, MEMBER) ((size_t) &((TYPE *)0)->MEMBER)

#define container_of(ptr, type, member) ({				\
	const typeof( ((type *)0)->member ) *__mptr = (ptr);		\
	(type *)( (char *)__mptr - offsetof(type,member) );})

/* ncrx_msg from its ->node */
#define node_to_msg(ptr)	container_of(ptr, struct ncrx_msg, node)

/* iterate msg_list */
#define msg_list_for_each(pos, n, list)					\
	for (pos = node_to_msg((list)->head.next),			\
		     n = node_to_msg(pos->node.next);			\
	     &pos->node != &(list)->head;				\
	     pos = n, n = node_to_msg(pos->node.next))

/* ncrx_slot from its ->hole_node */
#define hole_to_slot(ptr)						\
	container_of(ptr, struct ncrx_slot, hole_node)

/* iterate hole_list */
#define hole_list_for_each(pos, n, list)				\
	for (pos = hole_to_slot((list)->next),				\
		     n = hole_to_slot(pos->hole_node.next);		\
	     &pos->hole_node != (list);					\
	     pos = n, n = hole_to_slot(pos->hole_node.next))

static unsigned int hweight32(uint32_t w)
{
	w -= (w >> 1) & 0x55555555;
	w =  (w & 0x33333333) + ((w >> 2) & 0x33333333);
	w =  (w + (w >> 4)) & 0x0f0f0f0f;
	return (w * 0x01010101) >> 24;
}

static void init_list(struct ncrx_list *head)
{
	head->next = head;
	head->prev = head;
}

static int list_empty(struct ncrx_list *head)
{
	return head->next == head;
}

static void list_del(struct ncrx_list *head)
{
	struct ncrx_list *prev = head->prev;
	struct ncrx_list *next = head->next;

	prev->next = next;
	next->prev = prev;
	init_list(head);
}

static void list_append(struct ncrx_list *node, struct ncrx_list *list)
{
	struct ncrx_list *prev = list->prev;

	assert(node->next == node && node->prev == node);

	node->next = list;
	node->prev = prev;
	prev->next = node;
	list->prev = node;
}

static void msg_list_del(struct ncrx_msg *msg, struct ncrx_msg_list *list)
{
	list_del(&msg->node);
	list->nr--;

	if (!list->nr)
		assert(list->head.next == &list->head &&
		       list->head.prev == &list->head);
}

static void msg_list_append(struct ncrx_msg *msg, struct ncrx_msg_list *list)
{
	list_append(&msg->node, &list->head);
	list->nr++;
}

static struct ncrx_msg *msg_list_peek(struct ncrx_msg_list *list)
{
	if (list_empty(&list->head))
		return NULL;
	return node_to_msg(list->head.next);
}

static struct ncrx_msg *msg_list_pop(struct ncrx_msg_list *list)
{
	struct ncrx_msg *msg;

	msg = msg_list_peek(list);
	if (msg)
		msg_list_del(msg, list);
	return msg;
}

/*
 * Parse @payload into @msg.  The data is not copied into @msg's buffer.
 * @msg->text and ->dict are updated to point into @payload instead.
 */
static int parse_packet(const char *payload, struct ncrx_msg *msg)
{
	char buf[1024];
	char *p, *tok;
	int idx;

	memset(msg, 0, sizeof(*msg));

	p = strchr(payload, ';');
	if (!p || p - payload >= (signed)sizeof(buf))
		goto einval;
	memcpy(buf, payload, p - payload);
	buf[p - payload] = '\0';

	msg->text = p + 1;
	msg->text_len = strlen(msg->text);
	if (msg->text_len > NCRX_LINE_MAX)
		msg->text_len = NCRX_LINE_MAX;

	/* <level>,<sequnum>,<timestamp>,<contflag>[,KEY=VAL]* */
	idx = 0;
	p = buf;
	while ((tok = strsep(&p, ","))) {
		char *endp, *key, *val;
		unsigned long long v;

		switch (idx++) {
		case 0:
			v = strtoul(tok, &endp, 0);
			if (*endp != '\0' || v > UINT8_MAX)
				goto einval;
			msg->facility = v >> 3;
			msg->level = v & ((1 << 3) - 1);
			continue;
		case 1:
			v = strtoull(tok, &endp, 0);
			if (*endp != '\0')
				goto einval;
			msg->seq = v;
			continue;
		case 2:
			v = strtoull(tok, &endp, 0);
			if (*endp != '\0')
				goto einval;
			msg->ts_usec = v;
			continue;
		case 3:
			if (tok[0] == 'c')
				msg->cont_start = 1;
			else if (tok[0] == '+')
				msg->cont = 1;
			continue;
		}

		val = tok;
		key = strsep(&val, "=");
		if (!val)
			continue;
		if (!strcmp(key, "ncfrag")) {
			unsigned nf_off, nf_len;

			if (sscanf(val, "%u/%u", &nf_off, &nf_len) != 2)
				goto einval;
			if (!msg->text_len ||
			    nf_len >= NCRX_LINE_MAX ||
			    nf_off + msg->text_len > nf_len)
				goto einval;

			msg->ncfrag_off = nf_off;
			msg->ncfrag_len = msg->text_len;
			msg->ncfrag_left = nf_len - msg->ncfrag_len;
			msg->text_len = nf_len;
		} else if (!strcmp(key, "ncemg")) {
			v = strtoul(val, &endp, 0);
			if (*endp != '\0')
				goto einval;
			msg->emg = v;
		}
	}
	return 0;
einval:
	errno = EINVAL;
	return -1;
}

/* how far @idx is behind @ncrx->head */
static int slot_dist(int idx, struct ncrx *ncrx)
{
	int dist = ncrx->head - idx;
	return dist >= 0 ? dist : dist + ncrx->p.nr_slots;
}

/* number of occupied slots */
static int nr_queued(struct ncrx *ncrx)
{
	return slot_dist(ncrx->tail, ncrx);
}

/* seq of the last queued message */
static uint64_t tail_seq(struct ncrx *ncrx)
{
	return ncrx->head_seq - nr_queued(ncrx);
}

/* slot index of a message with sequence number @ncrx->head_seq + @delta */
static int seq_delta_idx(struct ncrx *ncrx, int delta)
{
	int idx = ncrx->head + delta;

	if (idx < 0)
		return idx + ncrx->p.nr_slots;
	else if (idx >= ncrx->p.nr_slots)
		return idx - ncrx->p.nr_slots;
	else
		return idx;
}

/* is @slot completely empty? */
static int slot_is_free(struct ncrx_slot *slot)
{
	return !slot->msg && list_empty(&slot->hole_node);
}

/* @slot may have just been completed, if so, remove it from hole_list */
static void slot_maybe_complete(struct ncrx_slot *slot)
{
	struct ncrx_msg *msg = slot->msg;

	if (!msg || msg->ncfrag_left || list_empty(&slot->hole_node))
		return;

	list_del(&slot->hole_node);
}

/* retire the last queued slot whether complete or not */
static void retire_tail(struct ncrx *ncrx)
{
	int ntail = (ncrx->tail + 1) % ncrx->p.nr_slots;
	struct ncrx_slot *slot = &ncrx->slots[ncrx->tail];
	struct ncrx_slot *nslot = &ncrx->slots[ntail];

	if (slot->msg) {
		msg_list_append(slot->msg, &ncrx->retired_list);
		slot->msg = NULL;
	}

	list_del(&slot->hole_node);	/* free slot is never a hole */
	ncrx->tail = ntail;
	/*
	 * Activities of past msgs are considered activities for newer ones
	 * too.  This prevents oos interval verdicts from flipping as
	 * sequence progresses.
	 */
	nslot->timestamp = max(slot->timestamp, nslot->timestamp);
}

/* make room for message with seq ncrx->head_seq + @delta */
static void make_room(struct ncrx *ncrx, int delta)
{
	int i;

	/* head_seq is for the next msg, need to advance for 0 @delta too */
	for (i = 0; i <= delta; i++) {
		struct ncrx_slot *slot;
		int max_busy = ncrx->p.nr_slots - ncrx->p.retx_stride;

		/* a new slot is considered hole until it gets completed */
		slot = &ncrx->slots[ncrx->head];
		assert(slot_is_free(slot));
		list_append(&slot->hole_node, &ncrx->hole_list);
		slot->timestamp = ncrx->now_mono;
		slot->retx_timestamp = 0;

		/*
		 * Wind the ring buffer and push out if overflowed.  Always
		 * keep at least one stride empty so that retransmissions
		 * of expired slots don't count as oos.
		 */
		ncrx->head_seq++;
		ncrx->head = (ncrx->head + 1) % ncrx->p.nr_slots;
		if (slot_dist(ncrx->tail, ncrx) > max_busy)
			retire_tail(ncrx);
	}
}

/*
 * Get slot for @tmsg.  On success, returns pointer to the slot which may
 * be free or occupied with partial or complete message.  Returns NULL with
 * errno set to ERANGE if oos, NULL / ENOENT if already retired.
 */
static struct ncrx_slot *get_seq_slot(struct ncrx_msg *tmsg, struct ncrx *ncrx)
{
	struct ncrx_slot *slot;
	int64_t delta;
	int idx;

	/* new seq stream */
	if (!ncrx->head_seq) {
		ncrx->head_seq = tmsg->seq;
		ncrx->acked_seq = UINT64_MAX;
		tmsg->seq_reset = 1;
	}

	delta = tmsg->seq - ncrx->head_seq;

	/*
	 * Consider oos if outside reorder window or if the slot is
	 * complete and the last activity on it was more than oos_intv ago.
	 * Emergency messages are never considered oos as they don't follow
	 * the usual transmission pattern and may repeat indefinitely.
	 */
	if (-delta > ncrx->p.nr_slots || delta > ncrx->p.nr_slots) {
		errno = ERANGE;
		return NULL;
	}

	idx = seq_delta_idx(ncrx, delta);
	slot = &ncrx->slots[idx];

	if (-delta > nr_queued(ncrx)) {
		int is_free = slot_is_free(slot);

		if (!tmsg->emg &&
		    (!is_free ||
		     slot->timestamp + ncrx->p.oos_intv < ncrx->now_mono)) {
			errno = ERANGE;
			return NULL;
		}

		if (is_free)
			slot->timestamp = ncrx->now_mono;
		errno = ENOENT;
		return NULL;
	}

	make_room(ncrx, delta);
	slot->timestamp = ncrx->now_mono;

	return slot;
}

/* make @src's copy, if @src is a fragment, allocate full size as it may grow */
static struct ncrx_msg *copy_msg(struct ncrx_msg *src)
{
	struct ncrx_msg *dst;

	assert(!src->dict && !src->dict_len);

	dst = malloc(sizeof(*dst) + src->text_len + 1);
	if (!dst)
		return NULL;

	*dst = *src;
	init_list(&dst->node);

	dst->text = dst->buf;
	if (src->ncfrag_len) {
		memset(dst->text, 0, src->text_len + 1);
		memcpy(dst->text + src->ncfrag_off, src->text, src->ncfrag_len);
		dst->ncfrag_off = 0;
		dst->ncfrag_len = 0;
	} else {
		memcpy(dst->text, src->text, src->text_len);
		dst->text[dst->text_len] = '\0';
	}
	return dst;
}

/*
 * @tmsg is a newly parsed msg which is out-of-sequence.  Queue it on
 * @ncrx->oos_list until the message times out, gets pushed out by other
 * oos messages or the sequence stream gets reset.
 */
static int queue_oos_msg(struct ncrx_msg *tmsg, struct ncrx *ncrx)
{
	struct ncrx_slot *slot;
	struct ncrx_msg *msg, *nmsg, *first;

	msg = copy_msg(tmsg);
	if (!msg)
		return -1;

	msg_list_append(msg, &ncrx->oos_list);

	/*
	 * Shifted left automatically on each new msg.  Set oos and see if
	 * there have been too many oos among the last 32 messages.
	 */
	ncrx->oos_history |= 1;
	if ((signed)hweight32(ncrx->oos_history) < ncrx->p.oos_thr) {
		/* nope, handle oos overflow and handle */
		if (ncrx->oos_list.nr > NCRX_OOS_MAX) {
			msg = msg_list_pop(&ncrx->oos_list);
			msg->oos = 1;
			msg_list_append(msg, &ncrx->retired_list);
		}
		return 0;
	}

	/*
	 * The current sequence stream seems no good.  Let's reset by
	 * retiring all pending, picking the oos msg with the lowest seq,
	 * queueing it to reset the seq and then queueing all other oos
	 * msgs.  If a msg is still oos after reset, just retire it.
	 */
	while (ncrx->tail != ncrx->head)
		retire_tail(ncrx);

	ncrx->head_seq = 0;
	ncrx->acked_seq = UINT64_MAX;

	first = node_to_msg(ncrx->oos_list.head.next);
	msg_list_for_each(msg, nmsg, &ncrx->oos_list)
		first = msg->seq < first->seq ? msg : first;

	msg_list_del(first, &ncrx->oos_list);
	slot = get_seq_slot(first, ncrx);
	slot->msg = first;
	slot_maybe_complete(slot);

	while ((msg = msg_list_pop(&ncrx->oos_list))) {
		slot = get_seq_slot(msg, ncrx);
		if (slot) {
			slot->msg = msg;
			slot_maybe_complete(slot);
		} else {
			msg->oos = 1;
			msg_list_append(msg, &ncrx->retired_list);
		}
	}

	return 0;
}

/* @payload has just been received, parse and queue it */
static int ncrx_queue_payload(const char *payload, struct ncrx *ncrx,
		uint64_t now_real)
{
	struct ncrx_msg tmsg;
	struct ncrx_slot *slot;
	int new_msg = 0;

	if (parse_packet(payload, &tmsg))
		return -1;

	tmsg.rx_at_mono = ncrx->now_mono;
	tmsg.rx_at_real = now_real;
	ncrx->oos_history <<= 1;

	/* ack immediately if logging source is doing emergency transmissions */
	if (tmsg.emg) {
		ncrx->acked_seq = UINT64_MAX;
		ncrx->acked_at = 0;
	}

	/* get the matching slot and allocate a new message if empty */
	slot = get_seq_slot(&tmsg, ncrx);
	if (slot && !slot->msg) {
		slot->msg = copy_msg(&tmsg);
		new_msg = 1;
	}
	if (!slot || !slot->msg) {
		if (errno == ENOENT)
			return 0;
		if (errno == ERANGE)
			return queue_oos_msg(&tmsg, ncrx);
		return -1;
	}

	if (!new_msg && slot->msg->ncfrag_left) {
		struct ncrx_msg *msg = slot->msg;
		int off = tmsg.ncfrag_off;
		int i;

		for (i = 0; i < tmsg.ncfrag_len; i++) {
			if (msg->text[off + i])
				continue;
			msg->text[off + i] = tmsg.text[i];
			msg->ncfrag_left--;
		}
	}

	slot_maybe_complete(slot);

	return 0;
}

/*
 * Build ncrx_response() output.  Ack for the last retired msg is always
 * added.  If @slot is non-NULL, re-transmission for it is also added.
 */
static void ncrx_build_resp(struct ncrx_slot *slot, struct ncrx *ncrx)
{
	/* no msg received? */
	if (!ncrx->head_seq)
		return;

	/* "ncrx<ack-seq>" */
	if (!ncrx->resp_len) {
		ncrx->acked_seq = tail_seq(ncrx) - 1;
		ncrx->acked_at = ncrx->now_mono;

		ncrx->resp_len = snprintf(ncrx->resp_buf, NCRX_PKT_MAX,
					  "ncrx%"PRIu64, ncrx->acked_seq);
	}

	/* " <missing-seq>..." truncated to NCRX_PKT_MAX */
	if (slot) {
		int idx = slot - ncrx->slots;
		int len;

		len = snprintf(ncrx->resp_buf + ncrx->resp_len,
			       NCRX_PKT_MAX - ncrx->resp_len, " %"PRIu64,
			       ncrx->head_seq - slot_dist(idx, ncrx));
		if (ncrx->resp_len + len <= NCRX_PKT_MAX) {
			ncrx->resp_len += len;
			ncrx->resp_buf[ncrx->resp_len] = '\0';
		}
	}
}

int ncrx_process(const char *payload, uint64_t now_mono, uint64_t now_real,
		struct ncrx *ncrx)
{
	struct ncrx_slot *slot, *tmp_slot;
	struct ncrx_msg *msg;
	uint64_t old_head_seq = ncrx->head_seq;
	int dist_retx, ret = 0;

	if (now_mono < ncrx->now_mono)
		fprintf(stderr, "ncrx: time regressed %"PRIu64"->%"PRIu64"\n",
			ncrx->now_mono, now_mono);

	ncrx->now_mono = now_mono;
	ncrx->resp_len = 0;

	/*
	 * If fully acked, keep last ack timestamp current so that new
	 * messages arriving doesn't trigger ack timeout immediately.
	 */
	if (ncrx->acked_seq == tail_seq(ncrx) - 1)
		ncrx->acked_at = now_mono;

	/* parse and queue @payload */
	if (payload)
		ret = ncrx_queue_payload(payload, ncrx, now_real);

	/* retire complete & timed-out msgs from tail */
	while (ncrx->tail != ncrx->head) {
		slot = &ncrx->slots[ncrx->tail];

		if ((!slot->msg || !list_empty(&slot->hole_node)) &&
		    slot->timestamp + ncrx->p.msg_timeout > now_mono)
			break;
		retire_tail(ncrx);
	}

	/* retire timed-out oos msgs */
	while ((msg = msg_list_peek(&ncrx->oos_list))) {
		if (msg->rx_at_mono + ncrx->p.oos_timeout > now_mono)
			break;
		msg->oos = 1;
		msg_list_del(msg, &ncrx->oos_list);
		msg_list_append(msg, &ncrx->retired_list);
	}

	/* if enabled, ack pending and timeout expired? */
	if (ncrx->p.ack_intv && ncrx->acked_seq != tail_seq(ncrx) - 1 &&
	    ncrx->acked_at + ncrx->p.ack_intv < now_mono)
		ncrx_build_resp(NULL, ncrx);

	/* head passed one or more re-transmission boundaries? */
	dist_retx = old_head_seq / ncrx->p.retx_stride !=
		ncrx->head_seq / ncrx->p.retx_stride;

	hole_list_for_each(slot, tmp_slot, &ncrx->hole_list) {
		int retx = 0;

		/*
		 * If so, request re-tx of holes further away than stride.
		 * This ensures that a missing seq is requested at least
		 * certain number of times regardless of incoming rate.
		 */
		if (dist_retx &&
		    slot_dist(slot - ncrx->slots, ncrx) > ncrx->p.retx_stride)
			retx = 1;

		/* request re-tx every retx_intv */
		if (now_mono - max(slot->timestamp, slot->retx_timestamp) >=
		    (unsigned)ncrx->p.retx_intv) {
			slot->retx_timestamp = now_mono;
			retx = 1;
		}

		if (retx)
			ncrx_build_resp(slot, ncrx);
	}

	return ret;
}

const char *ncrx_response(struct ncrx *ncrx, int *lenp)
{
	if (lenp)
		*lenp = ncrx->resp_len;
	if (ncrx->resp_len)
		return ncrx->resp_buf;
	return NULL;
}

/* parse out the dictionary in a complete message, if it exists */
static void terminate_msg_and_dict(struct ncrx_msg *msg)
{
	msg->dict = strchr(msg->text, '\n');
	if (msg->dict) {
		int len = msg->text_len;
		msg->text_len = msg->dict - msg->text;
		msg->text[msg->text_len] = '\0';
		msg->dict_len = len - msg->text_len - 1;
		msg->dict++;
	}
}

struct ncrx_msg *ncrx_next_msg(struct ncrx *ncrx)
{
	struct ncrx_msg *msg = msg_list_pop(&ncrx->retired_list);

	if (msg)
		terminate_msg_and_dict(msg);

	return msg;
}

uint64_t ncrx_invoke_process_at(struct ncrx *ncrx)
{
	uint64_t when = UINT64_MAX;
	struct ncrx_msg *msg;

	/* ack enabled and pending? */
	if (ncrx->p.ack_intv && ncrx->head_seq &&
			ncrx->acked_seq != tail_seq(ncrx) - 1)
		when = min(when, ncrx->acked_at + ncrx->p.ack_intv);

	/*
	 * Holes to request for retransmission?  msg_timeout is the same
	 * condition but way longer.  Checking on retx_intv is enough.
	 */
	if (!list_empty(&ncrx->hole_list))
		when = min(when, ncrx->now_mono + ncrx->p.retx_intv);

	/* oos timeout */
	if ((msg = msg_list_peek(&ncrx->oos_list)))
		when = min(when, msg->rx_at_mono + ncrx->p.oos_timeout);

	/* min 10ms intv to avoid busy loop in case something goes bonkers */
	return max(when, ncrx->now_mono + 10);
}

struct ncrx *ncrx_create(const struct ncrx_param *param)
{
	const struct ncrx_param *dfl = &ncrx_dfl_param;
	struct ncrx_param *p;
	struct ncrx *ncrx;
	int i;

	ncrx = calloc(1, sizeof(*ncrx));
	if (!ncrx)
		return NULL;

	p = &ncrx->p;
	if (param) {
		p->nr_slots	= param->nr_slots	?: dfl->nr_slots;

		p->ack_intv	= param->ack_intv	?: dfl->ack_intv;
		p->retx_intv	= param->retx_intv	?: dfl->retx_intv;
		p->retx_stride	= param->retx_stride	?: dfl->retx_stride;
		p->msg_timeout	= param->msg_timeout	?: dfl->msg_timeout;

		p->oos_thr	= param->oos_thr	?: dfl->oos_thr;
		p->oos_intv	= param->oos_intv	?: dfl->oos_intv;
		p->oos_timeout	= param->oos_timeout	?: dfl->oos_timeout;
	} else {
		*p = *dfl;
	}

	ncrx->acked_seq = UINT64_MAX;
	init_list(&ncrx->hole_list);
	init_list(&ncrx->oos_list.head);
	init_list(&ncrx->retired_list.head);

	ncrx->slots = calloc(ncrx->p.nr_slots, sizeof(ncrx->slots[0]));
	if (!ncrx->slots)
		return NULL;

	for (i = 0; i < ncrx->p.nr_slots; i++)
		init_list(&ncrx->slots[i].hole_node);

	return ncrx;
}

void ncrx_destroy(struct ncrx *ncrx)
{
	struct ncrx_msg *msg;
	int i;

	for (i = 0; i < ncrx->p.nr_slots; i++)
		free(ncrx->slots[i].msg);

	while ((msg = msg_list_pop(&ncrx->oos_list)))
		free(msg);

	while ((msg = msg_list_pop(&ncrx->retired_list)))
		free(msg);

	free(ncrx->slots);
	free(ncrx);
}
