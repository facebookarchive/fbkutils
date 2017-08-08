#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from benchpress.lib.parser import Parser


class ReturncodeParser(Parser):
    """Returncode parser outputs one metric 'success' that is True if job binary
    had a 0 exit code, and False all other times."""

    def parse(self, stdout, stderr, returncode):
        return {
            'success': returncode == 0,
        }
