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
from abc import abstractmethod
from dataclasses import dataclass
from subprocess import CalledProcessError, TimeoutExpired
from typing import Any, Dict, Iterable, List, Optional, Type

from benchpress.lib.hook_factory import HookFactory
from benchpress.lib.parser import TestCaseResult


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiscoveredTestCase(object):
    name: str
    description: Optional[str]


class SuiteMeta(type):

    suite_classes: Dict[str, Type["Suite"]] = {}

    @classmethod
    def instantiate(metacls, config: Dict[str, Any]) -> "Suite":
        runner = config.get("runner", "generic")
        if runner not in metacls.suite_classes:
            raise RuntimeError(f'No such suite runner "{runner}"')
        suite_cls = metacls.suite_classes[runner]
        return suite_cls(config)

    def __init__(cls, name, bases, namespace, **kwargs):
        super().__init__(name, bases, namespace, **kwargs)
        if "NAME" in namespace:
            SuiteMeta.suite_classes[namespace["NAME"]] = cls


class Suite(metaclass=SuiteMeta):
    def __init__(self, config: Dict[str, Any]):
        self.config = config

        self.name = config["name"]
        self.description = config["description"]

        self.binary = config["path"]
        self.args = self.arg_list(config["args"])
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

    @staticmethod
    def arg_list(args):
        """Convert argument definitions to a list suitable for subprocess."""
        if isinstance(args, list):
            return args

        lst = []
        for key, val in args.items():
            lst.append("--" + key)
            if val is not None:
                lst.append(str(val))
        return lst

    def run_pre_hooks(self):
        logger.info('Running setup hooks for "{}"'.format(self.name))
        for hook, opts in self.hooks:
            logger.info("Running %s %s", hook, opts)
            hook.before(opts, self)

    def run_post_hooks(self):
        logger.info('Running cleanup hooks for "{}"'.format(self.name))
        # run hooks in reverse this time so it operates like a stack
        for hook, opts in reversed(self.hooks):
            hook.after(opts, self)

    def run_to_completion(self) -> subprocess.CompletedProcess:
        """run_to_completion can be used when streaming output is not requried"""
        logger.info('Starting "{}"'.format(self.name))
        cmd = [self.binary] + self.args
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
            )
            stdout, stderr = proc.communicate(None, timeout=self.timeout)
            # other parts of the code rely on stdout/err being strings on the
            # process itself (this is how subprocess.run works)
            proc.stdout = stdout
            proc.stderr = stderr
            if self.check_returncode:
                if proc.returncode != 0:
                    raise CalledProcessError(
                        proc.returncode, cmd, output=stdout, stderr=stderr
                    )
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

            return proc
        except OSError as e:
            logger.error('"{}" failed ({})'.format(self.name, e))
            if e.errno == errno.ENOENT:
                logger.error("Binary not found, did you forget to install it?")
            raise  # make sure it passes the exception up the chain
        except CalledProcessError as e:
            logger.error(e.output)
            raise  # make sure it passes the exception up the chain
        except TimeoutExpired:
            proc.kill()
            raise

    def discover_cases(self) -> List[DiscoveredTestCase]:
        return [DiscoveredTestCase(name="exec", description="does the test exit(0)")]

    @abstractmethod
    def parse(
        self, stdout: List[str], stderr: List[str], returncode: Optional[int]
    ) -> Iterable[TestCaseResult]:
        pass

    def run(
        self, cases: Optional[List[DiscoveredTestCase]] = None
    ) -> Iterable[TestCaseResult]:
        # default run implementation requires a parse method that takes
        # std{out,err} as lists of strings
        self.run_pre_hooks()
        try:
            proc = self.run_to_completion()
            stdout = proc.stdout.splitlines()
            stderr = proc.stderr.splitlines()
            return self.parse(stdout, stderr, proc.returncode)
        except TimeoutExpired as e:
            stdout, stderr = e.stdout, e.stderr
            if not self.timeout_is_pass:
                logger.error(
                    "Job timed out\n" "stdout:\n{}\nstderr:\n{}".format(stdout, stderr)
                )
                raise
            # if timeout was success, parse the output
            # we cannot get output from a timed out process that has children
            # because of how Popen.communicate works
            stdout = ["timed out as expected"]
            stderr = []
            # for generic tests, set the exit code to 0 even though it didn't
            # actually pass
            return self.parse(stdout, stderr, 0)
        finally:
            self.run_post_hooks()
