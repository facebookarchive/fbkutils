#!/usr/bin/env python3

from .command import BenchpressCommand


class ListCommand(BenchpressCommand):

    def populate_parser(self, subparsers):
        parser = subparsers.add_parser('list', help='list all configured jobs')
        parser.set_defaults(command=self)

    def run(self, args, jobs):
        for job in jobs.values():
            print('{}: {}'.format(job.name, job.description))
