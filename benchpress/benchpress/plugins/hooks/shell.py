#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import logging
import os
import shlex
import subprocess

from benchpress.lib.hook import Hook

logger = logging.getLogger(__name__)


class ShellHook(Hook):
    """ShellHook provides the ability to run arbitrary shell commands
    before/after a job
    Options are a dictioanry of 'before' and 'after' lists with a string for
    each command to run.
    Commands are not run in a shell, so 'cd's are converted to os.chdir
    A 'cd' can be executed and will change the working directory of the running
    test binary, and is reverted to the previous working directory during the
    post hook.
    """

    def __init__(self):
        self.original_dir = os.getcwd()

    @staticmethod
    def run_commands(cmds):
        for cmd in cmds:
            cmd = shlex.split(cmd)
            if cmd[0] == 'cd':
                assert len(cmd) == 2
                dst = cmd[1]
                logger.info('Switching to dir "%s"', dst)
                os.chdir(dst)
            else:
                subprocess.check_call(cmd)

    def before_job(self, opts, job=None):
        self.original_dir = os.getcwd()
        if 'before' in opts:
            self.run_commands(opts['before'])

    def after_job(self, opts, job=None):
        if 'after' in opts:
            self.run_commands(opts['after'])

        # cd back to the original dir in case a command changed it
        if os.getcwd() != self.original_dir:
            logger.info('Returning to "%s"', self.original_dir)
            os.chdir(self.original_dir)
