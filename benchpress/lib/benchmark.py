#!/usr/bin/env python3


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
    """

    def __init__(self, name, config):
        self.name = name
        self.parser_name = config['parser']
        self.path = config['path']
        self.metrics_config = MetricsConfig(config['metrics'])

    def get_parser(self):
        return ParserFactory.create(self.parser_name)
