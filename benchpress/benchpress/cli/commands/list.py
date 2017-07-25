#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from .command import BenchpressCommand


class ListCommand(BenchpressCommand):

    def populate_parser(self, subparsers):
        parser = subparsers.add_parser('list', help='list all configured jobs')
        parser.set_defaults(command=self)

    def run(self, args, jobs):
        for job in jobs.values():
            print('{}: {}'.format(job.name, job.description))
