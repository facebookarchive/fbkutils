#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from benchpress.plugins.parsers.generic import JSONParser
from benchpress.plugins.parsers.ltp import LtpParser
from benchpress.plugins.parsers.packetdrill_parser import PacketdrillParser
from benchpress.plugins.parsers.returncode import ReturncodeParser
from benchpress.plugins.parsers.xfstests_parser import XfstestsParser


def register_parsers(factory):
    factory.register("json", JSONParser)
    factory.register("ltp", LtpParser)
    factory.register("returncode", ReturncodeParser)
    factory.register("packetdrill", PacketdrillParser)
    factory.register("xfstests", XfstestsParser)
