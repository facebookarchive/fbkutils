#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from datetime import datetime, timezone
import os
from pyfakefs import fake_filesystem_unittest
import unittest

from benchpress.lib.history import History
from benchpress.lib.job import BenchmarkJob
from benchpress.lib.metrics import Metrics


class TestHistory(fake_filesystem_unittest.TestCase):

    def setUp(self):
        self.setUpPyfakefs()

    def test_consistency(self):
        """History is able to detect when a job configuration has changed."""
        history = History('/history')
        consistent_job = BenchmarkJob({
            'args': ['somearg'],
            'benchmark': 'bench',
            'description': 'cool description',
            'hook': {
                'hook': 'noop',
                'options': []
            },
            'metrics': ['mysupercoolmetric'],
            'name': 'job name',
        }, None)

        self.fs.CreateFile('/history/job_name/1.json',
                           contents='''
                           {
                             "config": {
                               "args": ["somearg"],
                               "benchmark": "bench",
                               "description": "cool description",
                               "hook": {
                                 "hook": "noop",
                                 "options": []
                               },
                               "metrics": ["mysupercoolmetric"],
                               "name": "job name"
                             },
                             "job": "job name",
                             "metrics": {
                               "mysupercoolmetric": 1
                             },
                             "timestamp": "2017-06-26T21:41:04"
                           }
                           ''')

        self.assertTrue(history.is_job_config_consistent(consistent_job))

        inconsistent_job = consistent_job
        inconsistent_job.config['args'] = ['some different arg']

        self.assertFalse(history.is_job_config_consistent(inconsistent_job))

    def test_save(self):
        """A json file is created in the right directory with the right name
           when saving a job result."""
        history = History('/history')
        job = BenchmarkJob({
            'args': ['somearg'],
            'benchmark': 'bench',
            'description': 'cool description',
            'hook': {
                'hook': 'noop',
                'options': []
            },
            'metrics': ['mysupercoolmetric'],
            'name': 'job name',
        }, None)

        now = datetime.now(timezone.utc)

        expected_path = os.path.join(
            '/history', 'job_name',
            now.strftime('%Y-%m-%dT%H:%M:%SZ') + '.json')

        # make sure file doesn't already exist
        self.assertFalse(self.fs.Exists(expected_path))

        history.save_job_result(job, Metrics({'mysupercoolmetric': 1}), now)

        # make sure it exists now
        self.assertTrue(self.fs.Exists(expected_path))

    def test_invalid_format(self):
        """History complains when a historical record is in an invalid format
           (missing key(s))."""
        history = History('/history')
        job = BenchmarkJob({
            'args': ['somearg'],
            'benchmark': 'bench',
            'description': 'cool description',
            'metrics': ['mysupercoolmetric'],
            'name': 'broken job',
        }, None)

        self.fs.CreateFile('/history/broken_job/1.json',
                           contents='''
                           {
                             "config": {
                               "args": ["somearg"],
                               "benchmark": "bench",
                               "description": "cool description",
                               "hook": {
                                 "hook": "noop",
                                 "options": []
                               },
                               "metrics": ["mysupercoolmetric"],
                               "name": "job name"
                             },
                             "job": "broken_job",
                             "metrics": {
                                 "mysupercoolmetric": 1
                             }
                           }''')

        with self.assertRaises(KeyError):
            history.load_historical_results(job)


if __name__ == '__main__':
    unittest.main()
