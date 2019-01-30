#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import re
from typing import Iterable, List

from benchpress.lib.parser import Parser, TestCaseResult, TestStatus


# <test name> <number> <status> : <extra stuff>
test_format_re = re.compile("\\w+\\s+\\d+\\s+(T(?:FAIL|PASS|BROK|WARN|INFO)).*")


class LtpParser(Parser):
    def test_cases(self, stdout: List[str]) -> Iterable[TestCaseResult]:
        case_lines: List[str] = []
        for line in stdout:
            if line == "<<<test_start>>>":
                case_lines = []
            if line == "<<<test_end>>>":
                name_match = re.match(r"^tag=(.*) stime=.*$", case_lines[1])
                assert name_match is not None
                name = name_match.group(1)

                output_start = case_lines.index("<<<test_output>>>")
                output_end = case_lines.index("<<<execution_status>>>")
                output = case_lines[output_start + 1 : output_end]

                status_line = output[-1]
                match = test_format_re.match(status_line)
                assert match is not None
                status_name = match.group(1)
                status = TestStatus.SKIPPED
                if status_name in ("TFAIL", "TBROK", "TWARN"):
                    status = TestStatus.FAILED
                elif status_name == "TPASS":
                    status = TestStatus.PASSED
                case = TestCaseResult(
                    name=name, status=status, details="\n".join(output)
                )
                yield case
                continue
            case_lines.append(line)

    def parse(
        self, stdout: List[str], stderr: List[str], returncode: int
    ) -> List[TestCaseResult]:
        return list(self.test_cases(stdout))
