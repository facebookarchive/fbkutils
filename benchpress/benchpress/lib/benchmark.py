#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from .job import MetricsConfig
from .parser_factory import ParserFactory


class Benchmark(object):
    """Holds the configuration for a benchmark.
    A Benchmark points to a binary that is run by jobs using this Benchmark and
    also has default configuration options that can be overridden by a job.

    Attributes:
        name (str): short name to identify the benchmark
        path (str): path to executable run by this benchmark
        metrics_config (MetricsConfig): default metrics configuration for
                                        jobs using this benchmark
        check_returncode (bool): automatically fail if the process returncode
                                 was not 0, default True
    """

    def __init__(self, name, config):
        self.name = name
        self.parser_name = config['parser']
        self.path = config['path']
        self.metrics_config = MetricsConfig(config['metrics'])
        self.check_returncode = config.get('check_returncode', True)

    def get_parser(self):
        return ParserFactory.create(self.parser_name)
