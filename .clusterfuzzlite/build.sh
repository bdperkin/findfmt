#!/bin/bash -eu

# Install findfmt runtime dependencies pinned by hash
python3 -m pip install --no-deps --require-hashes -r "$SRC/findfmt/.clusterfuzzlite/requirements.txt"

# Build and install findfmt with native findfmt._rust_ext PyO3 extension offline (#585).
# Unset C/C++/Rust nightly sanitizer flags from OSS-Fuzz during the stable Rust abi3 cdylib build
# before compile_python_fuzzer configures ASan preloading for the Atheris binaries.
env -u CFLAGS -u CXXFLAGS -u LDFLAGS -u RUSTFLAGS -u CARGO_ENCODED_RUSTFLAGS \
  maturin build --manifest-path "$SRC/findfmt/findfmt_rs/Cargo.toml" \
  --locked --offline --compatibility off --out /tmp/findfmt-wheels
python3 -m pip install --no-deps --force-reinstall /tmp/findfmt-wheels/findfmt-*.whl
python3 -c "import findfmt._rust_ext as ext; assert ext.backend_name() == 'rust'"

# Compile Atheris fuzz targets into $OUT (bundling findfmt._rust_ext)
compile_python_fuzzer tests/fuzz/fuzz_classifier.py --hidden-import=findfmt._rust_ext
compile_python_fuzzer tests/fuzz/fuzz_traversal.py --hidden-import=findfmt._rust_ext
