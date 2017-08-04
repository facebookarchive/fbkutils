#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import json

from benchpress.lib.parser import Parser


class FioParser(Parser):

    def parse(self, stdout, stderr, returncode):
        metrics = {}

        stdout = ''.join(stdout)

        results = json.loads(stdout)
        results = results['jobs']
        for job in results:
            name = job['jobname']
            metrics[name] = job

        return metrics
