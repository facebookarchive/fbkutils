#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import logging
import re
from typing import List

from benchpress.lib.parser import TestCaseResult, TestStatus
from benchpress.suites.suite import DiscoveredTestCase, Suite


logger = logging.getLogger(__name__)

LINE_REGEX = re.compile(r"^(.*?):?\s+(PASS|FAIL)$")


class PacketdrillSuite(Suite):
    NAME = "packetdrill"

    def discover_cases(self) -> List[DiscoveredTestCase]:
        # TODO
        return [DiscoveredTestCase(name="exec", description="does the test exit(0)")]

    def parse(
        self, stdout: List[str], stderr: List[str], returncode: int
    ) -> List[TestCaseResult]:
        """
        Packetdrill test output is very simple (for now). One row for each
        test:
               test_name return_value
        So the parsing is simple:
            "test_name 0" => "test_name PASS"
            "test_name non-zero" => "test_name FAIL"
        """
        test_cases: List[TestCaseResult] = []
        for line in stdout:
            items = line.split()
            if len(items) != 2:
                continue

            test_name = items[0]
            case = TestCaseResult(name=test_name, status=TestStatus.FAILED)
            if items[1] == "0":
                case.status = TestStatus.PASSED

            test_cases.append(case)

        return test_cases
