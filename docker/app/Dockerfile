ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION:-3.13}-slim AS build

ARG UV_VERSION=0.10.0

ENV PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir "uv==${UV_VERSION}"

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

FROM python:${PYTHON_VERSION:-3.13}-slim AS runtime

WORKDIR /app

# Minimal runtime OS deps for healthchecks/troubleshooting + WeasyPrint
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl jq \
       libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
       libgdk-pixbuf-2.0-0 libffi8 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create an unprivileged user
RUN useradd --create-home --home-dir /home/app --shell /usr/sbin/nologin --uid 10001 app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Copy the venv and app code
COPY --from=build /app/.venv /app/.venv
COPY ./src ./

RUN chown -R app:app /app

USER app
