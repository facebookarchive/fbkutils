#!/bin/bash
# Downloads and compiles schbench and fio, putting the binaries into ./benchmarks/

# benchmark binaries that we install here live in benchmarks/
BENCHMARKS_DIR="$(pwd)/benchmarks"
mkdir -p benchmarks

./install_schbench.sh
./install_fio.sh
./install_silo.sh

echo "Benchmarks installed into ./benchmarks/"
