#!/usr/bin/env python3

from abc import ABCMeta, abstractmethod
import json
import sys


class Reporter(object, metaclass=ABCMeta):
    """A Reporter is used to record job results in your infrastructure.
    """

    @abstractmethod
    def report(self, job, metrics):
        """Save job metrics somewhere in existing monitoring infrastructure.

        Args:
            job (BenchmarkJob): job that was run
            metrics (Metrics): metrics that were exported by job
        """
        pass

    @abstractmethod
    def close(self):
        """Do whatever necessary cleanup is required after all jobs are finished.
        """
        pass


class StdoutReporter(Reporter):
    """Default reporter implementation, logs a JSON object to stdout."""
    def report(self, job, metrics):
        """Log JSON report to stdout.
        Attempt to detect whether a real person is running the program then
        pretty print the JSON, otherwise print it without linebreaks and
        unsorted keys.
        """
        # use isatty as a proxy for if a real human is running this
        if sys.stdout.isatty():
            json.dump(metrics.metrics(), sys.stdout, sort_keys=True, indent=2)
        else:
            json.dump(metrics.metrics(), sys.stdout)
        sys.stdout.write('\n')

    def close(self):
        pass
