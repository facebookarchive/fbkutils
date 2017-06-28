#!/usr/bin/env python3

from abc import ABCMeta, abstractmethod

class BenchpressCommand(object, metaclass=ABCMeta):

    @abstractmethod
    def populate_parser(self, parser):
        pass

    @abstractmethod
    def run(self, args, jobs):
        pass
