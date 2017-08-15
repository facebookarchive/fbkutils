#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from collections import defaultdict


def analyze(current, job, history):
    """Given a Metrics object and the job, return a list of
    metrics that are outside the acceptable range. Acceptable range is based on
    a percentage tolerance defined in the job configuration centered around the
    the average of historical results.

    Args:
        current (Metrics): current job results
        job (Job): job that was run
        history (History): history interface
    Returns:
        list (metric name, value, min, max): metrics outside acceptable range
    """
    historical = history.load_historical_results(job)
    results_by_metrics = defaultdict(list)
    for entry in historical:
        metrics = entry.metrics.performance_metrics()
        for key, value in metrics.items():
            results_by_metrics[key].append(value)
    averages = {metric: sum(results) / len(results)
                for metric, results in results_by_metrics.items()}
    outside_range = []
    for metric, tolerance in job.tolerances.items():
        average = averages[metric]
        value = current[metric]
        min = average * (1 - tolerance)
        max = average * (1 + tolerance)
        if value < min or value > max:
            outside_range.append((metric, value, min, max))
    return outside_range
