#!/usr/bin/env python3

import argparse
import yaml

import sys
from os import path

# add this to the path so that imports work in a sane way
sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))

from lib.benchmark import Benchmark
from lib.job import BenchmarkJob
from lib.reporter import StdoutReporter
from lib.reporter_factory import ReporterFactory

from commands.list import ListCommand
from commands.run import RunCommand

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


def main():
    args = parser.parse_args()

    with open(args.benchmarks) as tests_file:
        benchmarks = yaml.load(tests_file)

    with open(args.jobs_file) as jobs_file:
        jobs = yaml.load(jobs_file)

    benchmarks = {name: Benchmark(name, val) for name, val in benchmarks.items()}

    jobs = [BenchmarkJob(j, benchmarks[j['benchmark']]) for j in jobs]
    jobs = {j.name: j for j in jobs}


    args.command.run(args, jobs)


if __name__ == '__main__':
    # register a default class for reporting metrics
    ReporterFactory.register('default', StdoutReporter)
    main()
