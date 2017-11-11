#!/bin/bash
set -e
set -x

# System dependencies Pre-Requisites
# APT_PACKAGES='libjemalloc-dev libnuma-dev libdb++-dev libmysqld-dev libaio-dev libssl-dev'
# sudo apt install "${APT_PACKAGES}"

# YUM_PACKAGES='jemalloc-devel numactl-devel libdb-cxx-devel mysql-devel libaio-devel openssl-devel'
# sudo yum install "${YUM_PACKAGES}"

# Downloads and compiles Silo's dbtest benchmark, putting the binary into ./benchmarks/
SILO_GIT_REPO="https://github.com/stephentu/silo.git"
SILO_GIT_TAG="cc11ca1ea949ef266ee12a9b1c310392519d9e3b"

# benchmark binaries that we install here live in benchmarks/
BENCHMARKS_DIR="$(pwd)/benchmarks"
mkdir -p benchmarks

# Use seperate build directory, third party dependency is dynamically linked, cannot delete.
rm -rf silo_build
mkdir -p silo_build
cd silo_build


git clone https://github.com/stephentu/silo.git
cd silo

# Disables Warning maybe-uninitialized which causes compilation error on
# the masstree. Checks which flag gcc supports.
MAYBE_UNINIT="$(echo | gcc -Wmaybe-uninitialized -E - >/dev/null 2>&1 && \
                echo '-Wno-error=maybe-uninitialized')"
cxx="g++ -std=gnu++0x ${MAYBE_UNINIT}"

# make dbtest
CXX="${cxx}" MODE=perf DEBUG=0 CHECK_INVARIANTS=0 USE_MALLOC_MODE=1 make dbtest

# move the binary to the install dir
mv out-perf.masstree/benchmarks/dbtest "${BENCHMARKS_DIR}"
cd ../../

echo "silo dbtest installed into ./benchmarks/dbtest"
