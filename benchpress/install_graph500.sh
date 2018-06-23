#!/bin/bash

GRAPH500_GIT_REPO_URL="https://github.com/graph500/graph500.git"
GRAPH500_GIT_COMMIT_TAG="graph500-2.1.4"

BENCHMARKS_DIR="$(pwd)/benchmarks"
mkdir -p "$BENCHMARKS_DIR"

GRAPH500_INSTALLATION_PREFIX="${BENCHMARKS_DIR}/graph500"
GRAPH500_BINARY_PATH="${GRAPH500_INSTALLATION_PREFIX}/omp-csr"

rm -rf build
mkdir -p build
cd build/

git clone "$GRAPH500_GIT_REPO_URL"
cd graph500/
git checkout -b benchpress tags/"$GRAPH500_GIT_COMMIT_TAG"
cat <<EOF > make.inc
BUILD_OPENMP=Yes
BUILD_MPI=No
CFLAGS=-O2 -std=c99 -lm
EOF


make omp-csr/omp-csr
mkdir -p "${GRAPH500_INSTALLATION_PREFIX}"
mv omp-csr/omp-csr "${GRAPH500_BINARY_PATH}"
cd ../../

rm -rf build/

echo "Graph500 installed into ${GRAPH500_INSTALLATION_PREFIX}"
