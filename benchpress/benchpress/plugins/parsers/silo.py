#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import re

from benchpress.lib.parser import Parser


AGG_TPUT_REGEX = \
    r'(agg_throughput):\s+(\d+\.?\d*e?[+-]?\d*)\s+([a-z/]+)'
PER_CORE_TPUT_REGEX = \
    r'(avg_per_core_throughput):\s+(\d+\.?\d*e?[+-]?\d*)\s+([a-z/]+)'
LAT_REGEX = r'(avg_latency):\s+(\d+\.?\d*e?[+-]?\d*)\s+([a-z]+)'


class SiloParser(Parser):

    def parse(self, stdout, stderr, returncode):
        output = ''.join(stderr)  # Results output in stderr
        metrics = {'throughput': {}, 'latency': {}}
        tput_metrics = [
            re.findall(AGG_TPUT_REGEX, output)[0],
            re.findall(PER_CORE_TPUT_REGEX, output)[0]
        ]
        lat_metrics = [re.findall(LAT_REGEX, output)[0]]

        for tput_metric in tput_metrics:
            metrics['throughput'][tput_metric[0]] = float(tput_metric[1])

        for lat_metric in lat_metrics:
            metrics['latency'][lat_metric[0]] = float(lat_metric[1])

        return metrics
