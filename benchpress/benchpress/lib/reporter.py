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
    def report(self, job, metrics, anomalies):
        """Save job metrics somewhere in existing monitoring infrastructure.

        Args:
            job (Job): job that was run
            metrics (Metrics): metrics that were exported by job
            anomalies (list of (name, value, min, max)): anomalies
        """
        pass

    @abstractmethod
    def close(self):
        """Do whatever necessary cleanup is required after all jobs are finished.
        """
        pass


class StdoutReporter(Reporter):
    """Default reporter implementation, logs a JSON object to stdout."""
    def report(self, job, metrics, anomalies):
        """Log JSON report to stdout.
        Attempt to detect whether a real person is running the program then
        pretty print the JSON, otherwise print it without linebreaks and
        unsorted keys.
        """
        # use isatty as a proxy for if a real human is running this
        if sys.stdout.isatty():
            # if on the console, write in a more human-readable form
            print('Metrics')
            print('-------')
            for key in sorted(metrics.names):
                print('{}={}'.format(key, metrics[key]))
            if anomalies:
                print('Possible anomalies')
                print('------------------')
                anomaly_names = [a[0] for a in anomalies]
                anomalies = {a[0]: a for a in anomalies}
                for name in sorted(anomaly_names):
                    _, val, min, max = anomalies[name]
                    print('{}={} not in range ({}, {})'.format(name, val, min, max))
        else:
            obj = {
                'metrics': metrics.metrics(),
                'anomalies': anomalies
            }
            json.dump(metrics.metrics(), sys.stdout)
        sys.stdout.write('\n')

    def close(self):
        pass
