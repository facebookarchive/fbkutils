#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
import dataclasses
import json
from abc import ABCMeta, abstractmethod
from typing import Iterable, List

from benchpress.lib.parser import TestCaseResult, TestStatus
from benchpress.suites import Suite


class Reporter(object, metaclass=ABCMeta):
    """A Reporter is used to record suite results in your infrastructure."""

    @abstractmethod
    def report(self, suite: Suite, results: List[TestCaseResult]):
        """Save suite metrics somewhere in existing monitoring infrastructure."""
        pass

    @abstractmethod
    def close(self):
        """Do whatever necessary cleanup is required after all suites are finished."""
        pass


class StdoutReporter(Reporter):
    """Default reporter implementation, logs a human-readable line to stdout."""

    def report(self, suite: Suite, results: List[TestCaseResult]):
        for case in results:
            color = "\u001b[32m" if case.status == TestStatus.PASSED else "\u001b[31m"
            print(f"{case.name}: {color}{case.status.name}\033[0m")
            if case.details:
                lines = case.details.split("\n")
                for line in lines:
                    print(f"  {line}")
            if case.metrics:
                print("  metrics:")
                for key, value in case.metrics:
                    print(f"    {key}={value}")

    def close(self):
        pass


class JSONReporter(Reporter):
    def report(self, suite: Suite, results: Iterable[TestCaseResult]):
        """Log JSON report to stdout.
        Attempt to detect whether a real person is running the program then
        pretty print, otherwise print it as JSON.
        """
        for case in results:
            print(json.dumps(dataclasses.asdict(case)), flush=True)

    def close(self):
        pass
