#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import errno
import logging
import subprocess
import sys
from subprocess import CalledProcessError, TimeoutExpired

from benchpress.lib.hook_factory import HookFactory
from benchpress.lib.parser_factory import ParserFactory


logger = logging.getLogger(__name__)


class Job(object):
    """Holds the run configuration for an individual job.
    A Job starts it's default config based on the benchmark configuration that
    it references. The binary defined in the benchmark is run according to the
    configuration of this job.

    Attributes:
        name (str): short name to identify job
        description (str): longer description to state intent of job
        tolerances (dict): percentage tolerance around the mean of historical
                           results
        config (dict): raw configuration dictionary
    """

    def __init__(self, job_config, benchmark_config):
        """Create a Job with the default benchmark_config and the specific job
        config

        Args:
            config (dict): job config
            benchmark_config (dict): benchmark (aka default) config
        """
        # start with the config being the benchmark config and then update it
        # with the job config so that a job can override any options in the
        # benchmark config
        config = benchmark_config
        # TODO(vmagro) should there be some basic sanity check that a job_config
        # contains certain fields?
        config.update(job_config)
        self.config = config

        self.name = config["name"]
        self.description = config["description"]

        self.binary = config["path"]
        self.parser = ParserFactory.create(config["parser"])
        self.check_returncode = config.get("check_returncode", True)
        self.timeout = config.get("timeout", None)
        self.timeout_is_pass = config.get("timeout_is_pass", False)
        # if tee_output is True, the stdout and stderr commands of the child
        # process will be copied onto the stdout and stderr of benchpress
        # if this option is a string, the output will be written to the file
        # named by this value
        self.tee_output = config.get("tee_output", False)

        self.hooks = config.get("hooks", [])
        self.hooks = [
            (HookFactory.create(h["hook"]), h.get("options", None)) for h in self.hooks
        ]
        # self.hooks is list of (hook, options)

        self.tolerances = config.get("tolerances", {})

        self.args = self.arg_list(config["args"])

    @staticmethod
    def arg_list(args):
        """Convert argument definitions to a list suitable for subprocess.
        """
        if isinstance(args, list):
            return args

        l = []
        for key, val in args.items():
            l.append("--" + key)
            if val is not None:
                l.append(str(val))
        return l

    def run(self):
        """Run the benchmark and return the metrics that are reported.
        """
        # take care of preprocessing setup via hook
        logger.info('Running setup hooks for "{}"'.format(self.name))
        for hook, opts in self.hooks:
            logger.info("Running %s %s", hook, opts)
            hook.before_job(opts, self)

        try:
            logger.info('Starting "{}"'.format(self.name))
            cmd = [self.binary] + self.args
            try:
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=self.timeout,
                    encoding="utf-8",
                )
            except TimeoutExpired as e:
                stdout, stderr = e.stdout, e.stderr
                if not self.timeout_is_pass:
                    logger.error(
                        "Job timed out\n"
                        "stdout:\n{}\nstderr:\n{}".format(stdout, stderr)
                    )
                    raise
                returncode = 0
            else:
                stdout, stderr = process.stdout, process.stderr
                returncode = process.returncode
            if self.check_returncode and returncode != 0:
                output = "stdout:\n{}\nstderr:\n{}".format(stdout, stderr)
                cmd = " ".join(cmd)
                raise CalledProcessError(process.returncode, cmd, output)

            # optionally copy stdout/err of the child process to our own
            if self.tee_output:
                # default to stdout if no filename given
                tee = sys.stdout
                # if a file was specified, write to that file instead
                if isinstance(self.tee_output, str):
                    tee = open(self.tee_output, "w")
                # do this so each line is prefixed with stdout
                for line in stdout.splitlines():
                    tee.write(f"stdout: {line}\n")
                for line in stderr.splitlines():
                    tee.write(f"stderr: {line}\n")
                # close the output if it was a file
                if tee != sys.stdout:
                    tee.close()

            logger.info('Parsing results for "{}"'.format(self.name))
            try:
                return self.parser.parse(
                    stdout.splitlines(), stderr.splitlines(), returncode
                )
            except Exception:
                logger.error(
                    "Failed to parse results, this might mean the" " benchmark failed"
                )
                logger.error("stdout:\n{}".format(stdout))
                logger.error("stderr:\n{}".format(stderr))
                raise
        except OSError as e:
            logger.error('"{}" failed ({})'.format(self.name, e))
            if e.errno == errno.ENOENT:
                logger.error("Binary not found, did you forget to install it?")
            raise  # make sure it passes the exception up the chain
        except CalledProcessError as e:
            logger.error(e.output)
            raise  # make sure it passes the exception up the chain
        finally:
            logger.info('Running cleanup hooks for "{}"'.format(self.name))
            # run hooks in reverse this time so it operates like a stack
            for hook, opts in reversed(self.hooks):
                hook.after_job(opts, self)

    @property
    def safe_name(self):
        return self.name.replace(" ", "_")
