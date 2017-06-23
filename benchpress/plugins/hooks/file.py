#!/usr/bin/env python3

import os
import shutil

from lib.hook import Hook


class FileHook(Hook):
    """FileHook provides the ability to create and delete files/directories.
    Options are specified as a list of dictionaries - each dictionary must have
    a 'type' and a 'path', 'type' is either 'dir' or 'file', and path is where
    it will live on the filesystem. Files/directories are created before the
    job runs and destroyed after.
    """

    def before_job(self, opts):
        for opt in opts:
            if opt['type'] == 'dir':
                os.makedirs(opt['path'], exist_ok=True)
            if opt['type'] == 'file':
                os.mknod(opt['path'])

    def after_job(self, opts):
        for opt in opts:
            if opt['type'] == 'dir':
                shutil.rmtree(opt['path'])
            if opt['type'] == 'file':
                os.unlink(opt['path'])
