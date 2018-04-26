#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import logging
from datetime import datetime, timezone

from .command import BenchpressCommand
from benchpress.lib.history import History
from benchpress.lib.reporter_factory import ReporterFactory

logger = logging.getLogger(__name__)


class RunCommand(BenchpressCommand):

    def populate_parser(self, subparsers):
        parser = subparsers.add_parser('run', help='run job(s)')
        parser.set_defaults(command=self)
        parser.add_argument('jobs', nargs='*', default=[], help='jobs to run')

    def run(self, args, jobs):
        reporter = ReporterFactory.create('default')

        if len(args.jobs) > 0:
            for name in args.jobs:
                if name not in jobs:
                    logger.error('No job "{}" found'.format(name))
                    exit(1)
            jobs = {name: jobs[name] for name in args.jobs}

        jobs = jobs.values()
        print('Will run {} job(s)'.format(len(jobs)))

        history = History(args.results)
        now = datetime.now(timezone.utc)

        for job in jobs:
            print('Running "{}": {}'.format(job.name, job.description))

            if not args.clowntown and not history.is_job_config_consistent(job):
                logger.error('There was a previous run of "{}" that had a'
                             ' different configuration, this is likely to make'
                             ' your results confusing.'.format(job.name))
                logger.error('You can proceed anyway using --clowntown')
                exit(3)

            metrics = job.run()

            reporter.report(job, metrics)

            history.save_job_result(job, metrics, now)

        reporter.close()
