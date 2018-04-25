#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import os
from pyfakefs import fake_filesystem_unittest
import subprocess
import unittest
from unittest.mock import patch

from benchpress.plugins.hooks.shell import ShellHook


FAKEDIR = '/tmp_benchpress_test'

class TestShellHook(fake_filesystem_unittest.TestCase):

    def setUp(self):
        self.setUpPyfakefs()
        self.original_dir = os.getcwd()
        self.hook = ShellHook()

        self.fs.CreateDirectory(FAKEDIR)

    def tearDown(self):
        os.chdir(self.original_dir)

    def test_cd_pre(self):
        """Can cd to change the working directory of a test"""
        self.assertNotEqual(FAKEDIR, os.getcwd())
        self.assertEqual(self.original_dir, os.getcwd())
        self.hook.before_job({'before': ['cd {}'.format(FAKEDIR)]})
        self.assertEqual(FAKEDIR, os.getcwd())

    def test_cd_pre_reset(self):
        """cd in a before hook is reset in post"""
        self.assertNotEqual(FAKEDIR, os.getcwd())
        self.assertEqual(self.original_dir, os.getcwd())
        self.hook.before_job({'before': ['cd {}'.format(FAKEDIR)]})
        self.assertEqual(FAKEDIR, os.getcwd())
        self.hook.after_job({'before': ['cd {}'.format(FAKEDIR)]})
        self.assertEqual(self.original_dir, os.getcwd())

    @patch('subprocess.check_call')
    def test_pre_subprocess(self, check_call):
        """pre hook executes commands"""
        self.hook.before_job({'before': ['echo "hello world" extra']})
        check_call.assert_called_once_with('echo "hello world" extra',
                                           shell=True,
                                           stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL)

    @patch('subprocess.check_call')
    def test_post_subprocess(self, check_call):
        """post hook executes commands"""
        self.hook.after_job({'after': ['echo "hello world" extra']})
        check_call.assert_called_once_with('echo "hello world" extra',
                                           shell=True,
                                           stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL)

    @patch('subprocess.check_call')
    def test_subprocess_fail(self, check_call):
        """Failing subprocess raises error"""
        with self.assertRaises(subprocess.CalledProcessError):
            check_call.side_effect = subprocess.CalledProcessError(1, '')
            self.hook.before_job({'before': ['true']})


if __name__ == '__main__':
    unittest.main()
