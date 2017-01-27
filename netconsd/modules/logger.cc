/* logger.cc: Very simple example C++ netconsd module
 *
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#include <cstdlib>
#include <cstring>
#include <functional>
#include <unordered_map>

#include <fcntl.h>
#include <netdb.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>

#include <msgbuf-struct.h>
#include <ncrx-struct.h>

#include <jhash.h>

/*
 * The below allows us to index an unordered_map by an IP address.
 */

static bool operator==(const struct in6_addr& lhs, const struct in6_addr& rhs)
{
	return std::memcmp(&lhs, &rhs, 16) == 0;
}

namespace std {

template<> struct hash<struct in6_addr>
{
	std::size_t operator()(struct in6_addr const& s) const
	{
		return jhash2((uint32_t*)&s, sizeof(s) / sizeof(uint32_t),
				0xbeefdead);
	}
};

} /* namespace std */

/*
 * Basic struct to hold the hostname and the FD for its logfile.
 */
struct logtarget {
	char hostname[48];
	int fd;

	/*
	 * Resolve the hostname, and open() an appropriately named file to
	 * write the logs into.
	 */
	logtarget(struct in6_addr *src)
	{
		int ret;
		struct sockaddr_in6 sa = {
			.sin6_family = AF_INET6,
			.sin6_port = 0,
		};

		memcpy(&sa.sin6_addr, src, sizeof(*src));
		ret = getnameinfo((const struct sockaddr *)&sa, sizeof(sa),
				hostname, 48, NULL, 0, NI_NAMEREQD);
		if (ret)
			inet_ntop(AF_INET6, src, hostname, sizeof(*src));

		ret = open(hostname, O_TRUNC|O_WRONLY|O_CREAT, 0644);
		if (ret == -1) {
			fprintf(stderr, "FATAL: open() failed: %m\n");
			abort();
		}

		fd = ret;
	}

	/*
	 * Close the file
	 */
	~logtarget(void)
	{
		close(fd);
	}
};

/*
 * This relates the IP address of the remote host to its logtarget struct.
 */
static std::unordered_map<struct in6_addr, struct logtarget> *maps;

/*
 * Return the existing logtarget struct if we've seen this host before; else,
 * initialize a new logtarget, insert it, and return that.
 */
static struct logtarget& get_target(int thread_nr, struct in6_addr *src)
{
	auto itr = maps[thread_nr].find(*src);
	if (itr == maps[thread_nr].end())
		return maps[thread_nr].emplace(*src, src).first->second;

	return itr->second;
}

/*
 * Actually write the line to the file
 */
static void write_log(struct logtarget& tgt, struct msgbuf *buf,
		struct ncrx_msg *msg)
{
	if (!msg)
		dprintf(tgt.fd, "%s\n", buf->buf);
	else
		dprintf(tgt.fd, "%06lu %014lu %d %d %s%s%s%s%s\n", msg->seq,
			msg->ts_usec, msg->facility, msg->level,
			msg->cont_start ? "[CONT START] " : "",
			msg->cont ? "[CONT] " : "",
			msg->oos ? "[OOS] ": "",
			msg->seq_reset ? "[SEQ RESET] " : "",
			msg->text);
}

extern "C" int netconsd_output_init(int nr)
{
	maps = new std::unordered_map<struct in6_addr, struct logtarget>[nr];
	return 0;
}

extern "C" void netconsd_output_exit(void)
{
	delete[] maps;
}

/*
 * This is the actual function called by netconsd.
 */
extern "C" void netconsd_output_handler(int t, struct in6_addr *src,
		struct msgbuf *buf, struct ncrx_msg *msg)
{
	struct logtarget& cur = get_target(t, src);
	write_log(cur, buf, msg);
}
