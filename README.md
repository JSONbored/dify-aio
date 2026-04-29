# dify-aio

Unraid-first AIO wrapper for [Dify](https://github.com/langgenius/dify), an open-source platform for building agentic workflows, chat apps, knowledge-base apps, and LLM-backed automations.

This image intentionally keeps Dify installable as one Unraid template while still exposing the important escape hatches. It bundles the Dify API, background workers, worker beat, web UI, plugin daemon, code sandbox, SSRF proxy, Nginx, PostgreSQL 15 with pgvector, and Redis.

## Status

This repository is pre-release, but the source template and local container boot path are now covered by pytest-backed validation. Treat Community Applications submission as a separate catalog/support-thread step.

## What Is Included

- Dify API and worker services from `langgenius/dify-api`
- Dify web UI from `langgenius/dify-web`
- Dify sandbox from `langgenius/dify-sandbox`
- Dify plugin daemon from `langgenius/dify-plugin-daemon`
- bundled PostgreSQL 15 with pgvector by default
- bundled Redis by default
- Nginx gateway on port `8080`
- SSRF proxy for sandboxed code execution
- first-boot secret generation under `/appdata/config/generated.env`

## First Run

1. Install the Unraid template with the default settings.
2. Open `http://<unraid-ip>:8080/install`.
3. Create the initial admin account.
4. Add model-provider keys, SMTP, storage, and datasource credentials inside Dify as needed.

If `INIT_PASSWORD` is set in the template, Dify uses it as the initial admin password. Dify limits that value to 30 characters.

## Persistent Data

The template mounts one AppData path:

- `/appdata`

That path stores generated secrets, PostgreSQL data, Redis data, uploads, plugin daemon state, sandbox configuration, and local file storage.

## Common Configuration

The default install uses bundled PostgreSQL, pgvector, and Redis.

Power-user overrides:

- set `DIFY_AIO_PUBLIC_URL` when Dify is behind a reverse proxy
- use the advanced Dify settings for the real operator surface: URLs, DB/Redis, vector stores, storage backends, mail, sandbox, plugins, observability, uploads, and common integrations
- put rare upstream-only variables in `/appdata/config/extra.env` instead of expanding the Unraid form with every Dify knob
- set `DIFY_USE_INTERNAL_POSTGRES=false` and provide `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, and `DB_DATABASE` for external PostgreSQL
- set `DIFY_USE_INTERNAL_REDIS=false` and provide `REDIS_HOST`, `REDIS_PORT`, and `REDIS_PASSWORD` for external Redis
- set `VECTOR_STORE` to `qdrant`, `weaviate`, `milvus`, `chroma`, `opensearch`, `elasticsearch`, or `upstash` only when that external service is already available
- set `STORAGE_TYPE=s3` plus the S3 variables for external object storage
- keep `DIFY_ENABLE_SANDBOX=true` unless you deliberately want code execution features disabled

## Operational Caveats

Dify is not a tiny single-process app. The AIO wrapper trades operational simplicity for a heavier container with multiple supervised services inside it. For a serious deployment, use a reverse proxy with TLS, give the container enough memory, back up `/appdata`, and consider external PostgreSQL, Redis, and object storage when uptime or recovery matters.

The sandbox and SSRF proxy are included because they are part of the official self-hosted Dify topology. They reduce risk, but they do not make arbitrary code execution risk-free.

## Validation

Local checks:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python3 scripts/validate-template.py
pytest tests/unit tests/template
pytest tests/integration -m integration
```

The integration test builds a Linux amd64 image and boots the full container stack, so it is intentionally more expensive than the unit and XML checks.

Extended provider checks:

```sh
pytest tests/integration -m extended_integration
```

The extended suite is meant for deeper release or manual validation. It starts provider sidecars for external PostgreSQL plus Redis, Qdrant, MinIO-compatible S3 storage, and SMTP capture, then boots the AIO container against those settings. It also verifies that common optional provider settings for plugin object storage, additional vector backends, Notion, Unstructured, Sentry, and OpenTelemetry can be supplied through `/appdata/config/extra.env`. Storage and mail sidecars prove boot-time configuration and network reachability; SaaS-backed integrations still require app-level credentials and workflows for true end-to-end provider validation.

The Unraid XML template is generated from `docs/upstream/dify.env.example` plus AIO-specific defaults. The generated XML is curated for Community Applications usability, while `rootfs/opt/dify-aio/upstream-env-vars.txt` still tracks the full upstream variable list for blank-value normalization and drift checks. When Dify updates its upstream environment surface, refresh the fixture, run `python3 scripts/generate_dify_template.py`, and then run validation.

## Upstream

- Project: <https://github.com/langgenius/dify>
- Self-hosted install docs: <https://docs.dify.ai/en/self-host/quick-start/docker-compose>
- Release notes: <https://github.com/langgenius/dify/releases>
