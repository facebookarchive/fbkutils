#!/usr/bin/env python3

import argparse
import yaml

import sys
from os import path

import logging

# add this to the path so that imports work in a sane way
sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))

# the linter complains about this, but these have to be imported after the code
# above otherwise the package will not have been setup properly
from lib.benchmark import Benchmark  # noqa
from lib.job import BenchmarkJob  # noqa
from lib.reporter import StdoutReporter  # noqa
from lib.reporter_factory import ReporterFactory  # noqa

from commands.list import ListCommand  # noqa
from commands.run import RunCommand  # noqa

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

parser.add_argument('--log', metavar='logging level', default='WARN')


def main():
    args = parser.parse_args()

    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: {}'.format(args.log))
    logging.basicConfig(format='%(levelname)s:%(name)s: %(message)s',
                        level=numeric_level)
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


if __name__ == '__main__':
    # register a default class for reporting metrics
    ReporterFactory.register('default', StdoutReporter)
    main()
