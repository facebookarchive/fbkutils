#!/bin/bash
# Downloads and compiles schbench, putting the binary into ./benchmarks/

# benchmark binaries that we install here live in benchmarks/
BENCHMARKS_DIR="$(pwd)/benchmarks"
mkdir -p benchmarks

rm -rf build
mkdir -p build
pushd build

# make schbench
git clone https://kernel.googlesource.com/pub/scm/linux/kernel/git/mason/schbench
pushd schbench
make
# move the binary to the install dir
mv schbench $BENCHMARKS_DIR
popd

# destroy the build directory
popd
rm -rf build

echo "shcbench installed into ./benchmarks/schbench"
