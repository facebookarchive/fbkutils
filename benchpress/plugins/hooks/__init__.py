#!/usr/bin/env python3

from .noop import NoopHook
from .file import FileHook


def register_hooks(factory):
    factory.register('noop', NoopHook)
    factory.register('file', FileHook)
