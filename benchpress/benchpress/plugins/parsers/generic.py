#!/usr/bin/env python3
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import json
import logging
import re

from benchpress.lib.parser import Parser

JSON_LIKE_REGEX = r'\s*([{\[].*?[}\]]\s*[}\]]*)\s*'
JSON_LIKE_MATCHER = re.compile(JSON_LIKE_REGEX)


class JSONParser(Parser):
    def parse(self, stdout, stderr, returncode):
        """Converts JSON output from either stdout or stderr into a dict.

        Assumes that either stdout or stderr contains a section of valid JSON,
        as expected by the `json` module. Returns only first match of JSON. It
        will try to scan for JSON-like string sections, REGEX is too simple
        could miss some contrived cases.

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
            process_output = ' '.join(output)
            possible_json_matches = JSON_LIKE_MATCHER.findall(process_output)
            for m in possible_json_matches:
                try:
                    return json.loads(m)
                except ValueError:
                    pass
            else:
                logging.warning(err_msg.format(ValueError(), kind))

        msg = "Couldn't not find or parse JSON from either stdout or stderr"
        raise ValueError(msg)
