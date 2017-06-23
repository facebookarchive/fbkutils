#!/usr/bin/env python3

from .factory import BaseFactory
from .parser import Parser

from plugins.parsers import register_parsers

ParserFactory = BaseFactory(Parser)

# register third-party parsers with the factory
register_parsers(ParserFactory)
