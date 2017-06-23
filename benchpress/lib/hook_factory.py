#!/usr/bin/env python3

from .factory import BaseFactory
from .hook import Hook

from plugins.hooks import register_hooks

HookFactory = BaseFactory(Hook)

# register third-party hooks with the factory
register_hooks(HookFactory)
