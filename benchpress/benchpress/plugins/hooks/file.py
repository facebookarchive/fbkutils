#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import errno
import logging
import os
import shutil

from benchpress.lib.hook import Hook

logger = logging.getLogger(__name__)


class FileHook(Hook):
    """FileHook provides the ability to create and delete files/directories.
    Options are specified as a list of dictionaries - each dictionary must have
    a 'type' and a 'path', 'type' is either 'dir' or 'file', and path is where
    it will live on the filesystem. Files/directories are created before the
    job runs and destroyed after.
    """

    def before_job(self, opts, job):
        for opt in opts:
            path = opt['path']
            logger.info('Creating "{}"'.format(path))
            if opt['type'] == 'dir':
                try:
                    os.makedirs(path)
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        logger.warning('"{}" already exists, proceeding anyway'
                                       .format(path))
                    else:
                        # other errors should be fatal
                        raise
            if opt['type'] == 'file':
                os.mknod(path)

    def after_job(self, opts, job):
        for opt in opts:
            path = opt['path']
            logger.info('Deleting "{}"'.format(path))
            if opt['type'] == 'dir':
                shutil.rmtree(path)
            if opt['type'] == 'file':
                os.unlink(path)
