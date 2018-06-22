# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import unittest

from benchpress.plugins.parsers.graph500 import Graph500Parser


class TestGraph500Parser(unittest.TestCase):

    def setUp(self):
        self.parser = Graph500Parser()

    def test_graph500_output(self):
        output = [
            'SCALE: 20',
            'nvtx: 1048576',
            'edgefactor: 16',
            'terasize: 2.68435455999999995e-04',
            'A: 5.69999999999999951e-01',
            'B: 1.90000000000000002e-01',
            'C: 1.90000000000000002e-01',
            'D: 5.00000000000000444e-02',
            'generation_time: 7.66684459000000018e+00',
            'construction_time: 6.41681591700000009e+00',
            'nbfs: 64',
            'min_time: 2.15880087000000026e-01',
            'firstquartile_time: 2.67573745249999995e-01',
            'median_time: 2.89870043500000008e-01',
            'thirdquartile_time: 3.04702949249999966e-01',
            'max_time: 5.52760817999999987e-01',
            'mean_time: 2.96250436796875016e-01',
            'stddev_time: 5.09852699808539048e-02',
            'min_nedge: 1.67770270000000000e+07',
            'firstquartile_nedge: 1.67770270000000000e+07',
            'median_nedge: 1.67770270000000000e+07',
            'thirdquartile_nedge: 1.67770270000000000e+07',
            'max_nedge: 1.67770270000000000e+07',
            'mean_nedge: 1.67770270000000000e+07',
            'stddev_nedge: 0.00000000000000000e+00',
            'min_TEPS: 3.03513318123789318e+07',
            'firstquartile_TEPS: 5.58372454800551683e+07',
            'median_TEPS: 5.84075242403832078e+07',
            'thirdquartile_TEPS: 6.31682987237617970e+07',
            'max_TEPS: 7.77145647527925968e+07',
            'harmonic_mean_TEPS: 5.66312312697220370e+07',
            'harmonic_stddev_TEPS: 1.22792390265783062e+06',
        ]
        metrics = self.parser.parse(output, None, 0)
        self.assertDictEqual({
                'min_TEPS': float('3.03513318123789318e+07'),
                'firstquartile_TEPS': float('5.58372454800551683e+07'),
                'median_TEPS': float('5.84075242403832078e+07'),
                'thirdquartile_TEPS': float('6.31682987237617970e+07'),
                'max_TEPS': float('7.77145647527925968e+07'),
                'harmonic_mean_TEPS': float('5.66312312697220370e+07'),
                'harmonic_stddev_TEPS': float('1.22792390265783062e+06'),
            }, metrics)


if __name__ == '__main__':
    unittest.main()
