#!/usr/bin/env python3
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import json
import logging
import re
from typing import List

from benchpress.lib.parser import Parser, TestCaseResult, TestStatus


JSON_LIKE_REGEX = r"\s*([{\[].*?[}\]]\s*[}\]]*)\s*"
JSON_LIKE_MATCHER = re.compile(JSON_LIKE_REGEX)


class JSONParser(Parser):
    def find_json(self, stdout: List[str], stderr: List[str]):
        """Converts JSON output from either stdout or stderr into a dict.

        Assumes that either stdout or stderr contains a section of valid JSON,
        as expected by the `json` module. Returns only first match of JSON. It
        will try to scan for JSON-like string sections, REGEX is too simple
        could miss some contrived cases.

        Args:
            stdout (list[str]): Process's line-by-line stdout output.
            stderr (list[str]): Process's line-by-line stderr output.

        Returns:
            metrics (dict): Representation of either stdout or stderr.

        Raises:
            ValueError: When neither stdout nor stderr could be parsed as JSON.
        """
        err_msg = "Failed to parse {1} as JSON: {0}"
        for (output, kind) in [(stdout, "stdout"), (stderr, "stderr")]:
            process_output = " ".join(output)
            possible_json_matches = JSON_LIKE_MATCHER.findall(process_output)
            for m in possible_json_matches:
                try:
                    return json.loads(m)
                except ValueError:
                    pass
            else:
                logging.warning(err_msg.format(ValueError(), kind))

        msg = "Couldn't not find or parse JSON from either stdout or stderr"
        raise ValueError(msg)

    def flatten(self, d):
        def items():
            for key, value in d.items():
                if isinstance(value, dict):
                    for subkey, subvalue in self.flatten(value).items():
                        yield key + "." + subkey, subvalue
                else:
                    yield key, value

        return dict(items())

    def parse(
        self, stdout: List[str], stderr: List[str], returncode: int
    ) -> List[TestCaseResult]:
        dct = self.find_json(stdout, stderr)
        dct = self.flatten(dct)

        test_cases: List[TestCaseResult] = []
        # try to parse a pass/fail output from each test case
        for key, value in dct.items():
            if isinstance(value, bool):
                status = TestStatus.PASSED if value else TestStatus.FAILED
                test_cases.append(TestCaseResult(name=key, status=status))
            if isinstance(value, str):
                passed = re.match(r"^pass(ed)?|succe(ss|ed)|true|T|1$", value, re.I)
                status = TestStatus.PASSED if passed else TestStatus.FAILED
                test_cases.append(TestCaseResult(name=key, status=status))
            if isinstance(value, dict):
                # TODO this is a janky way to handle a bunch of generic case formats
                passed = value.get(
                    "pass", value.get("passed", value.get("success", False))
                )
                status = TestStatus.PASSED if passed else TestStatus.FAILED
                test_cases.append(
                    TestCaseResult(
                        name=key, status=status, details=value.get("details")
                    )
                )

        # get a status for pseudo-case "exec" that is based on the exec code
        status = TestStatus.PASSED if returncode == 0 else TestStatus.FAILED
        test_cases.append(
            TestCaseResult(
                name="exec",
                status=status,
                details="stdout:\n"
                + "\n".join(stdout)
                + "\n\nstderr:\n"
                + "\n".join(stderr),
            )
        )

        return test_cases
