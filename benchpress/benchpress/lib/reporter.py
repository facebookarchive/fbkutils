#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import dataclasses
import json
import sys
from abc import ABCMeta, abstractmethod
from typing import List

from benchpress.lib.job import Job
from benchpress.lib.parser import TestCaseResult, TestStatus


class Reporter(object, metaclass=ABCMeta):
    """A Reporter is used to record job results in your infrastructure.
    """

    @abstractmethod
    def report(self, job: Job, results: List[TestCaseResult]):
        """Save job metrics somewhere in existing monitoring infrastructure."""
        pass

    @abstractmethod
    def close(self):
        """Do whatever necessary cleanup is required after all jobs are finished."""
        pass


class StdoutReporter(Reporter):
    """Default reporter implementation, logs a JSON object to stdout."""

    def report(self, job: Job, results: List[TestCaseResult]):
        """Log JSON report to stdout.
        Attempt to detect whether a real person is running the program then
        pretty print, otherwise print it as JSON.
        """
        # use isatty as a proxy for if a real human is running this
        if sys.stdout.isatty():
            for case in results:
                color = (
                    "\u001b[32m" if case.status == TestStatus.PASSED else "\u001b[31m"
                )
                print(f"{case.name}: {color}{case.status.name}\033[0m")
                if case.details:
                    lines = case.details.split("\n")
                    for line in lines:
                        print(f"  {line}")
                if case.metrics:
                    print("  metrics:")
                    for key, value in case.metrics:
                        print(f"    {key}={value}")
        else:
            dct = {c.name: dataclasses.asdict(c) for c in results}
            json.dump(dct, sys.stdout)
        sys.stdout.write("\n")

    def close(self):
        pass
