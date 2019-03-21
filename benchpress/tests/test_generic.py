#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import unittest
from unittest.mock import MagicMock

from benchpress.lib.parser import TestCaseResult, TestStatus
from benchpress.suites.generic import GenericSuite


class TestGeneric(unittest.TestCase):
    def setUp(self):
        self.parser = GenericSuite(MagicMock())

    def test_sample_output(self):
        """Can parse output from running generic single-line output format"""
        # sample output from running ltp fs tests
        output = """case1: PASS
some
case2: FAIL
other
case3 FAIL
garbage intermixed
case4 PASS
"""
        results = list(self.parser.parse(output.split("\n"), [], 0))
        self.maxDiff = None
        self.assertEqual(
            [
                TestCaseResult(name="case1", status=TestStatus.PASSED),
                TestCaseResult(name="case2", status=TestStatus.FAILED),
                TestCaseResult(name="case3", status=TestStatus.FAILED),
                TestCaseResult(name="case4", status=TestStatus.PASSED),
                TestCaseResult(
                    name="exec",
                    status=TestStatus.PASSED,
                    details="""stdout:
case1: PASS
some
case2: FAIL
other
case3 FAIL
garbage intermixed
case4 PASS


stderr:
""",
                ),
            ],
            results,
        )


if __name__ == "__main__":
    unittest.main()
