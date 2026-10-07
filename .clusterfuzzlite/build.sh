#!/bin/bash -eu

# Install runtime dependencies pinned by cryptographic hash
python3 -m pip install --no-cache-dir --require-hashes -r .clusterfuzzlite/requirements.txt

# Install findfmt into python site-packages
SITE_PKG=$(python3 -c "import site; print(site.getsitepackages()[0])")
cp -r src/findfmt "$SITE_PKG/"


# Compile Atheris fuzz targets into $OUT
compile_python_fuzzer tests/fuzz/fuzz_classifier.py
compile_python_fuzzer tests/fuzz/fuzz_traversal.py
