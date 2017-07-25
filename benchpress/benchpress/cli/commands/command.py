#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from abc import ABCMeta, abstractmethod


class BenchpressCommand(object, metaclass=ABCMeta):

    @abstractmethod
    def populate_parser(self, parser):
        pass

    @abstractmethod
    def run(self, args, jobs):
        pass
