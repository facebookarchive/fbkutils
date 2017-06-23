#!/usr/bin/env python3

import sys


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
