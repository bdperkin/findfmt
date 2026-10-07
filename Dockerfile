# Multi-stage slim container build for findfmt using uv
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim@sha256:531f855bda2c73cd6ef67d56b733b357cea384185b3022bd09f05e002cd144ca AS builder

WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Install into a standalone system environment
RUN uv pip install --no-cache --system .

# Runtime Stage
FROM python:3.13-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641 AS runtime

LABEL org.opencontainers.image.title="findfmt" \
      org.opencontainers.image.description="A .gitignore-aware file discovery and classification suite" \
      org.opencontainers.image.url="https://github.com/bdperkin/findfmt" \
      org.opencontainers.image.source="https://github.com/bdperkin/findfmt" \
      org.opencontainers.image.licenses="MIT"

# Copy installed site-packages and binaries from builder
COPY --from=builder /usr/local /usr/local

# Security: Non-privileged user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /workspace && \
    chown -R appuser:appuser /workspace

USER appuser
WORKDIR /workspace

ENTRYPOINT ["findfmt"]
CMD ["--help"]
