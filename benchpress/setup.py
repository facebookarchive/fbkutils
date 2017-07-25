#!/usr/bin/env python3
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from os import path
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


# Inspired by the example at https://pytest.org/latest/goodpractices.html
class NoseTestCommand(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # Run nose ensuring that argv simulates running nosetests directly
        import nose
        nose.run_exit(argv=['nosetests'])


here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='fbkbenchpress',
    version='0.1',
    description='A framework for running benchmarks and reporting metrics',
    long_description=long_description,
    author='Vinnie Magro',
    author_email='vmagro@fb.com',
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Testing',
        'Topic :: Utilities',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
    ],
    keywords='benchmark kernel test',
    url='https://www.github.com/facebook/fbkutils',
    packages=find_packages(exclude=['tests']),
    install_requires=['pyyaml'],
    tests_require=[
        'nose', 'coverage', 'mock', 'pyfakefs'
    ],
    setup_requires=[
        'flake8'
    ],
    cmdclass={'test': NoseTestCommand},
    scripts=['benchpress_cli.py'],
)
