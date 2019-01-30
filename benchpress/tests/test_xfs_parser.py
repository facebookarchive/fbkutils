#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import os.path
import unittest

from benchpress.lib.parser import TestCaseResult, TestStatus
from benchpress.plugins.parsers.xfstests_parser import XfstestsParser
from pyfakefs import fake_filesystem_unittest


class TestXfstestsParser(fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.parser = XfstestsParser()
        self.fs.CreateDirectory(self.parser.tests_dir)
        self.fs.CreateDirectory(os.path.join(self.parser.tests_dir, "generic"))
        self.fs.CreateDirectory(self.parser.results_dir)
        self.fs.CreateDirectory(os.path.join(self.parser.results_dir, "generic"))

    def test_pass(self):
        stdout = ["generic/001  2s", "generic/002  2s ... 4s"]
        results = self.parser.parse(stdout, [], 0)
        self.assertEqual(
            [
                TestCaseResult(
                    name="generic/001", status=TestStatus.PASSED, runtime=2.0
                ),
                TestCaseResult(
                    name="generic/002", status=TestStatus.PASSED, runtime=4.0
                ),
            ],
            results,
        )

    def test_output_mismatch(self):
        out = os.path.join(self.parser.tests_dir, "generic", "305.out")
        with open(out, "w") as f:
            f.write("expected\n")
        out_bad = os.path.join(self.parser.results_dir, "generic", "305.out.bad")
        with open(out_bad, "w") as f:
            f.write("actual\n")

        diff = f"""\
--- {self.parser.tests_dir}/generic/305.out
+++ {self.parser.results_dir}/generic/305.out.bad
@@ -1 +1 @@
-expected
+actual
"""

        stdout = [
            "generic/305 output mismatch blah blah",
            "something something",
            "more output blah blah",
        ]
        results = self.parser.parse(stdout, [], 0)
        self.assertEqual(
            [
                TestCaseResult(
                    name="generic/305", status=TestStatus.FAILED, details=diff
                )
            ],
            results,
        )

    def test_not_run(self):
        notrun1 = os.path.join(self.parser.results_dir, "generic", "001.notrun")
        with open(notrun1, "w") as f:
            f.write("fire walk with me\n")
        notrun2 = os.path.join(self.parser.results_dir, "generic", "002.notrun")
        with open(notrun2, "w") as f:
            f.write("black lodge\n")

        stdout = [
            "generic/001        [not run] foo",
            "generic/002 0s ... [not run] bar",
        ]
        results = self.parser.parse(stdout, [], 0)
        self.assertEqual(
            [
                TestCaseResult(
                    name="generic/001",
                    status=TestStatus.SKIPPED,
                    details="Not run: fire walk with me",
                ),
                TestCaseResult(
                    name="generic/002",
                    status=TestStatus.SKIPPED,
                    details="Not run: black lodge",
                ),
            ],
            results,
        )

    def test_expunged(self):
        with open("exclude_list", "w") as f:
            f.write("generic/001 # this is the water\n")

        stdout = ["generic/001  [expunged]"]
        results = self.parser.parse(stdout, [], 0)
        self.assertEqual(
            [
                TestCaseResult(
                    name="generic/001",
                    status=TestStatus.OMITTED,
                    details="Excluded: this is the water",
                )
            ],
            results,
        )

    def test_invalid_unicode(self):
        full = os.path.join(self.parser.results_dir, "generic", "001.full")
        with open(full, "wb") as f:
            f.write(b"This is not valid UTF-8\xff\n")

        stdout = ["generic/001  filesystem is inconsistent"]
        results = self.parser.parse(stdout, [], 0)
        self.assertEqual(
            [
                TestCaseResult(
                    name="generic/001",
                    status=TestStatus.FAILED,
                    details=f"{full}:\nThis is not valid UTF-8\\xff\n",
                )
            ],
            results,
        )


if __name__ == "__main__":
    unittest.main()
