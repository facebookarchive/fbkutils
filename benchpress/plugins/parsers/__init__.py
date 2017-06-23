#!/usr/bin/env python3

from .fio import FioParser
from .schbench import SchbenchParser


def register_parsers(factory):
    factory.register('fio', FioParser)
    factory.register('schbench', SchbenchParser)
