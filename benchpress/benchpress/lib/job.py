#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import errno
import logging
import subprocess
from subprocess import CalledProcessError

from .hook_factory import HookFactory
from .parser_factory import ParserFactory

logger = logging.getLogger(__name__)


class Job(object):
    """Holds the run configuration for an individual job.
    A Job starts it's default config based on the benchmark configuration that
    it references. The binary defined in the benchmark is run according to the
    configuration of this job.

    Attributes:
        name (str): short name to identify job
        description (str): longer description to state intent of job
        tolerances (dict): percentage tolerance around the mean of historical
                           results
        config (dict): raw configuration dictionary
    """

    def __init__(self, job_config, benchmark_config):
        """Create a Job with the default benchmark_config and the specific job
        config

        Args:
            config (dict): job config
            benchmark_config (dict): benchmark (aka default) config
        """
        # start with the config being the benchmark config and then update it
        # with the job config so that a job can override any options in the
        # benchmark config
        config = benchmark_config
        # TODO(vmagro) should there be some basic sanity check that a job_config
        # contains certain fields?
        config.update(job_config)
        self.config = config

        self.name = config['name']
        self.description = config['description']

        self.binary = config['path']
        self.parser = ParserFactory.create(config['parser'])
        self.check_returncode = config.get('check_returncode', True)
        self.timeout = config.get('timeout', None)

        self.hooks = config.get('hooks', [])
        self.hooks = [
            (HookFactory.create(h['hook']), h.get('options', None))
            for h in self.hooks]
        # self.hooks is list of (hook, options)

        self.tolerances = config.get('tolerances', {})

        self.args = self.arg_list(config['args'])

    @staticmethod
    def arg_list(args):
        """Convert argument definitions to a list suitable for subprocess.
        """
        if isinstance(args, list):
            return args

        l = []
        for key, val in args.items():
            l.append('--' + key)
            if val is not None:
                l.append(str(val))
        return l

    def run(self):
        """Run the benchmark and return the metrics that are reported.
        """
        # take care of preprocessing setup via hook
        logger.info('Running setup hooks for "{}"'.format(self.name))
        for hook, opts in self.hooks:
            logger.info('Running %s %s', hook, opts)
            hook.before_job(opts, self)

        try:
            logger.info('Starting "{}"'.format(self.name))
            cmd = [self.binary] + self.args
            process = subprocess.Popen(cmd,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(timeout=self.timeout)
            stdout = stdout.decode('utf-8', 'ignore')
            stderr = stderr.decode('utf-8', 'ignore')
            returncode = process.returncode
            if self.check_returncode and returncode != 0:
                output = 'stdout:\n{}\nstderr:\n{}'.format(stdout, stderr)
                cmd = ' '.join(cmd)
                raise CalledProcessError(process.returncode, cmd, output)
        except OSError as e:
            logger.error('"{}" failed ({})'.format(self.name, e))
            if e.errno == errno.ENOENT:
                logger.error('Binary not found, did you forget to install it?')
            raise  # make sure it passes the exception up the chain
        except CalledProcessError as e:
            logger.error(e.output)
            raise  # make sure it passes the exception up the chain
        finally:
            # cleanup via hook - do this immediately in case the parser crashes
            logger.info('Running cleanup hooks for "{}"'.format(self.name))
            # run hooks in reverse this time so it operates like a stack
            for hook, opts in reversed(self.hooks):
                hook.after_job(opts, self)
        stdout = stdout.split('\n')
        stderr = stderr.split('\n')

        parser = self.parser
        logger.info('Parsing results for "{}"'.format(self.name))
        try:
            return parser.parse(stdout, stderr, returncode)
        except Exception:
            logger.error('stdout:')
            logger.error('\n\t'.join(stdout))
            logger.error('stderr:')
            logger.error('\n\t'.join(stderr))
            logger.error('Failed to parse results, this might mean the'
                         ' benchmark failed')
            raise

    @property
    def safe_name(self):
        return self.name.replace(' ', '_')


class JobSuite(Job):
    """JobSuite is a collection of jobs that will be run as a group.
    The results of all the jobs in the suite are compiled into a single dict.
    """

    def __init__(self, config, jobs):
        self.config = config
        self.name = config['name']
        self.description = config['description']
        self.jobs = jobs

    def run(self):
        """Run jobs in the suite and merges the results into a single dict."""
        results = {}
        for job in self.jobs:
            try:
                results[job.safe_name] = job.run()
            except Exception:
                logger.error('Job "%s" failed', job.name)
                raise
        return results
