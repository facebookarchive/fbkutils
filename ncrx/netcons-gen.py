#!/usr/bin/env python3

"""
This tool produces netcons messages for testing (mostly of {lib,}ncrx).

Usual usage:

1. Run `ncrx [port]` listening in one shell
2. In another shell, run `netcons-gen [...] | nc -u 127.0.0.1 [port]`
"""

import argparse
import random
import sys
import time
from enum import Enum


class Level(Enum):
    LOG_EMERG = 0
    LOG_ALERT = 1
    LOG_CRIT = 2
    LOG_ERR = 3
    LOG_WARNING = 4
    LOG_NOTICE = 5
    LOG_INFO = 6
    LOG_DEBUG = 7


class Facility(Enum):
    LOG_KERN = 0
    LOG_USER = 1
    LOG_MAIL = 2
    LOG_DAEMON = 3
    LOG_AUTH = 4
    LOG_SYSLOG = 5
    LOG_LPR = 6
    LOG_NEWS = 7
    LOG_UUCP = 8
    LOG_CRON = 9
    LOG_AUTHPRIV = 10

    LOG_LOCAL0 = 16
    LOG_LOCAL1 = 17
    LOG_LOCAL2 = 18
    LOG_LOCAL3 = 19
    LOG_LOCAL4 = 20
    LOG_LOCAL5 = 21
    LOG_LOCAL6 = 22
    LOG_LOCAL7 = 23


class Mode(Enum):
    NORMAL = 0
    SKIP = 1
    RESET = 2


ARG_TO_MODE_MAP = {"reset": Mode.RESET, "skip": Mode.SKIP}


def make_dictionary_string(msg):
    """Format X=Y\0X=Y, no trailing \0"""
    return "\0".join("{}={}".format(k, v) for k, v in msg.items())


def make_ext_header(seq, facility, level, cont):
    """
    See printk.c's msg_print_ext_header for format spec.
    """

    faclev = (facility.value << 3) | level.value
    ts_usec = int(time.monotonic() * (10 ** 6))
    return "{},{},{},{};".format(faclev, seq, ts_usec, "c" if cont else "-")


def _body_escape(text):
    return text.replace("\0", "\n")


def make_ext_body(text, dict_str):
    """
    See printk.c's msg_print_ext_body for format spec.

    Escaping of unprintables is currently unimplemented.
    """
    return "{}\n{}".format(_body_escape(text), _body_escape(dict_str))


def make_netcons_msg(
    seq=0,
    facility=Facility.LOG_KERN,
    level=Level.LOG_ERR,
    cont=False,
    text="text",
    meta_dict=None,
):
    if meta_dict is None:
        meta_dict = {"DICT": "test"}

    dict_str = make_dictionary_string(meta_dict)

    header = make_ext_header(seq=seq, facility=facility, level=level, cont=cont)
    body = make_ext_body(text=text, dict_str=dict_str)

    return "{}{}".format(header, body)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip", action="store_true", help="Randomly skip sequence numbers"
    )
    parser.add_argument(
        "--reset", action="store_true", help="Randomly reset the sequence to 0 again"
    )
    parser.add_argument(
        "--cont", action="store_true", help="Randomly insert LOG_CONT messages"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    enabled_modes = [Mode.NORMAL]

    for arg_name, mode in ARG_TO_MODE_MAP.items():
        if getattr(args, arg_name):
            enabled_modes.append(mode)

    seq = 0
    cont = False

    while True:
        print(
            make_netcons_msg(
                seq=seq, text="hi", meta_dict={"UNAME": "it's minix i swear"}, cont=cont
            ),
            flush=True,
        )

        chosen_mode = random.choice(enabled_modes)

        if chosen_mode == Mode.NORMAL:
            new_seq = seq + 1
        elif chosen_mode == Mode.SKIP:
            new_seq = seq + random.randint(1, 5)
        elif chosen_mode == Mode.RESET:
            new_seq = 0

        if args.cont:
            cont = random.choice([True, False])

        print(
            "seq: {} -> {}, mode: {}, cont: {}".format(seq, new_seq, chosen_mode, cont),
            file=sys.stderr,
        )
        seq = new_seq

        time.sleep(0.5)
