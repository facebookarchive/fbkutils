Benchpress
==========

Benchpress (BENCHmark Pluggable haRnESS) is a framework for running benchmark
suites.  
Benchpress takes a configuration-based approach to running tests, specifying
configuration in yaml files.


Running benchpress
------------------

The `benchpress` cli is simple to use, simply give it the paths to the
benchmarks and jobs definition files, along with an optional list of
benchmark jobs to run (if this is omitted all defined jobs are run).

How benchpress works
--------------------

Benchmarks can be defined using yaml (see benchmarks.yml). A benchmark has a
simple definition: the path to a binary, a parser class, and the metrics that
the parser exports.

Benchmark definitions don't do anything by themselves, `benchpress` also needs a
configuration for that benchmark. These are also defined using yaml (see
job\_configs.yml). A job is defined to point to a benchmark defined in the
benchmarks file. Jobs also have a short name and longer description used to
identify the test to the `benchpress` user. Lastly, a job has an array of
arguments, these are passed to the program defined in the benchmark definition
to be able to change the behavior of the benchmark. Job definitions can
optionally specify a list of metrics in the same format as a benchmark
definition that will override the default metrics for the benchmark.

Adding a benchmark
------------------

Adding a benchmark to `benchpress` is simple - just write the yaml definitions
of the benchmark program and the associated job(s). The usefulness of
`benchpress` is enabled by your parser implementation. `benchpress` loads a
parser module according to the parser name in the benchmark definition.

Once you've defined your metrics in the benchmark definition, you can write the
parser that will produce those metrics for use by `benchpress`. A parser is a
subclass of `Parser`, and must implement the `parse` method.  `parse` is called
by `benchpress` with the output (stdout + stderr) of the benchmark and is where
the parser should process that output, and return a dictionary of all the
metrics matching the format of the metrics defined in the benchmark.
