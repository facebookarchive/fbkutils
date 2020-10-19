#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import logging
import re
from typing import Iterable, List, Optional

from benchpress.lib.parser import TestCaseResult, TestStatus
from benchpress.suites.suite import Suite


logger = logging.getLogger(__name__)

LINE_REGEX = re.compile(r"^(.*?):?\s+(PASS|FAIL)$")


class GenericSuite(Suite):
    """GenericSuite is a way to add simple tests that don't support test case
    discovery or running a subset of test cases. This is appropriate for simple
    tests that just exit(0) to signal passing.

    We will attempt to parse some common form of output such as:
        case1: PASS
        case2 PASSED
        case4 FAIL
        case5: FAILED
        case6: TIMEOUT

    More complex test suites are encouraged to implement their own subclass of
    Suite to gain more useful functionality around test discovery and running
    subsets of tests which is very useful when debugging test failures."""

    NAME = "generic"

    @staticmethod
    def get_status_from_name(status: str):
        status = status.upper()
        try:
            return TestStatus[status]
        except KeyError:
            try:
                return TestStatus[status + "ED"]
            except KeyError:
                logger.warning(f'No such status "{status}(ED)"')
                return None

    @staticmethod
    def parse_line(line: str) -> Optional[TestCaseResult]:
        match = LINE_REGEX.match(line)
        if match:
            name = match.group(1)
            status = GenericSuite.get_status_from_name(match.group(2))
            if status:
                return TestCaseResult(name=name, status=status)
        return None

    def parse(
        self, stdout: List[str], stderr: List[str], returncode: int
    ) -> Iterable[TestCaseResult]:
        for output in (stdout, stderr):
            for line in output:
                case = self.parse_line(line)
                if case:
                    yield case
        # get a status for pseudo-case "generic" that is based on the exit code
        # and contains the subprocess exit code
        status = TestStatus.PASSED if returncode == 0 else TestStatus.FAILED
        yield TestCaseResult(
            name="generic",
            status=status,
            details=f"exit code: {returncode}\n"
            + "stdout:\n"
            + "\n".join(stdout)
            + "\n\nstderr:\n"
            + "\n".join(stderr),
        )
