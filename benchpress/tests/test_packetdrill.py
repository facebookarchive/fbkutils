#!/usr/bin/env python3
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import unittest
from unittest.mock import MagicMock

from benchpress.lib.parser import TestCaseResult, TestStatus
from benchpress.suites.packetdrill import PacketdrillSuite
from pyfakefs import fake_filesystem_unittest


class TestPacketdrill(fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.parser = PacketdrillSuite(MagicMock())

    def test_output(self):
        stdout = ["001-passed 0", "002-failed 1"]
        results = self.parser.parse(stdout, [], 0)
        self.assertEqual(
            [
                TestCaseResult(name="001-passed", status=TestStatus.PASSED),
                TestCaseResult(name="002-failed", status=TestStatus.FAILED),
            ],
            results,
        )


if __name__ == "__main__":
    unittest.main()
