#!/usr/bin/env python3

import errno
import logging
import subprocess

from .metrics import Metrics

from .hook_factory import HookFactory

logger = logging.getLogger(__name__)


class MetricsConfig(object):
    """Holds the metrics configuration for a job.
    In the future, metrics will likely have additional configuration options
    rather than just a list of names.

    Attributes:
        names (list of str): sorted metric names
    """

    def __init__(self, config):
        self.names = self.flatten_names(config)

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


class BenchmarkJob(object):
    """Holds the run configuration for an individual job.
    A BenchmarkJob has a reference to a Benchmark that it runs against. The
    binary defined in the Benchmark is run according to the configuration of
    this job.

    Attributes:
        name (str): short name to identify job
        description (str): longer description to state intent of job
    """

    def __init__(self, config, benchmark):
        self.config = config
        self.benchmark = benchmark
        self.name = config['name']
        self.description = config['description']

        hook_conf = config.get('hook', {'hook': 'noop'})
        self.hook_opts = hook_conf.get('options', {})
        self.hook = HookFactory.create(hook_conf['hook'])

        if 'metrics' in config:
            self.metrics_config = MetricsConfig(config['metrics'])
        else:
            self.metrics_config = benchmark.metrics_config

        self.args = self.arg_list(config['args'])

    def arg_list(self, args):
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
        self.hook.before_job(self.hook_opts)

        try:
            logger.info('Starting "{}"'.format(self.name))
            output = subprocess.check_output([self.benchmark.path] + self.args,
                                             stderr=subprocess.STDOUT)
        except Exception as e:
            logger.error('"{}" failed ({})'.format(self.name, e))
            if e.errno == errno.ENOENT:
                logger.error('Binary not found, did you forget to install it?')
            raise  # make sure it doesn't fail silently
        finally:
            # cleanup via hook - do this immediately in case the parser crashes
            logger.info('Running cleanup hooks for "{}"'.format(self.name))
            self.hook.after_job(self.hook_opts)

        parser = self.benchmark.get_parser()
        output = output.split(b'\n')

        logger.info('Parsing results for "{}"'.format(self.name))
        metrics = Metrics(parser.parse(output))
        self.validate_metrics(metrics)

        return metrics

    def validate_metrics(self, metrics):
        """Exported metrics sanity check.
        Ensure that the defined list of metrics is exactly the same as the
        actually exported names.

        Args:
            metrics (Metrics): results of benchmark run
        """
        expected = self.metrics_config.names
        metrics = metrics.names
        assert len(expected) == len(metrics), \
            'Expected {} metrics, got {}'.format(len(expected), len(metrics))
        for key in expected:
            assert key in metrics, 'Metric "{}" not exported'.format(key)
        return True