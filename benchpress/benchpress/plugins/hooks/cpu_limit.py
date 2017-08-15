#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import logging

from benchpress.lib.hook import Hook

logger = logging.getLogger(__name__)


class CpuLimit(Hook):
    """CpuLimit hook allows you to limit the benchmark to a set of CPUs using
    `taskset`. The only option is a hex string bitmask that is the CPU mask
    passed to `taskset`, for each bit, if there is a 1 the CPU is enabled for
    the benchmark process, otherwise it's disabled.
    """

    def before_job(self, opts, job):
        mask = str(opts)
        # try to parse the mask as a hex string as a basic sanity check
        try:
            int(mask, 16)
        except ValueError:
            raise ValueError('{} is not a valid CPU mask'.format(mask))

        # modify the job config to run taskset with the given mask instead of
        # directly running the benchmark binary
        binary = job.config['path']
        job.args = [mask, binary] + job.args
        job.binary = 'taskset'

    def after_job(self, opts, job):
        pass
