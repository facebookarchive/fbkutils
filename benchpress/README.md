Benchpress
==========

Benchpress (BENCHmark Pluggable haRnESS) is a framework for running benchmark
suites.  
Benchpress takes a configuration-based approach to running tests, specifying
configuration in yaml files.

Installation
------------

`benchpress` requires `python3`  
`benchpress` supports `python` 3.3 and higher, and is currently tested on
`python 3.3,3.4,3.5` and `3.6`.

pip:  
`pip` is the default Python package management system used to install tools or
dependencies needed by other scripts.
`benchpress`'s dependencies can be installed by running `pip3 install -r requirements.txt`.

Benchmark binaries also need to be installed. Running `./install_benchmarks.sh`
will download and compile `fio` and `schbench` and put the resulting binaries
in `benchmarks/`. In order to be able to run `fio` tests, you must have have
your distribution's development package for `libaio` installed before
compiling. The benchmarks can be installed individually by running
`./install_fio.sh` and `./install_schbench.sh`

Running benchpress
------------------

The `benchpress` cli is simple to use, simply give it the paths to the
benchmarks and jobs definition files, along with an optional list of
benchmark jobs to run (if this is omitted all defined jobs are run).

Examples:  
List available tests:  
`./benchpress_cli.py -b benchmarks.yml -j jobs/jobs.yml list`  
Run all tests defined in `jobs/jobs.yml`:  
`./benchpress_cli.py -b benchmarks.yml -j jobs/jobs.yml run`  
Run just the "fio aio" test:  
`./benchpress_cli.py -b benchmarks.yml -j jobs/jobs.yml run "fio aio"`  

How benchpress works
--------------------

`benchpress` is configured with 'jobs' and 'benchmarks'. A benchmark is a
reference to a binary (that usually can be run with different arguments). A job
is a specific run of that benchmark with a different configuration.  

Benchmark config
----------------

An example benchmark is defined as follows:
```yaml
schbench:
  parser: schbench
  path: ./benchmarks/schbench
  metrics:
    - latency:
        - p50
        - p75
        - p90
        - p95
        - p99
        - p99.5
        - p99.9
```
This defines the `schbench` benchmark to run the binary located at
`./benchmarks/schbench`, using the parser `schbench` and exports metrics
`latency.pXX`

Job config
----------

An example job is defined as follows:
```yaml
- benchmark: schbench
  name: schbench default
  description: defaults for schbench
  args:
    message-threads: 2
    threads: 16
    runtime: 30
    sleeptime: 10000
    cputime: 10000
    pipe: 0
    rps: 0
```
This job runs the binary from the `schbench` benchmark and exports the metrics
from the benchmark definition.

Job arguments:  
The arguments are passed to the benchmark binary and can be either a dictionary
or a list, if `args` is a dictionary, they are converted to the format `--<key>
<value>`, if they are a list, they are used directly as argv for the binary.

Job config overrides:  
A job config can override the metrics configuration for its associated
benchmark. If a job contains a `metrics` key, that is used instead of the
metrics defined in the benchmark.

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
