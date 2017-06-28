#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import unittest
from yaml import load as load_yaml

from lib.job import MetricsConfig
from lib.metrics import Metrics


class TestMetrics(unittest.TestCase):

    def test_flatten_metrics_definition(self):
        yaml = '''
- rps
- latency:
  - p50
  - p95
  - p99.9
  - 1
'''
        metrics = MetricsConfig(load_yaml(yaml))
        expected = [
            'latency.1',
            'latency.p50',
            'latency.p95',
            'latency.p99_9',
            'rps',
        ]
        self.assertListEqual(expected, metrics.names)

        yaml = '''
- rps
- latency:
  - nesting:
    - some:
      - more
    - else
'''
        metrics = MetricsConfig(load_yaml(yaml))
        expected = ['latency.nesting.else', 'latency.nesting.some.more', 'rps']
        self.assertListEqual(expected, metrics.names)

    def test_flatten_metrics_exported(self):
        # test with metrics exported from a parser
        metrics = Metrics({'rps': 1})
        expected = ['rps']
        self.assertListEqual(expected, metrics.names)

        metrics = Metrics({'latency': {'p50': 1, 'p95': 2}})
        expected = ['latency.p50', 'latency.p95']
        self.assertListEqual(expected, metrics.names)

        # test that values are preserved correctly
        metrics = Metrics({'latency': {'p50': 1, 'p95': 2}})
        expected = {'latency.p50': 1, 'latency.p95': 2}
        self.assertDictEqual(expected, metrics.metrics())


if __name__ == '__main__':
    unittest.main()
