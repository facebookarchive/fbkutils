#!/usr/bin/env python3

import json

from lib.parser import Parser


class FioParser(Parser):

    def parse(self, output):
        metrics = {}

        output = b''.join(output)

        results = json.loads(output)
        results = results['jobs']
        for job in results:
            name = job['jobname']
            metrics[name] = job

        return metrics
