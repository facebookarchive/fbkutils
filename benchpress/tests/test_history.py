#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from datetime import datetime, timezone
import os
import unittest

from benchpress.lib.history import History
from benchpress.lib.job import BenchmarkJob
from benchpress.lib.metrics import Metrics


class TestHistory(unittest.TestCase):

    def test_consistency(self):
        """Tests that History is able to detect when a job configuration
           has changed."""
        history = History(os.path.join(os.path.dirname(__file__), 'history'))
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

        self.assertTrue(history.is_job_config_consistent(consistent_job))

        inconsistent_job = consistent_job
        inconsistent_job.config['args'] = ['some different arg']

        self.assertFalse(history.is_job_config_consistent(inconsistent_job))

    def test_save(self):
        """Tests that a json file is created in the right directory with the
           right timestamp when saving a job result."""
        history = History(os.path.join(os.path.dirname(__file__), 'history'))
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

        expected_path = os.path.join(os.path.dirname(__file__), 'history',
                                     'job_name',
                                     now.strftime('%Y-%m-%dT%H:%M:%SZ')+'.json')

        # make sure file doesn't already exist
        self.assertFalse(os.path.exists(expected_path))

        history.save_job_result(job, Metrics({'mysupercoolmetric': 1}), now)

        # make sure it exists now
        self.assertTrue(os.path.exists(expected_path))

        # delete it to clean up
        os.unlink(expected_path)

    def test_invalid_format(self):
        """Tests to ensure that History complains when a historical record is in
           an invalid format (missing key(s))."""
        history = History(os.path.join(os.path.dirname(__file__), 'history'))
        job = BenchmarkJob({
            'args': ['somearg'],
            'benchmark': 'bench',
            'description': 'cool description',
            'metrics': ['mysupercoolmetric'],
            'name': 'broken job',
        }, None)

        with self.assertRaises(KeyError):
            history.load_historical_results(job)



if __name__ == '__main__':
    unittest.main()
