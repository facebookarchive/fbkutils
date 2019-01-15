#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from benchpress.plugins.hooks.cpu_limit import CpuLimit
from benchpress.plugins.hooks.file import FileHook
from benchpress.plugins.hooks.shell import ShellHook


def register_hooks(factory):
    factory.register("cpu-limit", CpuLimit)
    factory.register("file", FileHook)
    factory.register("shell", ShellHook)
