#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from benchpress.lib.parser import Parser


class SchbenchParser(Parser):

    def parse(self, stdout, stderr, returncode):
        stdout = stderr  # schbench writes it output on stderr
        metrics = {'latency': {}}

        latency_percs = ['p50', 'p75', 'p90', 'p95', 'p99', 'p99_5', 'p99_9']
        # this is gross - there should be some error handling eventually
        for key, line in zip(latency_percs, stdout[1:]):
            metrics['latency'][key] = float(line.split(':')[-1])

        return metrics
