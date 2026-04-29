# syntax=docker/dockerfile:1@sha256:2780b5c3bab67f1f76c781860de469442999ed1a0d7992a5efdf2cffc0e3d769
# checkov:skip=CKV_DOCKER_3: s6-overlay requires root init so cont-init scripts can prepare state before services drop privileges
# checkov:skip=CKV_DOCKER_8: s6-overlay entrypoint must start as root so init scripts can prepare filesystem state before dropping privileges

# Replace this starter base with the real upstream image once the derived repo is wired.
FROM python:3.14-slim-bookworm@sha256:2e256d0381371566ed96980584957ed31297f437569b79b0e5f7e17f2720e53a

ARG S6_OVERLAY_VERSION=3.2.1.0
ARG TARGETARCH

# hadolint ignore=DL3002
USER root
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates="$(apt-cache madison ca-certificates | awk 'NR==1 {print $3}')" \
    curl="$(apt-cache madison curl | awk 'NR==1 {print $3}')" \
    openssl="$(apt-cache madison openssl | awk 'NR==1 {print $3}')" \
    xz-utils="$(apt-cache madison xz-utils | awk 'NR==1 {print $3}')" && \
    curl -L -o /tmp/s6-overlay-noarch.tar.xz "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz" && \
    tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz && \
    case "${TARGETARCH}" in \
      amd64) s6_arch="x86_64" ;; \
      arm64) s6_arch="aarch64" ;; \
      *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac && \
    curl -L -o /tmp/s6-overlay-arch.tar.xz "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-${s6_arch}.tar.xz" && \
    tar -C / -Jxpf /tmp/s6-overlay-arch.tar.xz && \
    groupadd --system appuser && \
    useradd --system --gid appuser --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser && \
    mkdir -p /config /data /run/service-app && \
    chown -R appuser:appuser /run/service-app && \
    rm -rf /tmp/* /var/lib/apt/lists/*

COPY rootfs/ /

RUN find /etc/cont-init.d -type f -exec chmod +x {} \; && \
    find /etc/services.d -type f -name run -exec chmod +x {} \; && \
    find /usr/local/bin -type f -name '*.py' -exec chmod +x {} \;

VOLUME ["/config", "/data"]

EXPOSE 8080

ENV S6_CMD_WAIT_FOR_SERVICES_MAXTIME=300000
ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -fsS http://localhost:8080/health >/dev/null || exit 1

ENTRYPOINT ["/init"]
