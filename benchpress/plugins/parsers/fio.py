#!/usr/bin/env python3

import re
from lib.parser import Parser

bw_extract = re.compile('bw=(.*?)[GMK]')


class FioParser(Parser):

    def parse(self, output):
        metrics = {}

        important = False
        for line in output:
            line = line.lstrip().rstrip()
            if b'(all jobs)' in line:
                important = True
            if important:
                line = line.decode('utf-8')
                if line.startswith('READ'):
                    match = bw_extract.search(line)
                    metrics['read'] = {'bw': float(match.group(1))}
                if line.startswith('WRITE'):
                    match = bw_extract.search(line)
                    metrics['write'] = {'bw': float(match.group(1))}
                    important = False

        return metrics
