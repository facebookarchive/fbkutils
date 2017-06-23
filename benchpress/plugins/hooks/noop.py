#!/usr/bin/env python3

from lib.hook import Hook


class NoopHook(Hook):
    """NoopHook is the default hook used if no other hooks are specified. As the
    name suggests, it doesn't do anything.
    """

    def before_job(self, opts):
        pass

    def after_job(self, opts):
        pass
