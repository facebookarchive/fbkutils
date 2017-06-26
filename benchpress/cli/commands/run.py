#!/usr/bin/env python3

from datetime import datetime
import logging

from .command import BenchpressCommand
from lib.history import History
from lib.reporter_factory import ReporterFactory

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
        now = datetime.now()

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
