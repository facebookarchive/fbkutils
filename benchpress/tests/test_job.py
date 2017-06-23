#!/usr/bin/env python3

from collections import defaultdict
import unittest
from unittest.mock import MagicMock

from lib.job import BenchmarkJob
from lib.metrics import Metrics


class TestBenchmark(unittest.TestCase):

    def test_validate_metrics(self):
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


if __name__ == '__main__':
    unittest.main()