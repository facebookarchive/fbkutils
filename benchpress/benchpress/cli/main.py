#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import argparse
import logging
import yaml

from benchpress.lib.benchmark import Benchmark
from benchpress.lib.job import BenchmarkJob

from .commands.list import ListCommand
from .commands.run import RunCommand

commands = [ListCommand(), RunCommand()]

parser = argparse.ArgumentParser()
parser.add_argument('-b', '--benchmarks',
                    metavar='benchmarks file', help='path to benchmarks file',
                    default='benchmarks.yml')
parser.add_argument('-j', '--jobs', dest='jobs_file',
                    metavar='job configs file', help='path to job configs file',
                    default='jobs/jobs.yml')

subparsers = parser.add_subparsers(dest='command', help='subcommand to run')
for command in commands:
    command.populate_parser(subparsers)

subparsers.required = True

parser.add_argument('-r', '--results', metavar='results dir',
                    help='directory to load/store results', default='./results')

parser.add_argument('--clowntown', help='lets you do potentially stupid things',
                    action='store_true')

parser.add_argument('--verbose', '-v', action='count', default=0)


def main():
    args = parser.parse_args()

    # warn is 30, should default to 30 when verbose=0
    # each level below warning is 10 less than the previous
    log_level = args.verbose*(-10) + 30
    logging.basicConfig(format='%(levelname)s:%(name)s: %(message)s',
                        level=log_level)
    logger = logging.getLogger(__name__)

    logger.info('Loading benchmarks from "{}"'.format(args.benchmarks))
    with open(args.benchmarks) as tests_file:
        benchmarks = yaml.load(tests_file)

    logger.info('Loading jobs from "{}"'.format(args.jobs_file))
    with open(args.jobs_file) as jobs_file:
        jobs = yaml.load(jobs_file)

    benchmarks = {key: Benchmark(key, val) for key, val in benchmarks.items()}

    jobs = [BenchmarkJob(j, benchmarks[j['benchmark']]) for j in jobs]
    jobs = {j.name: j for j in jobs}

    logger.info('Loaded {} benchmarks and {} jobs'
                .format(len(benchmarks), len(jobs)))

    args.command.run(args, jobs)