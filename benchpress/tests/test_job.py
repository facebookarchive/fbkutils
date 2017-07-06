#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from collections import defaultdict
from json import JSONDecodeError
import subprocess
import unittest
from unittest.mock import MagicMock

from benchpress.lib.job import BenchmarkJob
from benchpress.lib.metrics import Metrics


class TestJob(unittest.TestCase):

    def test_validate_metrics(self):
        """Metrics with keys that don't match definition raise an error"""
        config = defaultdict(str)
        config['args'] = {}

        config['metrics'] = ['rps']
        job = BenchmarkJob(config, MagicMock())
        with self.assertRaises(AssertionError):
            job.validate_metrics(Metrics({}))
        with self.assertRaises(AssertionError):
            job.validate_metrics(Metrics({'latency': {'p50': 1}}))

        self.assertTrue(job.validate_metrics(Metrics({'rps': 1})))

        config['metrics'] = {'latency': ['p50', 'p95']}
        job = BenchmarkJob(config, MagicMock())
        self.assertTrue(job.validate_metrics(
            Metrics({'latency': {'p50': 1, 'p95': 2}})))

    def test_strip_metrics(self):
        """Metrics with keys that aren't in definition are removed"""
        config = defaultdict(str)
        config['args'] = {}

        config['metrics'] = ['rps']
        job = BenchmarkJob(config, MagicMock())

        # an empty set of metrics should stay empty
        stripped = job.strip_metrics(Metrics({}))
        self.assertEqual(len(stripped.metrics_list()), 0)

        # only passing the desired metric should stay the same
        stripped = job.strip_metrics(Metrics({'rps': 1}))
        self.assertEqual(len(stripped.metrics_list()), 1)

        # passing in more metrics should give just the requested ones
        stripped = job.strip_metrics(Metrics({'rps': 1, 'extra': 2}))
        self.assertEqual(len(stripped.metrics_list()), 1)

    def test_arg_list(self):
        """Argument list is formatted correctly with lists or dicts"""
        self.assertListEqual(
            ['--output-format=json', 'a'],
            BenchmarkJob.arg_list(['--output-format=json', 'a']))

        self.assertListEqual(
            ['--output-format', 'json', '--file'],
            BenchmarkJob.arg_list({'output-format': 'json', 'file': None}))

    def test_run_succeed(self):
        """Echo is able to run and be parsed correctly

        Run a job to echo some json and make sure it can be parse and is
        exported correctly."""
        config = defaultdict(str)
        mock_data = '{"key": "hello"}'
        config['args'] = [mock_data]
        config['metrics'] = ['key']

        mock_benchmark = MagicMock()
        mock_benchmark.path = 'echo'
        mock_parser = MagicMock()
        mock_benchmark.get_parser.return_value = mock_parser
        mock_parser.parse.return_value = {'key': 'hello'}

        job = BenchmarkJob(config, mock_benchmark)

        metrics = job.run()
        mock_parser.parse.assert_called_with([mock_data, ''], [''])
        self.assertDictEqual({'key': 'hello'}, metrics.metrics())

    def test_run_fail(self):
        """Exit 1 raises an exception"""
        config = defaultdict(str)
        config['args'] = ['-c', 'exit 1']

        mock_benchmark = MagicMock()
        mock_benchmark.path = 'sh'

        job = BenchmarkJob(config, mock_benchmark)

        with self.assertRaises(subprocess.CalledProcessError):
            job.run()

    def test_run_run_no_binary(self):
        """Nonexistent binary raises an error"""
        config = defaultdict(str)
        config['args'] = []

        mock_benchmark = MagicMock()
        mock_benchmark.path = 'somethingthatdoesntexist'

        job = BenchmarkJob(config, mock_benchmark)

        with self.assertRaises(OSError):
            job.run()

    def test_run_parser_error(self):
        """A crashed parser raises an error"""
        config = defaultdict(str)
        config['args'] = []

        mock_benchmark = MagicMock()
        mock_benchmark.path = 'echo'
        mock_parser = MagicMock()
        mock_benchmark.get_parser.return_value = mock_parser
        mock_parser.parse.side_effect = JSONDecodeError('', '', 0)

        job = BenchmarkJob(config, mock_benchmark)

        with self.assertRaises(JSONDecodeError):
            job.run()

if __name__ == '__main__':
    unittest.main()
