#!/usr/bin/env python3
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import json
import logging

from benchpress.lib.parser import Parser


class JSONParser(Parser):
    def parse(self, stdout, stderr, returncode):
        """Converts JSON output from either stdout or stderr into a dict.

        Assumes that either stdout or stderr contains only valid JSON, as
        expected by the `json` module.

        Args:
            stdout (list[str]): Process's line-by-line stdout output.
            stderr (list[str]): Process's line-by-line stderr output.
            returncode (int): Process's exit status code.

        Returns:
            metrics (dict): Representation of either stdout or stderr.

        Raises:
            ValueError: When neither stdout nor stderr could be parsed as JSON.
        """
        err_msg = 'Failed to parse {1} as JSON: {0}'
        for (output, kind) in [(stdout, 'stdout'), (stderr, 'stderr')]:
            process_output = '\n'.join(output)
            try:
                return json.loads(process_output)
            except ValueError as err:
                logging.warning(err_msg.format(err, kind))

        msg = "Couldn't not find or parse JSON from either stdout or stderr"
        raise ValueError(msg)
