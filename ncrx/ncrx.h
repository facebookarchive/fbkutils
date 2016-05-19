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

#ifndef __NETCONSOLE_NCRX__
#define __NETCONSOLE_NCRX__

#include <inttypes.h>

#define NCRX_LINE_MAX		8192

/* max payload len for responses, this is what netconsole uses on tx side */
#define NCRX_PKT_MAX		1000

#include "ncrx-struct.h"

/*
 * ncrx parameters.  Specify NULL to use defaults for all.  Specify 0 to use
 * default for individual parameters.  All time periods are in millisecs.
 *
 * nr_slots
 *	The number of reorder slots.  This bounds the maximum memory which
 *	may be consumed by the ncrx instance.  Lowering this number
 *	increases the chance of the ordering window passing by a missing
 *	message before it can be obtained leading to missed messages.
 *
 * ack_intv
 *	A received message is acked after this period.  Transmission side
 *	ack timeout is 10s and this should be shorter than that.
 *
 * retx_intv
 *	Retransmission request is sent and repeated every this period.
 *
 * retx_stride
 *	A missing message generates retransmission request whenever it gets
 *	pushed back this number of slots by newly arriving message.
 *
 * msg_timeout
 *	A missing message expires after this period and the sequence number
 *	will be skipped in the output.
 *
 * oos_thr
 *	Among last 32 message, if more than this number of messages are
 *	out-of-order, the message stream is reset.
 *
 * oos_intv
 *	A message is considered out-of-sequence only if the last message
 *	received with the sequence number is older than this.
 *
 * oos_timeout
 *	If sequence is not reset in this period after reception of an
 *	out-of-order message, the message is output.
 */
struct ncrx_param {
	int			nr_slots;

	int			ack_intv;
	int			retx_intv;
	int			retx_stride;
	int			msg_timeout;

	int			oos_thr;
	int			oos_intv;
	int			oos_timeout;
};

/* default params */
#define NCRX_DFL_NR_SLOTS	8192

#define NCRX_DFL_ACK_INTV	0	/* disable ack logic by default */

#define NCRX_DFL_RETX_INTV	1000
#define NCRX_DFL_RETX_STRIDE	256
#define NCRX_DFL_MSG_TIMEOUT	30000

#define NCRX_DFL_OOS_THR	(32 * 3 / 5)			/* 19 */
#define NCRX_DFL_OOS_INTV	5000
#define NCRX_DFL_OOS_TIMEOUT	NCRX_DFL_MSG_TIMEOUT

/*
 * A ncrx instance is created by ncrx_create() and destroyed by
 * ncrx_destroy().  All accesses to a given instance must be serialized;
 * however, a process may create any number of instances and use them
 * concurrently.
 */
struct ncrx;

struct ncrx *ncrx_create(const struct ncrx_param *param);
void ncrx_destroy(struct ncrx *ncrx);

/*
 * A ncrx instance doesn't do any IO or blocking.  It's just a state
 * machine that the user can feed data into and get the results out of.
 *
 * ncrx_process()
 *	Process @payload of a packet.  @now_mono is the current time in msecs.
 *	The origin doesn't matter as long as it's monotonously increasing.
 *	@payload may be NULL.  See ncrx_invoke_process_at().
 *
 *	@now_real is an optional timestamp which will be stored at rx_at_real
 *	in the resulting ncrx_msg struct. The library does not use this value
 *	at all, so it can be zero.
 *
 *	Returns 0 on success.  1 on failure with errno set.  EINVAL
 *	indicates that @payload is not a valid extended netconsole message.
 *
 * ncrx_response()
 *	The response to send to log source.  If the user calls this
 *	function after each ncrx_process() invocation and sends back the
 *	output, re- and emergency transmissions are activated increasing
 *	the reliability especially if the network is flaky.  If not, ncrx
 *	will passively reorder and assemble messages.
 *
 *	Returns pointer to '\0' terminated response string or NULL if
 *	there's nothing to send back.  If @lenp is not NULL, *@lenp is set
 *	to the length of the response string.
 *
 * ncrx_next_msg()
 *	Fetches the next completed message.  Call repeatedly until NULL is
 *	returned after each ncrx_process() invocation.  Each message should
 *	be free()'d by the user after consumption.
 *
 * ncrx_invoke_process_at()
 *	Message processing is timing dependent and ncrx often needs to take
 *	actions after a certain time period even when there hasn't been any
 *	new packets.  This function indicates when the caller should invoke
 *	ncrx_process() at the latest.
 *
 *	The returned time is relative to @now previously provided to
 *	ncrx_process().  e.g. if ncrx_process() needs to be invoked after 4
 *	seconds since the last invocation where @now was 60000, this
 *	function will return 64000.  Returns UINT64_MAX if there's no
 *	pending timing dependent operation.
 *
 * See tools/ncrx/ncrx.c for a simple example.
 */
int ncrx_process(const char *payload, uint64_t now_mono, uint64_t now_real,
		struct ncrx *ncrx);
const char *ncrx_response(struct ncrx *ncrx, int *lenp);
struct ncrx_msg *ncrx_next_msg(struct ncrx *ncrx);
uint64_t ncrx_invoke_process_at(struct ncrx *ncrx);

#endif	/* __NETCONSOLE_NCRX__ */
