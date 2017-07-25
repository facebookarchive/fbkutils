#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from benchpress.lib.hook import Hook


class NoopHook(Hook):
    """NoopHook is the default hook used if no other hooks are specified. As the
    name suggests, it doesn't do anything.
    """

    def before_job(self, opts):
        pass

    def after_job(self, opts):
        pass
