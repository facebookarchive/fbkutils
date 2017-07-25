#!/bin/bash
# Downloads and compiles schbench, putting the binary into ./benchmarks/

# benchmark binaries that we install here live in benchmarks/
BENCHMARKS_DIR="$(pwd)/benchmarks"
mkdir -p benchmarks

rm -rf build
mkdir -p build
pushd build

# make fio

# this is a kinda hacky way to ensure that libaio is installed
echo "#include <libaio.h>" | gcc -c -x c -o /dev/null - 2> /dev/null
if [ $? -ne 0 ]; then
  echo "libaio development headers are not installed, please install them and rerun this script"
  exit 1
fi

git clone http://git.kernel.dk/fio.git
pushd fio
make
# move the binary to the install dir
mv fio $BENCHMARKS_DIR
popd

# destroy the build directory
popd
rm -rf build

echo "fio installed into ./benchmarks/fio"
