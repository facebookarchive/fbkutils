# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
import re

from benchpress.lib.parser import Parser

TEPS_REGEX = r'(\w+_TEPS):\s+(\d+\.?\d*e?[+-]\d*)'


class Graph500Parser(Parser):

    def parse(self, stdout, stderr, returncode):
        output = ' '.join(stdout)
        metrics = {}
        times = re.findall(TEPS_REGEX, output)
        for t in times:
            metrics[t[0]] = float(t[1])
        return metrics
