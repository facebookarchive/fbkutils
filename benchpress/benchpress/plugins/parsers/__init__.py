#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from .fio import FioParser
from .generic import JSONParser
from .ltp import LtpParser
from .returncode import ReturncodeParser
from .schbench import SchbenchParser
from .silo import SiloParser


def register_parsers(factory):
    factory.register("fio", FioParser)
    factory.register("json", JSONParser)
    factory.register("ltp", LtpParser)
    factory.register("returncode", ReturncodeParser)
    factory.register("schbench", SchbenchParser)
    factory.register("silo", SiloParser)
