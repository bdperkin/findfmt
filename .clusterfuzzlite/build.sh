#!/bin/bash -eu

# Install findfmt and its runtime dependencies
python3 -m pip install .

# Compile Atheris fuzz targets into $OUT
compile_python_fuzzer tests/fuzz/fuzz_classifier.py
compile_python_fuzzer tests/fuzz/fuzz_traversal.py
