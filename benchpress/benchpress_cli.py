#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

# main functionality is actually provided in cli/main.py
from benchpress.cli.main import main
from benchpress.lib.reporter import StdoutReporter
from benchpress.lib.reporter_factory import ReporterFactory


# this makes it possible to install as a script with poetry or to just run this
# file as an executable
def entry_point():
    # register a default class for reporting metrics
    ReporterFactory.register("default", StdoutReporter)
    main()


if __name__ == "__main__":
    entry_point()
