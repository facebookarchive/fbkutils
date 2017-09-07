#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

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
            job (Job): job that was run
            metrics (dict): metrics that were exported by job
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
            json.dump(metrics, sys.stdout, sort_keys=True, indent=2)
        else:
            json.dump(metrics, sys.stdout)
        sys.stdout.write('\n')

    def close(self):
        pass
