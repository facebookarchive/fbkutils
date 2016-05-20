/*
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#ifndef __NETCONSOLE_NCRX_STRUCT__
#define __NETCONSOLE_NCRX_STRUCT__

struct ncrx_list {
	struct ncrx_list	*next;
	struct ncrx_list	*prev;
};

/*
 * ncrx_msg represents a single log message and what gets returned from
 * ncrx_next_msg().  Most of the public fields are self-explanatory except
 * for the followings.
 *
 * oos
 *	The message's sequence number doesn't match up with the current
 *	message stream.  Could be from a foreign source or corrupt.  Ignore
 *	when counting missing messages.
 *
 * seq_reset
 *	The sequence number stream has jumped.  This usually happens when
 *	the log source reboots.  The first message returned after ncrx
 *	initialization always has this flag set.
 */
struct ncrx_msg {
	/* public fields */
	uint64_t		seq;		/* printk sequence number */
	uint64_t		ts_usec;	/* printk timestamp in usec */
	char			*text;		/* message body */
	char			*dict;		/* optional dictionary */
	int			text_len;	/* message body length */
	int			dict_len;	/* dictionary length */

	uint8_t			facility;	/* log facility */
	uint8_t			level;		/* printk level */
	unsigned		cont_start:1;	/* first of continued msgs */
	unsigned		cont:1;		/* continuation of prev msg */
	unsigned		oos:1;		/* sequence out-of-order */
	unsigned		seq_reset:1;	/* sequence reset */

	/* private fields */
	struct ncrx_list	node;
	uint64_t		rx_at_mono;	/* monotonic rx time in msec */
	uint64_t		rx_at_real;	/* real rx time in msec */
	int			ncfrag_off;	/* netconsole frag offset */
	int			ncfrag_len;	/* netconsole frag len */
	int			ncfrag_left;	/* number of missing bytes */

	unsigned		emg:1;		/* emergency transmission */

	char			buf[];
};

#endif /* __NETCONSOLE_NCRX_STRUCT__ */
