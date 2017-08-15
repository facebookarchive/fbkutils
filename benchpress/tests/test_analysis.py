#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import unittest
from unittest.mock import MagicMock

from benchpress.lib.analysis import analyze
from benchpress.lib.metrics import Metrics


def metrics(results):
    """Create a mock HistoryEntry from the results"""
    mock = MagicMock()
    mock.metrics.performance_metrics.return_value = results
    return mock


class TestAnalysis(unittest.TestCase):
    def setUp(self):
        self.job = MagicMock()
        self.history = MagicMock()
        self.history.load_historical_results.return_value = [
            metrics({'a': 1, 'b': 2, 'c': 3}),
            metrics({'a': 2, 'b': 1, 'c': 2}),
            metrics({'a': 1, 'b': 3, 'c': 4}),
            metrics({'a': 2, 'b': 2, 'c': 3}),
            metrics({'a': 1, 'b': 1, 'c': 1}),
            metrics({'a': 2, 'b': 2, 'c': 5}),
        ]

    def test_no_thresholds(self):
        """No thresholds -> no anomalies"""
        self.job.tolerances = {}
        current = {'a': 1, 'b': 2, 'c': 3}
        anomalies = analyze(current, self.job, self.history)
        self.assertEqual(0, len(anomalies))

    def test_no_anomalies(self):
        """No anomalous metric"""
        self.job.tolerances = {'a': 1.0, 'b': 1.0, 'c': 1.0}
        current = {'a': 2, 'b': 2, 'c': 3}
        anomalies = analyze(current, self.job, self.history)
        self.assertEqual(0, len(anomalies))

    def test_one_anomaly(self):
        """One anomalous metric"""
        self.job.tolerances = {'a': 1.0, 'b': 1.0, 'c': 1.0}
        current = {'a': 4, 'b': 2, 'c': 3}
        anomalies = analyze(current, self.job, self.history)
        expected = [('a', 4, 0.0, 3.0)]
        self.assertCountEqual(expected, anomalies)

    def test_nested_names(self):
        """Nested tolerance dicts work"""
        self.job.tolerances = {'a': {'b': 1}}
        # Job constructor uses Metrics#flatten for tolerances as well
        self.job.tolerances = Metrics.flatten(self.job.tolerances)
        self.history.load_historical_results.return_value = [
            metrics({'a.b': 1})
        ]
        current = {'a.b': 4}
        anomalies = analyze(current, self.job, self.history)
        expected = [('a.b', 4, 0.0, 2.0)]
        self.assertCountEqual(expected, anomalies)


if __name__ == '__main__':
    unittest.main()
