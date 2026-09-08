# Build context is the REPOSITORY ROOT, not this directory, because the app
# depends on a workspace sibling:
#   docker build -f apps/api/Dockerfile -t routing-api .
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Manifests first, so the dependency layer survives source edits. The workspace
# members' pyproject files must be present for `uv sync` to resolve the graph.
COPY pyproject.toml uv.lock ./
COPY packages/car-routing/pyproject.toml packages/car-routing/
COPY apps/api/pyproject.toml apps/api/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace

# Then the sources, and install the workspace members themselves.
COPY packages/car-routing/src packages/car-routing/src
COPY apps/api/src apps/api/src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:3.12-slim-bookworm AS runtime

# curl is here only for the container healthcheck below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "routing_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
