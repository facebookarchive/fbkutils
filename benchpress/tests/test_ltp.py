#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import unittest
from unittest.mock import MagicMock

from benchpress.lib.parser import TestCaseResult, TestStatus
from benchpress.suites.ltp import LtpSuite


class TestLtp(unittest.TestCase):
    def setUp(self):
        self.parser = LtpSuite(MagicMock())

    def test_sample_output(self):
        """Can parse output from running ltp fs tests"""
        # sample output from running ltp fs tests
        output = """INFO: creating /root/ltp/output directory
INFO: creating /root/ltp/results directory
Checking for required user/group ids

'nobody' user id and group found.
'bin' user id and group found.
'daemon' user id and group found.
Users group found.
Sys group found.
Required users/groups exist.
If some fields are empty or look unusual you may have an old version.
Compare to the current minimal requirements in Documentation/Changes.

<<<test_start>>>
tag=gf14 stime=1548867875
cmdline="growfiles -W gf14 -b -e 1 -u -i 0 -L 20 -w -l -C 1 -T 10 -f glseek19 -S 2 -d $TMPDIR"
contacts=""
analysis=exit
<<<test_output>>>
gf14        1  TBROK  :  Test passed
<<<execution_status>>>
initiation_status="ok"
duration=15 termination_type=exited termination_id=0 corefile=no
cutime=535 cstime=844
<<<test_end>>>
<<<test_start>>>
tag=gf15 stime=1548867890
cmdline="growfiles -W gf15 -b -e 1 -u -r 1-49600 -I r -u -i 0 -L 120 -f Lgfile1 -d $TMPDIR"
contacts=""
analysis=exit
<<<test_output>>>
gf15        1  TPASS  :  Test passed
gf15        2  TPASS  :  Test passed
<<<execution_status>>>
initiation_status="ok"
duration=19 termination_type=exited termination_id=0 corefile=no
cutime=1673 cstime=212
<<<test_end>>>
<<<test_start>>>
tag=gf16 stime=1548867909
cmdline="growfiles -W gf16 -b -e 1 -i 0 -L 120 -u -g 4090 -T 101 -t 408990 -l -C 10 -c 1000 -S 10 -f Lgf02_ -d $TMPDIR"
contacts=""
analysis=exit
<<<test_output>>>
gf16        1  TFAIL  :  Test passed
<<<execution_status>>>
initiation_status="ok"
duration=121 termination_type=exited termination_id=0 corefile=no
cutime=10074 cstime=1922
<<<test_end>>>
<<<test_start>>>
tag=quota_remount_test01 stime=1548866311
cmdline="quota_remount_test01.sh"
tag=gf16 stime=1548867909
cmdline="growfiles -W gf16 -b -e 1 -i 0 -L 120 -u -g 4090 -T 101 -t 408990 -l -C 10 -c 1000 -S 10 -f Lgf02_ -d $TMPDIR"
contacts=""
analysis=exit
<<<test_output>>>
incrementing stop
quota_remount_test01    0  TINFO  :  Successfully mounted the File System
quota_remount_test01    0  TINFO  :  Successfully Created Quota Files
quotaon: using /tmp/ltp-gR1S51MtVi/mnt/aquota.group on /dev/loop2 [/tmp/ltp-gR1S51MtVi/mnt]: No such process
quotaon: Quota format not supported in kernel.
quotaon: using /tmp/ltp-gR1S51MtVi/mnt/aquota.user on /dev/loop2 [/tmp/ltp-gR1S51MtVi/mnt]: No such process
quotaon: Quota format not supported in kernel.
Could not turn quota on
quota_remount_test01    1  TFAIL  :  ltpapicmd.c:188: Quota on Remount Failed
gf16        1  TFAIL  :  Test passed
<<<execution_status>>>
initiation_status="ok"
duration=1 termination_type=exited termination_id=2 corefile=no
cutime=1 cstime=4
duration=121 termination_type=exited termination_id=0 corefile=no
cutime=10074 cstime=1922
<<<test_end>>>
        """
        results = list(self.parser.parse(output.split("\n"), None, 0))
        self.maxDiff = None
        self.assertEqual(
            [
                TestCaseResult(
                    name="gf14_1",
                    status=TestStatus.FAILED,
                    details="""
gf14        1  TBROK  :  Test passed
                """.strip(),
                ),
                TestCaseResult(
                    name="gf15_1",
                    status=TestStatus.PASSED,
                    details="""
gf15        1  TPASS  :  Test passed
gf15        2  TPASS  :  Test passed
                """.strip(),
                ),
                TestCaseResult(
                    name="gf15_2",
                    status=TestStatus.PASSED,
                    details="""
gf15        1  TPASS  :  Test passed
gf15        2  TPASS  :  Test passed
                """.strip(),
                ),
                TestCaseResult(
                    name="gf16_1",
                    status=TestStatus.FAILED,
                    details="""
gf16        1  TFAIL  :  Test passed
                """.strip(),
                ),
                TestCaseResult(
                    name="quota_remount_test01_1",
                    status=TestStatus.FAILED,
                    details="""
incrementing stop
quota_remount_test01    0  TINFO  :  Successfully mounted the File System
quota_remount_test01    0  TINFO  :  Successfully Created Quota Files
quotaon: using /tmp/ltp-gR1S51MtVi/mnt/aquota.group on /dev/loop2 [/tmp/ltp-gR1S51MtVi/mnt]: No such process
quotaon: Quota format not supported in kernel.
quotaon: using /tmp/ltp-gR1S51MtVi/mnt/aquota.user on /dev/loop2 [/tmp/ltp-gR1S51MtVi/mnt]: No such process
quotaon: Quota format not supported in kernel.
Could not turn quota on
quota_remount_test01    1  TFAIL  :  ltpapicmd.c:188: Quota on Remount Failed
gf16        1  TFAIL  :  Test passed
                """.strip(),
                ),
                TestCaseResult(
                    name="gf16_1",
                    status=TestStatus.FAILED,
                    details="""
incrementing stop
quota_remount_test01    0  TINFO  :  Successfully mounted the File System
quota_remount_test01    0  TINFO  :  Successfully Created Quota Files
quotaon: using /tmp/ltp-gR1S51MtVi/mnt/aquota.group on /dev/loop2 [/tmp/ltp-gR1S51MtVi/mnt]: No such process
quotaon: Quota format not supported in kernel.
quotaon: using /tmp/ltp-gR1S51MtVi/mnt/aquota.user on /dev/loop2 [/tmp/ltp-gR1S51MtVi/mnt]: No such process
quotaon: Quota format not supported in kernel.
Could not turn quota on
quota_remount_test01    1  TFAIL  :  ltpapicmd.c:188: Quota on Remount Failed
gf16        1  TFAIL  :  Test passed
                """.strip(),
                ),
            ],
            results,
        )


if __name__ == "__main__":
    unittest.main()
