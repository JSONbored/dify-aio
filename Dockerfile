# syntax=docker/dockerfile:1@sha256:2780b5c3bab67f1f76c781860de469442999ed1a0d7992a5efdf2cffc0e3d769
# checkov:skip=CKV_DOCKER_7: Upstream Dify images are pinned by immutable manifest digests.
# checkov:skip=CKV_DOCKER_8: s6-overlay starts as root to initialize bundled Postgres, Redis, Nginx, Squid, and Dify services.

ARG UPSTREAM_DIFY_VERSION=1.14.0
ARG UPSTREAM_DIFY_API_DIGEST=sha256:2256f6722eef6844007a2f7e28fd348b87ce38a20a229aed655f89d63eeca475
ARG UPSTREAM_DIFY_WEB_DIGEST=sha256:f54f865b9bfb6400d52fe5cae4ca82c8c91a3c5234bb2e9c3a1161fc048ae19c
ARG UPSTREAM_DIFY_SANDBOX_VERSION=0.2.15
ARG UPSTREAM_DIFY_SANDBOX_DIGEST=sha256:750e1111426ef31a9217b81c98cccfb750f17b182af3221102e420afa9f0928e
ARG UPSTREAM_DIFY_PLUGIN_DAEMON_VERSION=0.6.0-local
ARG UPSTREAM_DIFY_PLUGIN_DAEMON_DIGEST=sha256:f200b00544f83ed69ea11d82996819be43415ad33e5c2b37436667df152ef6c8
ARG NODE_RUNTIME_DIGEST=sha256:d415caac2f1f77b98caaf9415c5f807e14bc8d7bdea62561ea2fef4fbd08a73c
ARG S6_OVERLAY_VERSION=3.2.1.0

FROM langgenius/dify-web:${UPSTREAM_DIFY_VERSION}@${UPSTREAM_DIFY_WEB_DIGEST} AS web
FROM langgenius/dify-sandbox:${UPSTREAM_DIFY_SANDBOX_VERSION}@${UPSTREAM_DIFY_SANDBOX_DIGEST} AS sandbox
FROM langgenius/dify-plugin-daemon:${UPSTREAM_DIFY_PLUGIN_DAEMON_VERSION}@${UPSTREAM_DIFY_PLUGIN_DAEMON_DIGEST} AS plugin_daemon
FROM node:22-bookworm-slim@${NODE_RUNTIME_DIGEST} AS node_runtime
FROM langgenius/dify-api:${UPSTREAM_DIFY_VERSION}@${UPSTREAM_DIFY_API_DIGEST}

ARG TARGETARCH
ARG UPSTREAM_DIFY_VERSION
ARG UPSTREAM_DIFY_SANDBOX_VERSION
ARG UPSTREAM_DIFY_PLUGIN_DAEMON_VERSION
ARG S6_OVERLAY_VERSION

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# trunk-ignore(hadolint/DL3002)
USER root

LABEL org.opencontainers.image.title="dify-aio" \
      org.opencontainers.image.description="Unraid-first Dify AIO wrapper bundling Dify API, worker, web, sandbox, plugin daemon, PostgreSQL/pgvector, Redis, Nginx, and SSRF proxy defaults." \
      org.opencontainers.image.source="https://github.com/JSONbored/dify-aio" \
      org.opencontainers.image.vendor="JSONbored" \
      io.jsonbored.wrapper.name="dify-aio" \
      io.jsonbored.wrapper.type="unraid-aio" \
      io.jsonbored.upstream.dify.version="${UPSTREAM_DIFY_VERSION}" \
      io.jsonbored.upstream.dify_sandbox.version="${UPSTREAM_DIFY_SANDBOX_VERSION}" \
      io.jsonbored.upstream.dify_plugin_daemon.version="${UPSTREAM_DIFY_PLUGIN_DAEMON_VERSION}"

# trunk-ignore(hadolint/DL3008)
RUN find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -exec sed -i 's|http://|https://|g' {} + && \
    printf 'Acquire::Retries "5";\nAcquire::http::Timeout "30";\nAcquire::https::Timeout "30";\n' > /etc/apt/apt.conf.d/80-retries && \
    DEBIAN_FRONTEND=noninteractive apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      gettext-base \
      nginx \
      openssl \
      postgresql-common \
      redis-server \
      squid \
      xz-utils && \
    install -d /usr/share/postgresql-common/pgdg && \
    curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc && \
    . /etc/os-release && \
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    DEBIAN_FRONTEND=noninteractive apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      postgresql-15 \
      postgresql-15-pgvector \
      postgresql-client-15 && \
    curl -fsSL -o /tmp/s6-overlay-noarch.tar.xz "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz" && \
    tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz && \
    case "${TARGETARCH}" in \
      amd64) s6_arch="x86_64" ;; \
      arm64) s6_arch="aarch64" ;; \
      *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac && \
    curl -fsSL -o /tmp/s6-overlay-arch.tar.xz "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-${s6_arch}.tar.xz" && \
    tar -C / -Jxpf /tmp/s6-overlay-arch.tar.xz && \
    mkdir -p /appdata /opt/dify-aio /opt/dify-web /opt/dify-plugin-daemon /opt/dify-sandbox /run/postgresql /var/lib/postgresql/data && \
    chown -R postgres:postgres /run/postgresql /var/lib/postgresql && \
    rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf && \
    rm -rf /tmp/* /var/lib/apt/lists/*

COPY --from=web /app /opt/dify-web
COPY --from=node_runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=plugin_daemon /app /opt/dify-plugin-daemon
COPY --from=sandbox /main /opt/dify-sandbox/main
COPY --from=sandbox /conf /opt/dify-sandbox/conf
COPY --from=sandbox /dependencies /opt/dify-sandbox/dependencies
COPY --from=sandbox /opt /opt
COPY rootfs/ /

RUN find /etc/cont-init.d -type f -exec chmod +x {} \; && \
    find /etc/services.d -type f -name run -exec chmod +x {} \; && \
    find /opt/dify-aio/bin -type f -exec chmod +x {} \; && \
    sed -i 's#/app/targets#/opt/dify-web/targets#g' /opt/dify-web/entrypoint.sh && \
    chmod +x /opt/dify-web/entrypoint.sh /opt/dify-plugin-daemon/main /opt/dify-plugin-daemon/commandline /opt/dify-sandbox/main && \
    mkdir -p /app/api/storage && \
    chown -R dify:dify /opt/dify-web /app/api/storage

VOLUME ["/appdata"]

EXPOSE 8080

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV S6_CMD_WAIT_FOR_SERVICES_MAXTIME=900000
ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2

HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=5 \
  CMD curl -fsS http://127.0.0.1:5001/health >/dev/null || exit 1

ENTRYPOINT ["/init"]
