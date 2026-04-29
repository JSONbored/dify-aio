# Dify AIO Customization Guide

Use this when changing the wrapper after the initial scaffold.

## Runtime Surface

The AIO image supervises several Dify services inside one container:

- API
- worker
- worker beat
- web
- plugin daemon
- sandbox
- SSRF proxy
- Nginx
- PostgreSQL with pgvector
- Redis

Keep changes scoped to the service that needs them. If an upstream Dify release changes the official Compose topology, compare this repo against the new `docker/docker-compose.yaml` and `.env.example` before bumping image tags.

## Defaults

Beginner defaults should keep a first install working with only one AppData mount and one Web UI port:

- `/appdata`
- `8080/tcp`
- bundled PostgreSQL
- bundled Redis
- `VECTOR_STORE=pgvector`
- local OpenDAL filesystem storage

Advanced settings should remain optional unless Dify itself makes them required.

Do not dump every upstream Dify environment variable into `dify-aio.xml`. The XML should expose the real Unraid operator surface and common third-party integrations. Keep the full upstream list in `rootfs/opt/dify-aio/upstream-env-vars.txt` and support rare variables through `/appdata/config/extra.env`.

## Files To Check After Upstream Updates

- [`Dockerfile`](../Dockerfile)
- [`docs/upstream/dify.env.example`](upstream/dify.env.example)
- [`dify-aio.xml`](../dify-aio.xml)
- [`scripts/generate_dify_template.py`](../scripts/generate_dify_template.py)
- [`rootfs/opt/dify-aio/lib/env.sh`](../rootfs/opt/dify-aio/lib/env.sh)
- [`rootfs/etc/services.d`](../rootfs/etc/services.d)
- [`tests/integration/test_container_runtime.py`](../tests/integration/test_container_runtime.py)
- [`upstream.toml`](../upstream.toml)

## Validation Order

1. `python3 scripts/generate_dify_template.py --check`
2. `python3 scripts/validate-template.py`
3. `pytest tests/unit tests/template`
4. `pytest tests/integration -m integration`
5. install from the generated XML in a clean Unraid environment
6. verify `http://<unraid-ip>:8080/install`
7. verify restart persistence for `/appdata/config/generated.env`

## Current Known Follow-Up

The upstream monitor is intentionally `strategy = "notify"` because Dify uses multiple pinned upstream image digests. Do not switch it to automatic PR updates until the workflow can refresh all companion image digests in the same change.
