#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import argparse
import logging
import sys

import click
import yaml
from benchpress.lib.job import Job
from benchpress.lib.reporter import StdoutReporter
from benchpress.lib.reporter_factory import ReporterFactory


# register reporter plugins before setting up the parser
ReporterFactory.register("stdout", StdoutReporter)
ReporterFactory.register("default", StdoutReporter)


@click.group()
@click.option("-v", "--verbose", count=True, default=0)
@click.option("-b", "--benchmarks", type=click.File("r"), default="benchmarks.yml")
@click.option("-j", "--jobs", type=click.File("r"), default="jobs.yml")
@click.pass_context
def benchpress(ctx, verbose, benchmarks, jobs):
    ctx.ensure_object(dict)

    # warn is 30, should default to 30 when verbose=0
    # each level below warning is 10 less than the previous
    log_level = verbose * (-10) + 30
    logging.basicConfig(format="%(levelname)s:%(name)s: %(message)s", level=log_level)
    logger = logging.getLogger(__name__)

    logger.info('Loading benchmarks from "{}"'.format(benchmarks))
    benchmarks = yaml.load(benchmarks)

    logger.info('Loading jobs from "{}"'.format(jobs))
    job_configs = yaml.load(jobs)

    jobs = [Job(j, benchmarks[j["benchmark"]]) for j in job_configs if "tests" not in j]
    jobs = {j.name: j for j in jobs}
    ctx.obj["jobs"] = jobs

    logger.info("Loaded {} benchmarks and {} jobs".format(len(benchmarks), len(jobs)))


@benchpress.command()
@click.option("--job", multiple=True)
@click.pass_context
def run(ctx, job):
    job_names = job
    logger = logging.getLogger("benchpress.run")

    reporter = ReporterFactory.create("default")
    jobs = ctx.obj["jobs"]
    for name in job_names:
        if name not in jobs:
            logger.error('No job "{}" found'.format(name))
            sys.exit(1)

    jobs = {name: jobs[name] for name in job_names}
    jobs = jobs.values()
    click.echo("Will run {} job(s)".format(len(jobs)))

    for job in jobs:
        print('Running "{}": {}'.format(job.name, job.description))
        metrics = job.run()
        reporter.report(job, metrics)

    reporter.close()


@benchpress.command("list")
@click.pass_context
def list_jobs(ctx):
    jobs = ctx.obj["jobs"]
    for job in jobs.values():
        click.echo("{}: {}".format(job.name, job.description))
