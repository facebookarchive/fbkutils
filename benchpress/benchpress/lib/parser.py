#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from abc import ABCMeta, abstractmethod


class Parser(object, metaclass=ABCMeta):
    """Parser is the link between benchmark output and the rest of the system.
    A Parser is given the benchmark's stdout and stderr and returns the exported
    metrics.
    """

    @abstractmethod
    def parse(self, stdout, stderr, returncode):
        """Take stdout/stderr and convert it to a dictionary of metrics.

        Args:
            stdout (list of str): stdout of benchmark process split on newline
            stderr (list of str): stderr of benchmark process split on newline
            returncode (int): subprocess return code

        Returns:
            (dict): metrics mapping name -> value - keys can be nested or flat
                with dot-separated names
        """
        pass
