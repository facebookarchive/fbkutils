#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import re
from typing import List

from benchpress.lib.parser import Parser, TestCaseResult, TestStatus


# <test name> <number> <status> : <extra stuff>
test_format_re = re.compile("\\w+\\s+\\d+\\s+T(FAIL|PASS|BROK|WARN|INFO).*")


class LtpParser(Parser):
    def parse(
        self, stdout: List[str], stderr: List[str], returncode: int
    ) -> List[TestCaseResult]:
        # ltp run in quiet mode produces lines that are mostly a single line per
        # test with the test name and a status and optional message
        test_cases: List[TestCaseResult] = []

        for line in stdout:
            # make sure that the line matches the format of a test
            if not test_format_re.match(line):
                continue

            split = line.split()
            # combine 0 and 1 because sometimes the first name string isn't
            # unique but the following number is
            name = split[0] + "_" + split[1]

            status_name = split[2]
            status = TestStatus.SKIPPED
            # test failure conditions
            if status_name in ("TFAIL", "TBROK", "TWARN"):
                status = TestStatus.FAILED
            elif status_name == "TPASS":
                status = TestStatus.PASSED
            else:
                # if status is not one of these, skip it
                continue

            test_cases.append(TestCaseResult(name=name, status=status))

        return test_cases
