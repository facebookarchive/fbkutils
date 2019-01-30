#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from typing import List

from benchpress.lib.parser import Parser, TestCaseResult, TestStatus


class ReturncodeParser(Parser):
    """Returncode parser outputs one test case 'exec' that is considered a PASS
    if the job binary had a 0 exit code, and FAIL all other times."""

    def parse(
        self, stdout: List[str], stderr: List[str], returncode: int
    ) -> List[TestCaseResult]:
        status = TestStatus.PASSED if returncode == 0 else TestStatus.FAILED
        return [
            TestCaseResult(
                name="exec",
                status=status,
                details="stdout:\n"
                + "\n".join(stdout)
                + "\n\nstderr:\n"
                + "\n".join(stderr),
            )
        ]
