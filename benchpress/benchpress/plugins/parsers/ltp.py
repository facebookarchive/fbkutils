#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from benchpress.lib.parser import Parser

import re

# <test name> <number> <status> : <extra stuff>
test_format_re = re.compile('\\w+\\s+\\d+\\s+T(FAIL|PASS|BROK|WARN|INFO).*')


class LtpParser(Parser):

    def parse(self, stdout, stderr, returncode):
        # ltp run in quiet mode produces lines that are mostly a single line per
        # test with the test name and a status and optional message
        metrics = {}

        for line in stdout:
            # make sure that the line matches the format of a test
            if not test_format_re.match(line):
                continue

            line = line.split()
            # combine 0 and 1 because sometimes the first name string isn't
            # unique but the following number is
            name = line[0] + '_' + line[1]

            status = line[2]
            # test failure conditions
            if status in ('TFAIL', 'TBROK', 'TWARN'):
                status = False
            elif status == 'TPASS':
                status = True
            else:
                # if status is not one of these, just skip it
                continue  # pragma: no cover

            metrics[name] = status

        return metrics
