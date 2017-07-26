#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from abc import ABCMeta, abstractmethod


class Hook(object, metaclass=ABCMeta):
    """Hook allows jobs to run some Python code before/after a job runs."""

    @abstractmethod
    def before_job(self, opts, job):
        """Do something to setup before this job.

        Args:
            opts (dict): user-defined options for this hook
        """

    @abstractmethod
    def after_job(self, opts, job):
        """Do something to teardown after this job.

        Args:
            opts (dict): user-defined options for this hook
        """
