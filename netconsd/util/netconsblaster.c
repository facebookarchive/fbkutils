/*
 * netconsblaster: A test excerciser for netconsd
 *
 * This exists to act as a comprehensive test case for the netconsd daemon. At
 * present it's anything but comprehensive, but better than nothing.
 *
 * Copyright (C) 2016, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the LICENSE
 * file in the root directory of this source tree. An additional grant of patent
 * rights can be found in the PATENTS file in the same directory.
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <pthread.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/ip6.h>
#include <netinet/udp.h>

static inline unsigned long now_epoch_ms(void)
{
	struct timespec t;

	clock_gettime(CLOCK_REALTIME, &t);
	return t.tv_sec * 1000 + t.tv_nsec / 1000000L;
}

static struct params {
	int srcaddr_order;
	int nr_threads;
	struct in6_addr src;
	struct in6_addr dst;
	long blastcount;

	int stop_blasting;
} params;

static int ones_complement_sum(unsigned short *data, int len, int sum)
{
	unsigned int tmp;
	int i;

	for (i = 0; i < len / 2; i++) {
		tmp = ntohs(data[i]);

		/*
		 * Kill -0
		 */
		if (tmp == 65535)
			tmp = 0;

		sum += tmp;
		if (sum >= 65536) {
			sum &= 65535;
			sum++;
		}
	}

	if (len & 1) {
		puts("Calvin is lazy\n");
		abort();
	}

	return sum;
}

/*
 * From RFC768: "Checksum is the 16-bit one's complement of the one's
 * complement sum of a pseudo header of information from the IP header, the UDP
 * header, and the data, padded with zero octets at the end (if necessary) to
 * make a multiple of two octets."
 *
 * See RFC2460 section 8.1 for definition of pseudoheader for IPv6.
 *
 * In case you're wondering why I bothered with this: "Unlike IPv4, when UDP
 * packets are originated by an IPv6 node, the UDP checksum is NOT optional.
 * IPv6 receivers MUST discard packets containing a zero checksum."
 *
 * @addrs: Pointer to the begnning of the src/dst addresses in the ipv6hdr
 * @udppkt: Pointer to the udphdr
 * @len: Length of the udphdr and its payload
 */
static int udp_csum(void *addrptr, void *udppkt, int len)
{
	unsigned int sum = 0;
	unsigned short *addrs = addrptr;
	unsigned short pseudohdr[4] = {0, htons(len), 0, htons(IPPROTO_UDP)};

	sum = ones_complement_sum(addrs, 32, 0);
	sum = ones_complement_sum(pseudohdr, 8, sum);
	sum = ones_complement_sum(udppkt, len, sum);
	sum = ~sum;

	/*
	 * From RFC768: "If the computed checksum is zero, it is transmitted as
	 * all ones. An all zero transmitted checksum value means that the
	 * transmitter generated no checksum"
	 */
	if (sum == 0)
		sum = 65535;

	return sum;
}

static int write_message(int sockfd, struct in6_addr *src, struct in6_addr *dst,
		const char *payload, int len)
{
	struct sockaddr_in6 bogus = {
		.sin6_family = AF_INET6,
	};

	char raw[sizeof(struct ip6_hdr) + sizeof(struct udphdr) + len];
	struct ip6_hdr *ipv6hdr = (void*)raw;
	struct udphdr *udphdr = (void*)&raw[sizeof(*ipv6hdr)];
	char *data = &raw[sizeof(*ipv6hdr) + sizeof(*udphdr)];

	memset(raw, 0, sizeof(*ipv6hdr) + sizeof(*udphdr));

	memcpy(&ipv6hdr->ip6_src, src, sizeof(*src));
	memcpy(&ipv6hdr->ip6_dst, dst, sizeof(*dst));
	ipv6hdr->ip6_vfc |= (6 << 4);
	ipv6hdr->ip6_nxt = IPPROTO_UDP;
	ipv6hdr->ip6_plen = htons(sizeof(*udphdr) + len);
	ipv6hdr->ip6_hlim = 64;

	memcpy(data, payload, len);

	udphdr->source = htons(6666);
	udphdr->dest = htons(1514);
	udphdr->len = htons(sizeof(*udphdr) + len);
	udphdr->check = htons(udp_csum(&ipv6hdr->ip6_src, udphdr,
			sizeof(*udphdr) + len));

	/*
	 * FIXME: Figure out what the fuck is going on here...
	 */
	memcpy(&bogus.sin6_addr, dst, sizeof(*dst));
	return sendto(sockfd, raw, sizeof(raw), 0, &bogus, sizeof(bogus));
}


static int get_raw_socket(void)
{
	int fd;

	fd = socket(AF_INET6, SOCK_RAW, IPPROTO_RAW);
	if (fd == -1) {
		printf("Couldn't get raw socket: %m\n");
		abort();
	}

	return fd;
}

/*
 * Randomly flip the lowest @bits in @addr
 */
static void permute_addr(struct in6_addr *addr, int bits, unsigned int *rstate)
{
	int i;

	for (i = 15; i >= 0; i--) {
		if (bits < 8)
			break;

		addr->s6_addr[i] ^= rand_r(rstate) & 255;
		bits -= 8;
	}

	if (bits)
		addr->s6_addr[i] ^= rand_r(rstate) & ((1 << bits) - 1);
}

static void *blast(void *arg)
{
	struct params *p = arg;
	int fd, ret, len;
	unsigned int rstate;
	struct in6_addr src;
	char *bullshit;
	long count = 0;

	memcpy(&src, &p->src, sizeof(src));
	fd = get_raw_socket();
	bullshit = "abcdefghijklmnopqrstuvwxyz1234567890";
	len = strlen(bullshit);
	rstate = pthread_self();

	while (!p->stop_blasting) {
		permute_addr(&src, p->srcaddr_order, &rstate);
		ret = write_message(fd, &src, &p->dst, bullshit, len);

		if (ret > 0)
			count++;

		if (p->blastcount && count == p->blastcount)
			break;
	}

	return (void*)count;
}

static void parse_arguments(int argc, char **argv, struct params *p)
{
	int i;

	/*
	 * Defaults
	 */
	p->srcaddr_order = 16;
	p->nr_threads = 1;
	memcpy(&p->src, &in6addr_loopback, sizeof(in6addr_loopback));
	memcpy(&p->dst, &in6addr_loopback, sizeof(in6addr_loopback));
	p->blastcount = 0;

	p->stop_blasting = 0;

	while ((i = getopt(argc, argv, "o:s:d:t:n:")) != -1) {
		switch(i) {
		case 'o':
			/*
			 * Controls the number of bits to randomly flip in the
			 * actual IPv6 address of this machine. So the program
			 * will effectively simulate 2^N clients.
			 */
			p->srcaddr_order = atoi(optarg);
			break;
		case 's':
			if (inet_pton(AF_INET6, optarg, &p->src) != 1) {
				printf("Bad src '%s': %m\n", optarg);
				abort();
			}
			break;
		case 'd':
			if (inet_pton(AF_INET6, optarg, &p->dst) != 1) {
				printf("Bad dst '%s': %m\n", optarg);
				abort();
			}
			break;
		case 't':
			p->nr_threads = atoi(optarg);
			break;
		case 'n':
			p->blastcount = atol(optarg);
			break;
		default:
			puts("Invalid command line parameters");
			abort();
		}
	}
}

static void stop_signal(int signum)
{
	params.stop_blasting = 1;
}

int main(int argc, char **argv)
{
	int i, ret;
	pthread_t *ids;
	unsigned long tmp, count, start, finish;
	struct sigaction stopper = {
		.sa_handler = stop_signal,
		.sa_flags = SA_RESETHAND,
	};

	parse_arguments(argc, argv, &params);
	sigaction(SIGINT, &stopper, NULL);

	ids = calloc(params.nr_threads, sizeof(*ids));
	start = now_epoch_ms();
	for (i = 0; i < params.nr_threads; i++) {
		ret = pthread_create(&ids[i], NULL, blast, &params);
		if (ret) {
			printf("Couldn't spawn thread: %d\n", ret);
			abort();
		}
	}

	count = 0;
	for (i = 0; i < params.nr_threads; i++) {
		pthread_join(ids[i], (void**)&tmp);
		count += tmp;
	}
	finish = now_epoch_ms();

	printf("Wrote %lu packets (%lu pkts/sec)\n", count,
			count / ((finish - start) / 1000));
	return 0;
}
