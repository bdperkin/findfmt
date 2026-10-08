#!/bin/bash -eu

# Install findfmt runtime dependencies pinned by hash
python3 -m pip install --no-deps --require-hashes -r "$SRC/findfmt/.clusterfuzzlite/requirements.txt"

# Install findfmt source package into site-packages
SITE_PACKAGES=$(python3 -c "import site; print(site.getsitepackages()[0])")
cp -r "$SRC/findfmt/src/findfmt" "$SITE_PACKAGES/"

# Compile Atheris fuzz targets into $OUT
compile_python_fuzzer tests/fuzz/fuzz_classifier.py
compile_python_fuzzer tests/fuzz/fuzz_traversal.py
