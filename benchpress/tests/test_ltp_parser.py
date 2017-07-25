#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import unittest

from benchpress.plugins.parsers.ltp import LtpParser


class TestLtpParser(unittest.TestCase):

    def setUp(self):
        self.parser = LtpParser()

    def test_sample_output(self):
        """Can parse output from running ltp fs tests"""
        # sample output from running ltp fs tests
        output = [
            'INFO: creating /opt/ltp/results directory',
            'Checking for required user/group ids',
            '\'nobody\' user id and group found.',
            '\'bin\' user id and group found.',
            '\'daemon\' user id and group found.',
            'Users group found.',
            'Sys group found.',
            'Required users/groups exist.',
            'no big block device was specified on commandline.',
            'Tests which require a big block device are disabled.',
            'You can specify it with option -z',
            'INFO: Test start time: Tue Jul 25 12:58:54 PDT 2017',
            'COMMAND:    /opt/ltp/bin/ltp-pan  -q  -e -S   -a 20584     -n 20584  -p  -f /tmp/ltp-htqf01qm5r/alltests -l /opt/ltp/results/LTP_RUN_ON-2017_07_25-12h_58m_54s.log  -C /opt/ltp/output/LTP_RUN_ON-2017_07_25-12h_58m_54s.failed -T /opt/ltp/output/LTP_RUN_ON-2017_07_25-12h_58m_54s.tconf',  # noqa
            'LOG File: /opt/ltp/results/LTP_RUN_ON-2017_07_25-12h_58m_54s.log',
            'FAILED COMMAND File: /opt/ltp/output/LTP_RUN_ON-2017_07_25-12h_58m_54s.failed',  #noqa
            'TCONF COMMAND File: /opt/ltp/output/LTP_RUN_ON-2017_07_25-12h_58m_54s.tconf',  #noqa
            'Running tests.......',
            'growfiles(gf01): 20631 growfiles.c/2037: 254087 tlibio.c/961 writev(6, iov, 1) nbyte:1 ret:-1, errno=28 No space left on device',  #noqa
            'gf01        1  TFAIL  :  growfiles.c:132: Test failed',
            'gf02        1  TPASS  :  Test passed',
            'gf03        1  TINFO  :  Some useless info',
            'gf03        1  TPASS  :  Test passed',
            'gf04        1  TWARN  :  Test warning',
            'gf05        1  TBROK  :  Test brok',
        ]
        metrics = self.parser.parse(output, None, 0)
        self.assertDictEqual({
            'gf01_1': False,
            'gf02_1': True,
            'gf03_1': True,
            'gf04_1': False,
            'gf05_1': False,
        }, metrics)

if __name__ == '__main__':
    unittest.main()
