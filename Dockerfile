# Multi-stage slim container build for findfmt using uv.
#
# The image installs the wheel from dist/ (the release workflow's dist artifact), so it carries the
# same version as the PyPI release. Build one first: `uv build --wheel && docker build .` (#328).
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim@sha256:7cf77f594be8042dab6daa9fe326f90962252268b4f120a7f5dccce4d947e6c1 AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/findfmt

WORKDIR /src

# Runtime dependencies at the exact versions pinned in uv.lock (no dev groups, no project).
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --python /usr/local/bin/python3

# The project itself, from the built wheel; its dependencies are already locked in place.
COPY dist/ /tmp/dist/
RUN set -eu; \
    set -- /tmp/dist/findfmt-*.whl; \
    if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then \
        echo "expected exactly one findfmt wheel in dist/; run 'uv build --wheel' first" >&2; \
        exit 1; \
    fi; \
    uv pip install --python /opt/findfmt --no-deps "$1"; \
    uv pip check --python /opt/findfmt

# Runtime Stage
FROM python:3.14-slim-bookworm@sha256:945c2676dc2b18e0c1f16879244122c57c0ffede60006bf3df159c507a31bcae AS runtime

LABEL org.opencontainers.image.title="findfmt" \
      org.opencontainers.image.description="A .gitignore-aware file discovery and classification suite" \
      org.opencontainers.image.url="https://github.com/bdperkin/findfmt" \
      org.opencontainers.image.source="https://github.com/bdperkin/findfmt" \
      org.opencontainers.image.licenses="MIT"

# Only the virtual environment: no uv, no build tooling. Both stages share /usr/local/bin/python3.
COPY --from=builder /opt/findfmt /opt/findfmt
ENV PATH="/opt/findfmt/bin:${PATH}"

# Security: Non-privileged user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /workspace && \
    chown -R appuser:appuser /workspace

USER appuser
WORKDIR /workspace

ENTRYPOINT ["findfmt"]
CMD ["--help"]
