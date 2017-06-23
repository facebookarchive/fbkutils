#!/usr/bin/env python3

from abc import ABCMeta, abstractmethod


class Parser(object, metaclass=ABCMeta):
    """Parser is the link between benchmark output and the rest of the system.
    A Parser is given the benchmark's stdout and stderr and returns the exported
    metrics.
    """

    @abstractmethod
    def parse(self, output):
        """Take stdout/stderr and convert it to a dictionary of metrics.

        Args:
            output (list of str): stdout+stderr of benchmark process split on
                newline

        Returns:
            (dict): metrics mapping name -> value - keys can be nested or flat
                with dot-separated names
        """
        pass
