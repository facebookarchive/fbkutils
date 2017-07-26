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

from .metrics import Metrics

from .hook_factory import HookFactory
from .parser_factory import ParserFactory

logger = logging.getLogger(__name__)


class MetricsConfig(object):
    """Holds the metrics configuration for a job.
    In the future, metrics will likely have additional configuration options
    rather than just a list of names.

    Attributes:
        names (list of str): sorted metric names
        validate (bool): validate metrics (strip unused, error on missing)
                         default True
    """

    def __init__(self, config):
        self.names = self.flatten_names(config)
        self.validate = '_no_validate' not in self.names

    def flatten_names(self, names, prefix=''):
        flat = []
        if isinstance(names, list):
            for name in names:
                flat += self.flatten_names(name, prefix)
        elif isinstance(names, dict):
            for name, nest in names.items():
                flat += self.flatten_names(nest, prefix + name + '.')
        else:
            # '.' is used as a separator, so replace it with a '_'
            name = prefix + str(names).replace('.', '_')
            return [name]

        return sorted(flat)


class Job(object):
    """Holds the run configuration for an individual job.
    A Job starts it's default config based on the benchmark configuration that
    it references. The binary defined in the benchmark is run according to the
    configuration of this job.

    Attributes:
        name (str): short name to identify job
        description (str): longer description to state intent of job
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

        hook_conf = config.get('hook', {'hook': 'noop'})
        self.hook_opts = hook_conf.get('options', {})
        self.hook = HookFactory.create(hook_conf['hook'])
        self.metrics_config = MetricsConfig(config['metrics'])

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
        """Run the benchmark and return the Metrics that are reported.
        """
        # take care of preprocessing setup via hook
        logger.info('Running setup hooks for "{}"'.format(self.name))
        self.hook.before_job(self.hook_opts, self)

        try:
            logger.info('Starting "{}"'.format(self.name))
            cmd = [self.binary] + self.args
            process = subprocess.Popen(cmd,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
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
            self.hook.after_job(self.hook_opts, self)
        stdout = stdout.split('\n')
        stderr = stderr.split('\n')

        parser = self.parser
        logger.info('Parsing results for "{}"'.format(self.name))
        try:
            metrics = Metrics(parser.parse(stdout, stderr, returncode))

            if self.metrics_config.validate:
                metrics = self.strip_metrics(metrics)
                self.validate_metrics(metrics)

            return metrics
        except Exception:
            logger.error('stdout:')
            logger.error('\n\t'.join(stdout))
            logger.error('stderr:')
            logger.error('\n\t'.join(stderr))
            logger.error('Failed to parse results, this might mean the'
                         ' benchmark failed')
            raise

    def strip_metrics(self, metrics):
        """Remove metrics that were not required by the test.
        If the parser exports more data than was requested, just drop the extra
        data.

        Args:
            metrics (Metrics): results of benchmark run

        Returns:
            (Metrics): only the requested metrics that were exported
        """
        expected = self.metrics_config.names
        new_metrics = {name: v for name, v in metrics.metrics().items()
                       if name in expected}
        return Metrics(new_metrics)

    def validate_metrics(self, metrics):
        """Exported metrics sanity check.
        Ensure that the defined list of metrics is exactly the same as the
        actually exported names.

        Args:
            metrics (Metrics): results of benchmark run
        """
        expected = self.metrics_config.names
        metrics = metrics.names
        for key in expected:
            assert key in metrics, 'Metric "{}" not exported'.format(key)
        return True
