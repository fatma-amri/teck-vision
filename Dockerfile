FROM python:3.11-slim-bookworm AS build

# Teck-Vision — Plateforme CTF DevSecOps
WORKDIR /opt/teck-vision

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libssl-dev \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

COPY . /opt/teck-vision

RUN pip install --no-cache-dir -r requirements.txt \
    && for d in CTFd/plugins/*; do \
        if [ -f "$d/requirements.txt" ]; then \
            pip install --no-cache-dir -r "$d/requirements.txt";\
        fi; \
    done;


FROM python:3.11-slim-bookworm AS release
WORKDIR /opt/teck-vision

# Metadata labels for Kubernetes and DevSecOps
LABEL maintainer="Teck-Vision Team <noreply@teck-vision.tn>"
LABEL org.opencontainers.image.title="Teck-Vision CTF Platform"
LABEL org.opencontainers.image.description="Teck-Vision - Plateforme CTF pour projet DevSecOps"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.vendor="Teck-Vision Team"
LABEL project="devsecops-teck-vision"
LABEL team="Fatma Amri, Koussay Aydi, Mariem Baraket, Belgacem Balti, Omar Allagui"

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libffi8 \
        libssl3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=1001:1001 . /opt/teck-vision

RUN useradd \
    --no-log-init \
    --shell /bin/bash \
    -u 1001 \
    teck-vision \
    && mkdir -p /var/log/teck-vision /var/uploads \
    && chown -R 1001:1001 /var/log/teck-vision /var/uploads /opt/teck-vision \
    && chmod +x /opt/teck-vision/docker-entrypoint.sh

COPY --chown=1001:1001 --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Health check for Kubernetes liveness probe
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/healthcheck', timeout=2)" || exit 1

USER 1001
EXPOSE 8000
ENTRYPOINT ["/opt/teck-vision/docker-entrypoint.sh"]
