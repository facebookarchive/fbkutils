#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import difflib
import logging
import os
import re
from typing import Iterable, List, Optional

from benchpress.lib.parser import TestCaseResult, TestStatus
from benchpress.suites.suite import DiscoveredTestCase, Suite


logger = logging.getLogger(__name__)

TESTS_DIR = "xfstests/tests"
RESULTS_DIR = "xfstests/results"


class XfstestsSuite(Suite):
    NAME = "xfstests"

    def discover_cases(self) -> List[DiscoveredTestCase]:
        # TODO
        return [DiscoveredTestCase(name="exec", description="does the test exit(0)")]

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

    def run(
        self, cases: Optional[List[DiscoveredTestCase]] = None
    ) -> Iterable[TestCaseResult]:
        if cases:
            logger.warning(
                "benchpress currently doesn't support running groups"
                " of tests in xfstests, assuming you passed a list of individual"
                " test cases to run"
            )
            self.args += [c.name for c in cases]
        return super().run(cases)

    def parse(
        self, stdout: List[str], stderr: List[str], returncode: int
    ) -> Iterable[TestCaseResult]:
        excluded = {}
        # The exclude list is one test per line optionally followed by a
        # comment explaining why the test is excluded.
        exclude_list_re = re.compile(
            r"\s*(?P<test_name>[^\s#]+)\s*(?:#\s*(?P<reason>.*))?\s*"
        )
        try:
            with open("exclude_list", "r", errors="backslashreplace") as f:
                for line in f:
                    match = exclude_list_re.match(line)
                    if match:
                        reason = match.group("reason")
                        if reason is None:
                            reason = ""
                        excluded[match.group("test_name")] = reason
        except OSError:
            pass

        test_regex = re.compile(
            r"^(?P<test_name>\w+/\d+)\s+(?:\d+s\s+\.\.\.\s+)?(?P<status>.*)"
        )
        for line in stdout:
            match = test_regex.match(line)
            if match:
                test_name = match.group("test_name")

                case = TestCaseResult(name=test_name, status=TestStatus.FATAL)

                status = match.group("status")
                duration_match = re.fullmatch(r"(\d+(?:\.\d+)?)s", status)
                if duration_match:
                    case.status = TestStatus.PASSED
                    case.runtime = float(duration_match.group(1))
                elif status.startswith("[not run]"):
                    case.status = TestStatus.SKIPPED
                    case.details = self.not_run_details(test_name)
                elif status.startswith("[expunged]"):
                    case.status = TestStatus.OMITTED
                    case.details = self.excluded_details(excluded, test_name)
                else:
                    case.status = TestStatus.FAILED
                    case.details = self.run_details(test_name)

                yield case

    def not_run_details(self, test_name):
        try:
            notrun = os.path.join(RESULTS_DIR, test_name + ".notrun")
            with open(notrun, "r", errors="backslashreplace") as f:
                return "Not run: " + f.read().strip()
        except OSError:
            return "Not run"

    @staticmethod
    def excluded_details(excluded, test_name):
        try:
            return "Excluded: " + excluded[test_name]
        except KeyError:
            return "Excluded"

    def run_details(self, test_name):
        details = []
        self.append_diff(test_name, details)
        self.append_full_output(test_name, details)
        self.append_dmesg(test_name, details)
        return "".join(details)

    def append_diff(self, test_name, details):
        try:
            out_path = os.path.join(TESTS_DIR, test_name + ".out")
            with open(out_path, "r", errors="backslashreplace") as f:
                out = f.readlines()
            out_bad_path = os.path.join(RESULTS_DIR, test_name + ".out.bad")
            with open(out_bad_path, "r", errors="backslashreplace") as f:
                out_bad = f.readlines()
        except OSError:
            return

        diff = difflib.unified_diff(out, out_bad, out_path, out_bad_path)
        details.extend(diff)

    def append_full_output(self, test_name, details):
        full_path = os.path.join(RESULTS_DIR, test_name + ".full")
        try:
            # There are some absurdly large full results.
            if os.path.getsize(full_path) < 100_000:
                with open(full_path, "r", errors="backslashreplace") as f:
                    if details:
                        details.append("--\n")
                    details.append(f"{full_path}:\n")
                    details.append(f.read())
        except OSError:
            pass

    def append_dmesg(self, test_name, details):
        dmesg_path = os.path.join(RESULTS_DIR, test_name + ".dmesg")
        try:
            with open(dmesg_path, "r", errors="backslashreplace") as f:
                if details:
                    details.append("--\n")
                details.append(f"{dmesg_path}:\n")
                details.append(f.read())
        except OSError:
            pass
