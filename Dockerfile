# syntax=docker/dockerfile:1@sha256:2780b5c3bab67f1f76c781860de469442999ed1a0d7992a5efdf2cffc0e3d769
# checkov:skip=CKV_DOCKER_7: Upstream Dify images are pinned by immutable manifest digests.
# checkov:skip=CKV_DOCKER_8: s6-overlay starts as root to initialize bundled Postgres, Redis, Nginx, Squid, and Dify services.

ARG UPSTREAM_DIFY_VERSION=1.20.0
ARG UPSTREAM_DIFY_API_DIGEST=sha256:9acb839cd797532ee2fd7a357c9bca0c15710ace99ceca3702ea990239d5c8b7
ARG UPSTREAM_DIFY_WEB_DIGEST=sha256:70bfcf68a607a38d65fdc3b84a00386bd76413ffb293e2ab1fe5e6768f6b3efc
ARG UPSTREAM_DIFY_SANDBOX_VERSION=0.2.15
ARG UPSTREAM_DIFY_SANDBOX_DIGEST=sha256:750e1111426ef31a9217b81c98cccfb750f17b182af3221102e420afa9f0928e
ARG UPSTREAM_DIFY_PLUGIN_DAEMON_VERSION=0.6.15-local
ARG UPSTREAM_DIFY_PLUGIN_DAEMON_DIGEST=sha256:14aebd55ff37456dcf4ab8e5a92617eeef767e0e239a13c86083287ee1c1a338
ARG UPSTREAM_DIFY_AGENT_DIGEST=sha256:16bb6ccb40e647436064b1e16d030b668efacdb4c972ed46da6ffa15c2f8318b
ARG NODE_RUNTIME_DIGEST=sha256:dc26ae92c9fb15cf6b1d63e20f0944b2efe0f115b20e00be48fb23fceb061c54

FROM jsonbored/aio-base:s6-3.2.1.0@sha256:07db479a01a95ba28480b4605f5d1cc8bedb574b77cf167ee46e29b9558fee90 AS aio-base

FROM langgenius/dify-web:${UPSTREAM_DIFY_VERSION}@${UPSTREAM_DIFY_WEB_DIGEST} AS web
FROM langgenius/dify-sandbox:${UPSTREAM_DIFY_SANDBOX_VERSION}@${UPSTREAM_DIFY_SANDBOX_DIGEST} AS sandbox
FROM langgenius/dify-plugin-daemon:${UPSTREAM_DIFY_PLUGIN_DAEMON_VERSION}@${UPSTREAM_DIFY_PLUGIN_DAEMON_DIGEST} AS plugin_daemon
FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df AS plugin_python
FROM langgenius/dify-agent-backend:${UPSTREAM_DIFY_VERSION}@${UPSTREAM_DIFY_AGENT_DIGEST} AS agent_backend
FROM node:24.22.3-bookworm-slim@${NODE_RUNTIME_DIGEST} AS node_runtime
FROM langgenius/dify-api:${UPSTREAM_DIFY_VERSION}@${UPSTREAM_DIFY_API_DIGEST}

ARG UPSTREAM_DIFY_VERSION
ARG UPSTREAM_DIFY_SANDBOX_VERSION
ARG UPSTREAM_DIFY_PLUGIN_DAEMON_VERSION

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

# Shared, pinned s6-overlay from the fleet aio-base overlay.
COPY --from=aio-base /aio-overlay/ /

# trunk-ignore(hadolint/DL3008)
RUN aio-harden pre && \
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
    mkdir -p /appdata /opt/dify-aio /opt/dify-web /opt/dify-plugin-daemon /opt/dify-sandbox /run/postgresql /var/lib/postgresql/data && \
    chown -R postgres:postgres /run/postgresql /var/lib/postgresql && \
    rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf && \
    rm -rf /tmp/* /var/lib/apt/lists/*

COPY --from=web /app /opt/dify-web
COPY --from=node_runtime /usr/local/bin/node /usr/local/bin/node
# Dify 1.20 uses Python 3.13 for its API, while the local plugin SDK uses 3.12.
# Keep both installed so existing plugin manifests resolve the same interpreter.
COPY --from=plugin_python /usr/local/bin/python3.12 /usr/local/bin/python3.12
COPY --from=plugin_python /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=plugin_python /usr/local/lib/libpython3.12.so.1.0 /usr/local/lib/libpython3.12.so.1.0
COPY --from=agent_backend /app/api/.venv /opt/dify-agent/venv
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
