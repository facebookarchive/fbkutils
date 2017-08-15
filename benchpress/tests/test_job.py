#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from collections import defaultdict
import subprocess
import unittest
from unittest.mock import MagicMock, call

from benchpress.lib.job import Job, JobSuite
from benchpress.lib.metrics import Metrics
from benchpress.lib.hook_factory import HookFactory
from benchpress.lib.parser_factory import ParserFactory

HookFactory.create = MagicMock()
ParserFactory.create = MagicMock()


class TestJob(unittest.TestCase):

    def setUp(self):
        self.job_config = {
            'name': 'test',
            'description': 'desc',
            'args': [],
        }
        self.mock_benchmark = defaultdict(str)
        self.mock_hook = MagicMock()
        HookFactory.create.return_value = self.mock_hook
        self.mock_parser = MagicMock()
        ParserFactory.create.return_value = self.mock_parser

    def test_validate_metrics(self):
        """Metrics with keys that don't match definition raise an error"""
        self.job_config['metrics'] = ['rps']
        job = Job(self.job_config, self.mock_benchmark)
        with self.assertRaises(AssertionError):
            job.validate_metrics(Metrics({}))
        with self.assertRaises(AssertionError):
            job.validate_metrics(Metrics({'latency': {'p50': 1}}))

        self.assertTrue(job.validate_metrics(Metrics({'rps': 1})))

        self.job_config['metrics'] = {'latency': ['p50', 'p95']}
        job = Job(self.job_config, self.mock_benchmark)
        self.assertTrue(job.validate_metrics(
            Metrics({'latency': {'p50': 1, 'p95': 2}})))

    def test_strip_metrics(self):
        """Metrics with keys that aren't in definition are removed"""
        config = defaultdict(str)
        config['args'] = {}

        self.job_config['metrics'] = ['rps']
        job = Job(self.job_config, self.mock_benchmark)

        # an empty set of metrics should stay empty
        stripped = job.strip_metrics(Metrics({}))
        self.assertEqual(len(stripped.metrics_list()), 0)

        # only passing the desired metric should stay the same
        stripped = job.strip_metrics(Metrics({'rps': 1}))
        self.assertEqual(len(stripped.metrics_list()), 1)

        # passing in more metrics should give just the requested ones
        stripped = job.strip_metrics(Metrics({'rps': 1, 'extra': 2}))
        self.assertEqual(len(stripped.metrics_list()), 1)

    def test_no_validate_metrics(self):
        """When validation is disabled, job leaves metrics as-is"""
        config = defaultdict(str)
        config['args'] = {}
        self.mock_benchmark['path'] = 'true'

        self.job_config['metrics'] = ['_no_validate', 'something']

        job = Job(self.job_config, self.mock_benchmark)

        # an empty set of metrics should stay empty
        self.mock_parser.parse.return_value = {}
        metrics = job.run()
        self.assertEqual(len(metrics.metrics_list()), 0)

        # metric defined in config should remain
        self.mock_parser.parse.return_value = {'something': 1}
        metrics = job.run()
        self.assertEqual(len(metrics.metrics_list()), 1)

        # more metrics besides defined should keep all
        self.mock_parser.parse.return_value = {'something': 1, 'extra': 2}
        metrics = job.run()
        self.assertEqual(len(metrics.metrics_list()), 2)

    def test_arg_list(self):
        """Argument list is formatted correctly with lists or dicts"""
        self.assertListEqual(
            ['--output-format=json', 'a'],
            Job.arg_list(['--output-format=json', 'a']))

        expected = ['--output-format', 'json', '--file']
        actual = Job.arg_list({'output-format': 'json', 'file': None})
        # items are the same regardless of order
        self.assertCountEqual(expected, actual)
        # '--output-format' comes immediately before 'json'
        self.assertEqual(actual.index('--output-format') + 1,
                         actual.index('json'))

    def test_run_succeed(self):
        """Echo is able to run and be parsed correctly

        Run a job to echo some json and make sure it can be parse and is
        exported correctly."""
        mock_data = '{"key": "hello"}'
        self.job_config['args'] = [mock_data]
        self.job_config['metrics'] = ['key']

        self.mock_benchmark['path'] = 'echo'
        self.mock_parser.parse.return_value = {'key': 'hello'}

        job = Job(self.job_config, self.mock_benchmark)

        metrics = job.run()
        self.mock_parser.parse.assert_called_with([mock_data, ''], [''], 0)
        self.assertDictEqual({'key': 'hello'}, metrics.metrics())

    def test_run_fail(self):
        """Exit 1 raises an exception"""
        self.job_config['args'] = ['-c', 'echo "error" >&2; exit 1']

        self.mock_benchmark['path'] = 'sh'

        job = Job(self.job_config, self.mock_benchmark)

        with self.assertRaises(subprocess.CalledProcessError) as e:
            job.run()
        e = e.exception
        self.assertEqual('stdout:\n\nstderr:\nerror', e.output.rstrip())

    def test_run_fail_no_check_returncode(self):
        """Bad return code doesn't fail when check_returncode is False"""
        self.job_config['args'] = ['-c', 'echo "error" >&2; exit 1']

        self.mock_benchmark['path'] = 'sh'
        self.mock_benchmark['check_returncode'] = False

        job = Job(self.job_config, self.mock_benchmark)

        # job.run won't raise an exception
        job.run()

    def test_run_no_binary(self):
        """Nonexistent binary raises an error"""
        self.mock_benchmark['path'] = 'somethingthatdoesntexist'
        self.mock_benchmark['metrics'] = []

        job = Job(self.job_config, self.mock_benchmark)

        with self.assertRaises(OSError):
            job.run()

    def test_run_parser_error(self):
        """A crashed parser raises an error"""
        self.mock_benchmark['path'] = 'true'
        self.mock_benchmark['metrics'] = []
        self.mock_parser.parse.side_effect = ValueError('')

        job = Job(self.job_config, self.mock_benchmark)

        with self.assertRaises(ValueError):
            job.run()

    def test_run_timeout(self):
        """Binary running past timeout raises an error"""
        self.job_config['timeout'] = 0.1
        self.mock_benchmark['path'] = 'sleep'
        self.job_config['args'] = ['1']

        job = Job(self.job_config, self.mock_benchmark)

        with self.assertRaises(subprocess.TimeoutExpired):
            job.run()

    def test_hooks(self):
        """Job runs hooks before/after in stack order"""
        self.mock_benchmark['path'] = 'true'
        self.job_config['hooks'] = [
            {'hook': 'first', 'options': {'a': 1}},
            {'hook': 'second', 'options': {'b': 1}},
        ]
        mock = MagicMock()
        first = mock.first
        second = mock.second

        def get_mock_hook(name):
            if name == 'first':
                return first
            else:
                return second

        HookFactory.create.side_effect = get_mock_hook

        job = Job(self.job_config, self.mock_benchmark)
        job.run()

        self.assertListEqual([
            call.first.before_job({'a': 1}, job),
            call.second.before_job({'b': 1}, job),
            # post hooks run in reverse order
            call.second.after_job({'b': 1}, job),
            call.first.after_job({'a': 1}, job),
        ], mock.method_calls)

    def test_job_suite(self):
        """JobSuite runs all jobs in the suite"""
        jobs = [MagicMock() for i in range(10)]
        for i, job in enumerate(jobs):
            job.name = str(i)
            job.safe_name = str(i)
            job.metrics_config.names = ['a']
            job.run.return_value = Metrics({'a': i})
        suite = JobSuite({'name': 'suite', 'description': 'test'}, jobs)
        suite.run()
        metrics = suite.run()
        expected = {str(i)+'.a': i for i in range(10)}
        self.assertDictEqual(expected, metrics.metrics())

    def test_job_suite_job_fail(self):
        """JobSuite with a failed job raises an error"""
        self.mock_benchmark['path'] = 'abinaryhasnopath'

        fail_job = Job(self.job_config, self.mock_benchmark)

        suite = JobSuite({'name': 'suite', 'description': 'test'}, [fail_job])
        with self.assertRaises(OSError):
            suite.run()


if __name__ == '__main__':
    unittest.main()
