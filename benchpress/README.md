Benchpress
==========

Benchpress (BENCHmark Pluggable haRnESS) is a framework for running kernel
correctness test suites. The name is historical, when the project was originally
intended to run benchmarks, but it has since pivoted to running correctness
tests only.
Benchpress takes a configuration-based approach to running tests, specifying
configuration in yaml files.

Installation
------------

`benchpress` requires `python3`  
`benchpress` supports `python` 3.3 and higher, and is currently tested on
`python 3.3,3.4,3.5` and `3.6`.

`benchpress` can be installed with `pip install fb-benchpress`

Running benchpress
------------------

The `benchpress` cli is simple to use, simply give it the paths to the
benchmarks and jobs definition files, along with an optional list of
benchmark jobs to run (if this is omitted all defined jobs are run).

Examples:  
List available tests:  
`benchpress -b benchmarks.yml -j jobs/jobs.yml list`  
Run all tests defined in `jobs/jobs.yml`:  
`benchpress -b benchmarks.yml -j jobs/jobs.yml run`  
Run just the "fio aio" test:  
`benchpress -b benchmarks.yml -j jobs/jobs.yml run "fio aio"`  

How benchpress works
--------------------

`benchpress` is configured with 'jobs' and 'suites'. A suite is a
reference to a binary (that usually can be run with different arguments).
A job is a specific run of that suite with a specific configuration (eg: suite = xfstests, job = xfstests-btrfs)


Parsers
-------

Once you've defined your benchmarks and jobs, each benchmark needs a parser. A
parser is a piece of Python code that can parse the output of a benchmark
binary. A Parser is a subclass of `benchpress.lib.parser.Parser`, it must
implement the `parse` method, which returns a dictionary of metrics given the
stdout and stderr of the binary.

Adding a plugin entails writing the `Parser` implementation and adding it to
`register_parsers` in `benchpress/plugins/parsers/__init__.py`

Reporting
---------

By default, `benchpress` simply reports job results to stdout, this can be
customized by creating a subclass of `benchpress.lib.reporter.Reporter` and
registering it with the `ReporterFactory`
