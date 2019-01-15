#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from benchpress.plugins.parsers import register_parsers

from .factory import BaseFactory
from .parser import Parser


ParserFactory = BaseFactory(Parser)

# register third-party parsers with the factory
register_parsers(ParserFactory)
