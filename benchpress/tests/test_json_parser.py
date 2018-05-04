#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import unittest

from benchpress.plugins.parsers.generic import JSONParser


class TestJSONParser(unittest.TestCase):

    def setUp(self):
        self.parser = JSONParser()

    def test_parse_expected_output(self):
        output = [
            '{',
            '"Combined": {',
            '"Siege requests": 4808,',
            '"Siege wall sec": 2.42,',
            '"Siege RPS": 81.01,'
            '"Siege successful requests": 4609,',
            '"Siege failed requests": 0,',
            '"Nginx hits": 5008,',
            '"Nginx avg bytes": 188779.63238818,',
            '"Nginx avg time": 2.3533458466454,',
            '"Nginx P50 time": 2.365,',
            '"Nginx P90 time": 3.095,',
            '"Nginx P95 time": 3.378,',
            '"Nginx P99 time": 3.771,',
            '"Nginx 200": 4609,',
            '"Nginx 499": 200,',
            '"Nginx 404": 199,',
            '"canonical": 1',
            '}',
            '}',
        ]
        expected_dict = {
            "Combined": {
                "Siege requests": 4808,
                "Siege wall sec": 2.42,
                "Siege RPS": 81.01,
                "Siege successful requests": 4609,
                "Siege failed requests": 0,
                "Nginx hits": 5008,
                "Nginx avg bytes": 188779.63238818,
                "Nginx avg time": 2.3533458466454,
                "Nginx P50 time": 2.365,
                "Nginx P90 time": 3.095,
                "Nginx P95 time": 3.378,
                "Nginx P99 time": 3.771,
                "Nginx 200": 4609,
                "Nginx 499": 200,
                "Nginx 404": 199,
                "canonical": 1
            }
        }
        metrics = self.parser.parse(output, [], 0)
        self.assertDictEqual(expected_dict, metrics)
        metrics = self.parser.parse([], output, 0)
        self.assertDictEqual(expected_dict, metrics)

    def test_parse_empty_output(self):
        output = ['']
        with self.assertRaises(ValueError):
            self.parser.parse(output, ['garbage'], 1)
        with self.assertRaises(ValueError):
            self.parser.parse(['garbage'], output, 1)


if __name__ == '__main__':
    unittest.main()
