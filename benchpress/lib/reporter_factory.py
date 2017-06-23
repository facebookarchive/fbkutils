#!/usr/bin/env python3

from .factory import BaseFactory
from .reporter import Reporter

ReporterFactory = BaseFactory(Reporter)
