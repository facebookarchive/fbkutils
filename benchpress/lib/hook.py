#!/usr/bin/env python3

from abc import ABCMeta, abstractmethod


class Hook(object, metaclass=ABCMeta):
    """Hook allows jobs to run some Python code before/after a job runs."""

    @abstractmethod
    def before_job(self, opts):
        """Do something to setup before this job.

        Args:
            opts (dict): user-defined options for this hook
        """
        pass

    @abstractmethod
    def after_job(self, opts):
        """Do something to teardown after this job.

        Args:
            opts (dict): user-defined options for this hook
        """
        pass
