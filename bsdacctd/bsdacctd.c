/*
 * Copyright (C) 2019, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/syscall.h>

#include <sched.h>
#include <asm/types.h>
#include <linux/netlink.h>
#include <linux/genetlink.h>
#include <linux/taskstats.h>
#include <linux/acct.h>

#define log(...) do { if (0) fprintf(stderr, __VA_ARGS__); } while (0)
#define err(...) do { fprintf(stderr, __VA_ARGS__); } while (0)
#define fatal(...) do { err(__VA_ARGS__); abort(); } while (0)

/*
 * 2MB, need a clean multiple of the size to avoid splitting records.
 */
static const long acctfile_buffer = 32768 * sizeof(struct acct_v3);

/*
 * Netlink "constants"
 */
static const struct sockaddr_nl nladdr = {.nl_family = AF_NETLINK, };
static __u16 taskstats_family;

static int get_nlsocket(int tx, int rx)
{
	int fd = socket(AF_NETLINK, SOCK_RAW, NETLINK_GENERIC);

	if (fd == -1)
		fatal("Couldn't allocate socket: %m\n");

	if (tx && setsockopt(fd, SOL_SOCKET, SO_SNDBUF, &tx, sizeof(tx)))
		fatal("Couldn't expand txbuf: %m\n");

	if (rx && setsockopt(fd, SOL_SOCKET, SO_RCVBUF, &rx, sizeof(rx)))
		fatal("Couldn't expand rxbuf: %m\n");

	return fd;
}

/*
 * PID_AGGR and friends don't set the nested-attribute bit as they should, so
 * we can't parse the responses without assuming a priori they contain nested
 * attrs, oh well.
 */
struct taskstat_aggr {
	struct nlattr __pidhdr;
	__u32 pid;
	struct nlattr __statshdr;
	struct taskstats stats;
} __attribute__((packed));

struct attribute {
	struct nlattr attr;
	union {
		struct taskstat_aggr aggr[0];
		__u16 u16[0];
		char str[0];
	};
} __attribute__((packed));

struct netlink_response {
	struct nlmsghdr nl;
	union {
		struct {
			struct genlmsghdr gnl;
			struct attribute attrs[0];
		} __attribute__((packed));
		struct nlmsgerr err;
	};
} __attribute__((packed));

#define for_each_attribute(cur, resp, len) for ( \
	cur = (void *)resp->attrs; \
	(char *)cur < (char *)resp + len; \
	cur += NLA_ALIGN(cur->attr.nla_len) / sizeof(struct nlattr))

/*
 * Family ID depends on kernel initcall order, you have to look it up.
 */

struct taskstats_family_request {
	struct nlmsghdr nl;
	struct genlmsghdr gnl;
	struct nlattr attr;
	char n[NLA_ALIGN(sizeof(TASKSTATS_GENL_NAME))];
} __attribute__((packed));

static void load_family(void)
{
	const struct taskstats_family_request msg = {
		.nl = {
			.nlmsg_len = sizeof(msg),
			.nlmsg_type = GENL_ID_CTRL,
			.nlmsg_flags = NLM_F_REQUEST,
			.nlmsg_seq = 0,
			.nlmsg_pid = getpid(),
		},
		.gnl = {
			.cmd = CTRL_CMD_GETFAMILY,
			.version = 1,
		},
		.attr = {
			.nla_len = NLA_ALIGN(sizeof(struct nlattr) +
					     sizeof(TASKSTATS_GENL_NAME)),
			.nla_type = CTRL_ATTR_FAMILY_NAME,
		},
		.n = TASKSTATS_GENL_NAME,
	};
	struct netlink_response *resp;
	struct attribute *cur;
	int fd, ret;

	fd = get_nlsocket(0, 0);

	ret = sendto(fd, &msg, sizeof(msg), 0, (void *)&nladdr, sizeof(nladdr));
	if (ret != sizeof(msg))
		fatal("Can't ask for family: %d (%m)\n", ret);

	resp = alloca(1024);
	memset(resp, 0, 1024);

	ret = recv(fd, resp, 1024, 0);
	if (ret == -1)
		fatal("Can't get family: %d (%m)\n", ret);

	close(fd);

	if (!NLMSG_OK(&resp->nl, ret))
		fatal("Truncated family response\n");

	if (resp->nl.nlmsg_type == NLMSG_ERROR)
		fatal("Error in family response: %d (%s)\n", resp->err.error,
		      strerror(-resp->err.error));

	if (resp->nl.nlmsg_type != GENL_ID_CTRL)
		fatal("Unexpected response type: %d\n", resp->nl.nlmsg_type);

	log("Received valid %d byte family response\n", ret);

	for_each_attribute(cur, resp, ret) {
		switch (cur->attr.nla_type) {
		case CTRL_ATTR_FAMILY_ID:
			log("Family ID for taskstats: %d\n", *cur->u16);
			taskstats_family = *cur->u16;
			return;
		case CTRL_ATTR_FAMILY_NAME:
			log("Family name for taskstats: %s\n", cur->str);
			continue;
		default:
			err("Unknown attrtype %d\n", cur->attr.nla_type);
		}
	}

	fatal("No CTRL_ATTR_FAMILY_ID in response\n");
}

#define CPUMASK_SIZE (sizeof("0-999") + 1)

struct taskstats_register_request {
	struct nlmsghdr nl;
	struct genlmsghdr gnl;
	struct nlattr attr;
	char n[NLA_ALIGN(CPUMASK_SIZE)];
} __attribute__((packed));

static int taskstats_register(__u32 port)
{
	struct taskstats_register_request msg = {
		.nl = {
			.nlmsg_len = sizeof(msg),
			.nlmsg_type = taskstats_family,
			.nlmsg_flags = NLM_F_REQUEST,
			.nlmsg_seq = 0,
			.nlmsg_pid = port,
		},
		.gnl = {
			.cmd = TASKSTATS_CMD_GET,
			.version = 1,
		},
		.attr = {
			.nla_len = NLA_ALIGN(sizeof(struct nlattr) +
					     CPUMASK_SIZE),
			.nla_type = TASKSTATS_CMD_ATTR_REGISTER_CPUMASK,
		},
	};
	int fd, ret;

	/*
	 * Extra NUL padding at the end doesn't matter
	 */
	snprintf(msg.n, CPUMASK_SIZE, "0-%ld",
		 sysconf(_SC_NPROCESSORS_ONLN) - 1);

	fd = get_nlsocket(0, 1 * 1024 * 1024);
	ret = sendto(fd, &msg, sizeof(msg), 0, (void*)&nladdr, sizeof(nladdr));
	if (ret != sizeof(msg))
		fatal("Can't register: %d (%m)\n", ret);

	return fd;
}

/*
 * Returns a pointer into @resp
 */
static struct taskstats *taskstats_recv(int fd, void *buf, int len)
{
	struct netlink_response *resp = buf;
	struct attribute *cur;
	int ret;

	memset(resp, 0, len);
	ret = recv(fd, resp, len, 0);
	if (ret == -1) {
		switch (errno) {
		case ENOBUFS:
		case EAGAIN:
			log("Transient error: %m\n");
			return NULL;
		default:
			fatal("Fatal error: %m\n");
		}
	}

	if (!NLMSG_OK(&resp->nl, ret))
		fatal("Truncated taskstats response\n");

	if (resp->nl.nlmsg_type == NLMSG_ERROR) {
		const char *str = strerror(-resp->err.error);
		int err = resp->err.error;

		if (err >= 0) {
			err("NLMSG_ERROR set, but no error? (%d)\n", err);
			return NULL;
		}

		switch (err) {
		case -EAGAIN:
		case -ESRCH:
			err("Transient netlink error: %s (%d)\n", str, err);
			return NULL;
		default:
			fatal("Fatal netlink error: %s (%d)\n", str, err);
		}
	}

	log("Received valid %d byte taskstats response\n", ret);
	for_each_attribute(cur, resp, ret) {
		__u16 type = cur->attr.nla_type;
		__u16 len = cur->attr.nla_len;
		struct taskstats *tsk;

		log("Attr at %p: type=%d, len=%d\n", cur, type, len);

		switch(type) {
		case TASKSTATS_TYPE_AGGR_TGID:
			/*
			 * BSD Accounting only deals with process group leaders,
			 * so we ignore results for thread IDs.
			 */
			continue;

		case TASKSTATS_TYPE_AGGR_PID:
			tsk = &cur->aggr->stats;

			if (tsk->version < TASKSTATS_VERSION)
				fatal("Bad version: %d, need >=%d\n",
				      tsk->version, TASKSTATS_VERSION);

			log("pid=%u comm='%s'\n", cur->aggr->pid, tsk->ac_comm);
			return tsk;

		case TASKSTATS_TYPE_NULL:
			log("NULL attribute, how weird\n");
			continue;

		default:
			log("Unknown attribute: type=%d, len=%d\n", type, len);
			continue;
		}
	}

	return NULL;
}

static int open_acctfile(const char *p)
{
	int ret;

	ret = open(p, O_WRONLY | O_APPEND | O_CREAT, 0400);
	if (ret == -1)
		fatal("Can't open '%s': %m\n", p);

	return ret;
}

/*
 * To avoid any need to coordinate with consumers, we let st_size grow
 * monotonically, and punch holes off the front of the file as we go. We
 * maintain at least @acctfile_buffer bytes trailing the offset of the next
 * record to be written.
 *
 * The consumer is allowed to truncate the file to zero length: O_APPEND writes
 * are atomic, so that part works out. The fallocate() action cannot be atomic
 * in the same way (becuse we must obtain one of its args from fstat()), but
 * punching holes past st_size is harmless, so we don't have to care.
 */
static long trim_acctfile(int fd, long sz)
{
	long off, realsz, punch_offset;
	struct stat s;

	/*
	 * Let st_blocks grow to double the minimum trailing limit before doing
	 * anything. Per below, if the consumer has truncated the file, we will
	 * pass this check strictly *sooner* than necessary.
	 */
	if (sz < acctfile_buffer * 2)
		return sz;

	/*
	 * Get the real st_size/st_blocks, the file may have been truncated.
	 */
	if (fstat(fd, &s))
		fatal("Can't fstat: %m\n");

	realsz = s.st_blocks * 512;
	off = s.st_size;

	/*
	 * If it was truncated, our check will have been a bit early: just
	 * return the new st_blocks, so we'll try again at the right time.
	 */
	if (realsz < acctfile_buffer * 2)
		return realsz;

	/*
	 * Okay, time to actually punch a hole.
	 *
	 * If the file was truncated between the fstat() call and now, this
	 * will punch a hole beyond st_size, which is harmless.
	 */
	punch_offset = realsz > off ? 0UL : off - realsz;
	if (fallocate(fd, FALLOC_FL_PUNCH_HOLE | FALLOC_FL_KEEP_SIZE,
		      punch_offset, acctfile_buffer))
		fatal("Can't punch hole: %m\n");

	/*
	 * The number we return may be bogus, but if bogus, it strictly
	 * overestimates the actual st_blocks value. So we will call fstat()
	 * earlier than necessary and "fix" it.
	 */
	return realsz - acctfile_buffer;
}

static comp_t encode_comp_t(unsigned long value)
{
	unsigned long mantsize = 13;
	unsigned long expsize = 3;
	unsigned long maxfract = ((1 << mantsize));
	int exp, rnd;

	exp = rnd = 0;
	while (value > maxfract) {
		rnd = value & (1UL << (expsize - 1));
		value >>= expsize;
		exp++;
	}

	if (rnd && (++value > maxfract)) {
		value >>= expsize;
		exp++;
	}

	exp <<= mantsize;
	exp += value;
	return exp;
}

/*
 * For BSD acct_v3 the tick is always 100HZ, so we convert to centiseconds.
 */

static comp_t usec_to_AHZ(unsigned long val)
{
	return encode_comp_t(val / 10000UL);
}

/*
 * Leave ac_io, ac_rw, and ac_swaps as zeros, just like the kernel does. We
 * don't get the TTY in taskstats, so ac_tty is also zeros.
 */
static void fill_acct(struct acct_v3 *dst, const struct taskstats *src)
{
	memset(dst, 0, sizeof(*dst));

	*dst = (struct acct_v3){
		.ac_flag = src->ac_flag,
		.ac_version = 3,
		.ac_exitcode = src->ac_exitcode,
		.ac_uid = src->ac_uid,
		.ac_gid = src->ac_gid,
		.ac_pid = src->ac_pid,
		.ac_ppid = src->ac_ppid,
		.ac_btime = src->ac_btime,
		.ac_etime = usec_to_AHZ(src->ac_etime),
		.ac_utime = usec_to_AHZ(src->ac_utime),
		.ac_stime = usec_to_AHZ(src->ac_stime),
		.ac_minflt = encode_comp_t(src->ac_minflt),
		.ac_majflt = encode_comp_t(src->ac_majflt),

		/*
		 * This is a very slight behavior change: rather than just
		 * storing VSIZE at exit time like the kernel does, we store
		 * the largest value of VSIZE the task ever saw.
		 */
		.ac_mem = encode_comp_t(src->hiwater_vm),
	};

	strncpy(dst->ac_comm, src->ac_comm, ACCT_COMM - 1);
}

int main(int argc, char **argv)
{
	int netlink_fd, acct_fd;
	long acctsz;

	if (argc < 2)
		fatal("Usage: %s /path/to/acctfile\n", argv[0]);

	if (getuid())
		fatal("Run as root\n");

	acct_fd = open_acctfile(argv[1]);
	acctsz = 0;

	load_family();
	netlink_fd = taskstats_register(getpid());

	while (1) {
		struct taskstats *tsk;
		struct acct_v3 bsd;
		char buf[1024];
		int ret;

		tsk = taskstats_recv(netlink_fd, buf, sizeof(buf));
		if (!tsk)
			continue;

		fill_acct(&bsd, tsk);

		/*
		 * The kernel doesn't batch writes, so we don't either.
		 */
		ret = write(acct_fd, &bsd, sizeof(bsd));
		if (ret != sizeof(bsd))
			fatal("Bad write: %m\n");

		acctsz = trim_acctfile(acct_fd, acctsz + ret);
	}

	return 0;
}
