#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import logging
import os
import sys

import click
import yaml
from benchpress.lib.reporter import JSONReporter, StdoutReporter
from benchpress.lib.reporter_factory import ReporterFactory
from benchpress.suites.suite import DiscoveredTestCase, Suite


# register reporter plugins before setting up the parser
ReporterFactory.register("stdout", StdoutReporter)
ReporterFactory.register("default", StdoutReporter)
ReporterFactory.register("json", JSONReporter)


@click.group()
@click.option("-v", "--verbose", count=True, default=0)
@click.option(
    "-s",
    "--suites",
    type=click.File("r"),
    default=lambda: os.environ.get("BENCHPRESS_SUITES", "suites.yml"),
)
@click.pass_context
def benchpress(ctx, verbose, suites):
    ctx.ensure_object(dict)

    # warn is 30, should default to 30 when verbose=0
    # each level below warning is 10 less than the previous
    log_level = verbose * (-10) + 30
    logging.basicConfig(format="%(levelname)s:%(name)s: %(message)s", level=log_level)
    logger = logging.getLogger(__name__)

    logger.info('Loading suites from "{}"'.format(suites))
    suite_configs = yaml.load(suites)

    suites = [Suite.instantiate(s) for s in suite_configs]
    suites = {s.name: s for s in suites}
    ctx.obj["suites"] = suites

    logger.info("Loaded {} test suites".format(len(suites)))


@benchpress.command()
@click.option("--suite", "-s")
@click.option("--case", "-c", "cases", multiple=True)
@click.option("--json", "-j", "output_json", is_flag=True)
@click.pass_context
def run(ctx, suite, cases, output_json):
    logger = logging.getLogger("benchpress.run")

    reporter = ReporterFactory.create("default")
    if suite not in ctx.obj["suites"]:
        logger.error('No suite "{}" found'.format(suite))
        sys.exit(1)
    suite = ctx.obj["suites"][suite]

    print(f'Running "{suite.name}"')
    if not cases:
        cases = None
    else:
        cases = [DiscoveredTestCase(name=c, description="") for c in cases]
    results = suite.run(cases)
    if output_json:
        reporter = ReporterFactory.create("json")
    reporter.report(suite, results)
    reporter.close()


@benchpress.command("list")
@click.argument("suite", required=False)
@click.pass_context
def list_suites(ctx, suite):
    suites = ctx.obj["suites"]
    if suite:
        # list test cases in a suite
        suite = suites[suite]
        cases = suite.discover_cases()
        print(f'Test cases in "{suite.name}":')
        for case in cases:
            print(f"  {case.name}: {case.description}")
        return
    for suite in suites.values():
        click.echo("{}: {}".format(suite.name, suite.description))
