FROM rust:1.100-slim-bookworm@sha256:7c7d4eb4d05b7781187a327809466cfddf29753f6defdc3d19a0e291951b7a37 AS rust-toolchain
FROM gcr.io/oss-fuzz-base/base-builder-python@sha256:21f6fab17ace4dc76e1c56de91ee95d3d03da021df94b41056ba036f6c6f55e9

COPY --from=rust-toolchain /usr/local/cargo /usr/local/cargo
COPY --from=rust-toolchain /usr/local/rustup /usr/local/rustup
ENV RUSTUP_HOME="/usr/local/rustup" \
    CARGO_HOME="/usr/local/cargo" \
    PATH="/usr/local/cargo/bin:${PATH}"

COPY .clusterfuzzlite/build-requirements.txt /tmp/build-requirements.txt
RUN python3 -m pip install --no-cache-dir --no-deps --require-hashes -r /tmp/build-requirements.txt \
    && rm -f /tmp/build-requirements.txt

COPY . $SRC/findfmt
WORKDIR $SRC/findfmt
RUN cargo fetch --locked --manifest-path "$SRC/findfmt/findfmt_rs/Cargo.toml"
COPY .clusterfuzzlite/build.sh $SRC/
