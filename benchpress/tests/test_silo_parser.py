#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import unittest

from benchpress.plugins.parsers.silo import SiloParser


class TestSiloParser(unittest.TestCase):

    def setUp(self):
        self.parser = SiloParser()

    def test_sample_output(self):
        """Can parse output from running silo tests"""
        # sample output
        output = [
            'wait_an_epoch(): consistent reads happening in e-1, but e=0 so special case',
            '[0, 0, 0] txns persisted in loading phase',
            'table customer_0 size 30000',
            'table customer_name_idx_0 size 30000',
            'table district_0 size 10',
            'table history_0 size 30000',
            'table item_0 size 100000',
            'table new_order_0 size 9000',
            'table oorder_0 size 30000',
            'table oorder_c_id_idx_0 size 30000',
            'table order_line_0 size 299560',
            'table stock_0 size 100000',
            'table stock_data_0 size 100000',
            'table warehouse_0 size 1',
            'starting benchmark...',
            'tpcc: worker id 8 => warehouses [1, 2)',
            '--- table statistics ---',
            'table customer_0 size 30000 (+0 records)',
            'table customer_name_idx_0 size 30000 (+0 records)',
            'table district_0 size 10 (+0 records)',
            'table history_0 size 54092 (+24092 records)',
            'table item_0 size 100000 (+0 records)',
            'table new_order_0 size 34386 (+25386 records)',
            'table oorder_0 size 55386 (+25386 records)',
            'table oorder_c_id_idx_0 size 55386 (+25386 records)',
            'table order_line_0 size 553596 (+254036 records)',
            'table stock_0 size 100000 (+0 records)',
            'table stock_data_0 size 100000 (+0 records)',
            'table warehouse_0 size 1 (+0 records)',
            '--- benchmark statistics ---',
            'runtime: 1.00328 sec',
            'memory delta: 58.2734 MB',
            'memory delta rate: 58.0828 MB/sec',
            'logical memory delta: 3.56796 MB',
            'logical memory delta rate: 3.55628 MB/sec',
            'agg_nosync_throughput: 55954.4 ops/sec',
            'avg_nosync_per_core_throughput: 55954.4 ops/sec/core',
            'agg_throughput: 55954.4 ops/sec',
            'avg_per_core_throughput: 55954.4 ops/sec/core',
            'agg_persist_throughput: 55954.4 ops/sec',
            'avg_per_core_persist_throughput: 55954.4 ops/sec/core',
            'avg_latency: 0.0177805 ms',
            'avg_persist_latency: 0 ms',
            'agg_abort_rate: 0 aborts/sec',
            'avg_per_core_abort_rate: 0 aborts/sec/core',
            'txn breakdown: [[Delivery, 2193], [NewOrder, 25386], [OrderStatus, 2156], [Payment, 24092], [StockLevel, 2311]]',
            '--- system counters (for benchmark) ---',
            '--- perf counters (if enabled, for benchmark) ---',
            '--- allocator stats ---',
            '[allocator] ncpus=0',
            '---------------------------------------',
            'dumping heap profile...',
            'printing jemalloc stats...',
            '55954.4 55954.4 0.0177805 0 0',
        ]
        metrics = self.parser.parse(None, output, 0)
        self.assertTrue('throughput' in metrics)
        self.assertTrue('latency' in metrics)
        self.assertDictEqual({
            'agg_throughput': 55954.4,
            'avg_per_core_throughput': 55954.4,
        }, metrics['throughput'])
        self.assertDictEqual({
            'avg_latency': 0.0177805,
        }, metrics['latency'])


if __name__ == '__main__':
    unittest.main()
