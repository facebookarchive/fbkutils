#!/usr/bin/env python3

from lib.parser import Parser


class SchbenchParser(Parser):

    def parse(self, output):
        metrics = {'latency': {}}

        latency_percs = ['p50', 'p75', 'p90', 'p95', 'p99', 'p99_5', 'p99_9']
        # this is gross - there should be some error handling eventually
        for key, line in zip(latency_percs, output[1:]):
            metrics['latency'][key] = float(line.split(b':')[-1])

        return metrics
