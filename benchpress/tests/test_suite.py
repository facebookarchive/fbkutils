#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import io
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, call

from benchpress.lib.hook_factory import HookFactory
from benchpress.lib.parser import TestCaseResult, TestStatus
from benchpress.suites import Suite


HookFactory.create = MagicMock()


class TestSuite(unittest.TestCase):
    def setUp(self):
        self.suite_config = {"name": "test", "description": "desc", "args": []}
        self.mock_hook = MagicMock()
        HookFactory.create.return_value = self.mock_hook
        Suite.parse = Mock()

    def test_arg_list(self):
        """Argument list is formatted correctly with lists or dicts"""
        self.assertListEqual(
            ["--output-format=json", "a"], Suite.arg_list(["--output-format=json", "a"])
        )

        expected = ["--output-format", "json", "--file"]
        actual = Suite.arg_list({"output-format": "json", "file": None})
        # items are the same regardless of order
        self.assertCountEqual(expected, actual)
        # '--output-format' comes immediately before 'json'
        self.assertEqual(actual.index("--output-format") + 1, actual.index("json"))

    def test_run_succeed(self):
        """Echo is able to run and be parsed correctly

        Run a suite to echo some json and make sure it can be parse and is
        exported correctly."""
        mock_data = '{"key": "hello"}'
        self.suite_config["args"] = [mock_data]
        self.suite_config["metrics"] = ["key"]

        self.suite_config["path"] = "echo"

        suite = Suite(self.suite_config)
        suite.parse = Mock(
            return_value=[TestCaseResult(name="key", status=TestStatus.PASSED)]
        )

        metrics = suite.run()
        suite.parse.assert_called_with([mock_data], [], 0)
        self.assertEqual(
            [TestCaseResult(name="key", status=TestStatus.PASSED)], metrics
        )

    def test_run_fail(self):
        """Exit 1 raises an exception"""
        self.suite_config["args"] = ["-c", 'echo "error" >&2; exit 1']

        self.suite_config["path"] = "sh"

        suite = Suite(self.suite_config)

        with self.assertRaises(subprocess.CalledProcessError) as e:
            suite.run()
        e = e.exception
        self.assertEqual("", e.stdout.strip())
        self.assertEqual("error", e.stderr.strip())

    def test_run_fail_no_check_returncode(self):
        """Bad return code doesn't fail when check_returncode is False"""
        self.suite_config["args"] = ["-c", 'echo "error" >&2; exit 1']

        self.suite_config["path"] = "sh"
        self.suite_config["check_returncode"] = False

        suite = Suite(self.suite_config)

        # suite.run won't raise an exception
        suite.run()

    def test_run_no_binary(self):
        """Nonexistent binary raises an error"""
        self.suite_config["path"] = "somethingthatdoesntexist"
        self.suite_config["metrics"] = []

        suite = Suite(self.suite_config)

        with self.assertRaises(OSError):
            suite.run()

    def test_run_parser_error(self):
        """A crashed parser raises an error"""
        self.suite_config["path"] = "true"
        self.suite_config["metrics"] = []

        suite = Suite(self.suite_config)
        suite.parse = Mock(side_effect=ValueError(""))

        with self.assertRaises(ValueError):
            suite.run()

    def test_run_timeout(self):
        """Binary running past timeout raises an error"""
        self.suite_config["timeout"] = 0.1
        self.suite_config["path"] = "/bin/sh"
        self.suite_config["args"] = ["-c", "yes"]

        suite = Suite(self.suite_config)

        with self.assertRaises(subprocess.TimeoutExpired):
            suite.run()

    def test_run_timeout_is_pass(self):
        """Binary running past timeout raises an error"""
        self.suite_config["timeout"] = 0.1
        self.suite_config["timeout_is_pass"] = True
        self.suite_config["path"] = "/bin/sh"
        self.suite_config["args"] = [
            "-c",
            'echo "wow" && echo "err" > /dev/stderr && sleep 2',
        ]

        suite = Suite(self.suite_config)

        suite.run()

        suite.parse.assert_called_with(["timed out as expected"], [], 0)

    def test_tee_stdouterr(self):
        """tee_output option works correctly

        With tee_option=True, the suite should print the subprocess stdout lines
        starting with 'stdout:' and stderr starting with 'stderr:'"""
        mock_data = "line 1 from echo\nthis is the second line"
        self.suite_config["args"] = [mock_data]
        self.suite_config["metrics"] = ["key"]
        self.suite_config["tee_output"] = True

        self.suite_config["path"] = "echo"

        suite = Suite(self.suite_config)
        # capture stdout/err
        orig_stdout, orig_stderr = sys.stdout, sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        suite.run()

        expected = "stdout: line 1 from echo\nstdout: this is the second line\n"
        self.assertEqual(sys.stdout.getvalue(), expected)

        # test with stderr and stdout
        # first reset stdout string
        sys.stdout.truncate(0)
        sys.stdout.seek(0)

        self.suite_config["path"] = "sh"
        self.suite_config["args"] = ["-c", 'echo "error" >&2 && echo "from stdout"']
        self.suite_config["tee_output"] = True

        suite = Suite(self.suite_config)
        suite.run()

        expected = "stdout: from stdout\nstderr: error\n"
        self.assertEqual(sys.stdout.getvalue(), expected)

        sys.stdout = orig_stdout
        sys.stderr = orig_stderr

    def test_tee_output_file(self):
        """tee_output can write to file."""
        mock_data = "line 1 from echo\nthis is the second line"
        self.suite_config["args"] = [mock_data]
        self.suite_config["metrics"] = ["key"]

        fd, teefile = tempfile.mkstemp()
        os.close(fd)

        self.suite_config["path"] = "sh"
        self.suite_config["args"] = ["-c", 'echo "error" >&2 && echo "from stdout"']
        self.suite_config["tee_output"] = teefile

        suite = Suite(self.suite_config)
        suite.run()

        expected = "stdout: from stdout\nstderr: error\n"
        with open(teefile, "r") as tmp:
            self.assertEqual(tmp.read(), expected)
        os.remove(teefile)

    def test_hooks(self):
        """Suite runs hooks before/after in stack order"""
        self.suite_config["path"] = "true"
        self.suite_config["hooks"] = [
            {"hook": "first", "options": {"a": 1}},
            {"hook": "second", "options": {"b": 1}},
        ]
        mock = MagicMock()
        first = mock.first
        second = mock.second

        def get_mock_hook(name):
            if name == "first":
                return first
            else:
                return second

        HookFactory.create.side_effect = get_mock_hook

        suite = Suite(self.suite_config)
        suite.run()

        self.assertListEqual(
            [
                call.first.before({"a": 1}, suite),
                call.second.before({"b": 1}, suite),
                # post hooks run in reverse order
                call.second.after({"b": 1}, suite),
                call.first.after({"a": 1}, suite),
            ],
            mock.method_calls,
        )


if __name__ == "__main__":
    unittest.main()
