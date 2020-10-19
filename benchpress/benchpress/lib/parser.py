#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
import enum
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional


class TestStatus(enum.IntEnum):
    __test__ = False  # keep pytest from picking these up as tests

    PASSED = 1
    FAILED = 2
    SKIPPED = 3
    FATAL = 4
    TIMEOUT = 5
    OMITTED = 7


@dataclass
class TestCaseResult(object):
    __test__ = False  # keep pytest from picking these up as tests

    name: str

    status: TestStatus

    description: Optional[str] = None
    """more details about what this test case is meant to test"""

    details: Optional[str] = ""
    """detailed output from this test case for a debugging aid"""

    runtime: Optional[float] = None
    """runtime of this test case in seconds"""

    metrics: Optional[Dict[str, float]] = None
    """metrics can be used for performance testing, they are not natively used by
    benchpress but can be used by a wrapper using benchpress as a test runner."""


class Parser(object, metaclass=ABCMeta):
    """Parser is the link between test output and the rest of the system.
    A Parser is given the test's stdout and stderr and returns the exported
    test cases.
    """

    @abstractmethod
    def parse(
        self, stdout: List[str], stderr: List[str], returncode: int
    ) -> List[TestCaseResult]:
        """Take stdout/stderr and convert it to a list of test cases."""
        pass
