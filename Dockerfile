# Multi-stage slim container build for findfmt using uv
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim@sha256:7cf77f594be8042dab6daa9fe326f90962252268b4f120a7f5dccce4d947e6c1 AS builder

WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
COPY tools/ ./tools/

# Install into a standalone system environment
RUN uv pip install --no-cache --system .

# Runtime Stage
FROM python:3.14-slim-bookworm@sha256:945c2676dc2b18e0c1f16879244122c57c0ffede60006bf3df159c507a31bcae AS runtime

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
