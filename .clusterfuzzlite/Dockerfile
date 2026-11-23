FROM gcr.io/oss-fuzz-base/base-builder-python@sha256:21f6fab17ace4dc76e1c56de91ee95d3d03da021df94b41056ba036f6c6f55e9

ENV PATH="/root/.cargo/bin:/rust/bin:${PATH}"

RUN if command -v rustup >/dev/null 2>&1; then \
      rustup toolchain install stable --profile minimal && rustup default stable; \
    else \
      curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal; \
    fi \
    && python3 -m pip install --no-cache-dir "maturin>=1.14,<2"

COPY . $SRC/findfmt
WORKDIR $SRC/findfmt
RUN cargo fetch --locked --manifest-path "$SRC/findfmt/findfmt_rs/Cargo.toml"
COPY .clusterfuzzlite/build.sh $SRC/
