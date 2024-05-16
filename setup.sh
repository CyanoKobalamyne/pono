#!/bin/sh
set -o nounset
set -o errexit
set -o pipefail

# First argument is the install prefix
prefix=$1

# Download MathSAT
mkdir -p deps
pushd deps > /dev/null
if [ ! -d "mathsat" ]; then
    wget https://mathsat.fbk.eu/release/mathsat-5.6.10-linux-x86_64.tar.gz
    tar -xzf mathsat-5.6.10-linux-x86_64.tar.gz
    mv mathsat-5.6.10-linux-x86_64 mathsat
    rm -f mathsat-5.6.10-linux-x86_64.tar.gz
else
    echo "deps/mathsat already present, skipping download"
fi
popd > /dev/null

# Install dependencies
./contrib/setup-smt-switch.sh --with-msat
./contrib/setup-btor2tools.sh

# Configure
./configure.sh --prefix=$prefix --with-msat --static-lib

# Build
make -C build -j install
