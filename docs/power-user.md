# Dify AIO Power User Notes

The default template is intentionally small for first boot: one Web UI port, one AppData path, bundled PostgreSQL/pgvector, bundled Redis, local file storage, sandbox, plugin daemon, Nginx, and SSRF proxy.

Advanced users still get the real Dify operator surface in the XML: public URLs, database/Redis, common vector backends, object storage, mail, sandbox/SSRF, plugin daemon storage, observability, upload limits, Notion, and datasource toggles. Those settings are generated from `docs/upstream/dify.env.example`, with AIO-specific defaults overriding values that would otherwise point at Docker Compose service names that do not exist in a single-container Unraid deployment.

The full upstream environment list is still tracked in `rootfs/opt/dify-aio/upstream-env-vars.txt`, but not every variable is shown in Community Applications. Rare provider-specific or internal Dify tuning variables belong in `/appdata/config/extra.env`.

## External Services

Use external services when you need independent backup, scaling, or operational ownership:

- PostgreSQL: set `DIFY_USE_INTERNAL_POSTGRES=false`, then provide the `DB_*` settings.
- Redis: set `DIFY_USE_INTERNAL_REDIS=false`, then provide the `REDIS_*` settings.
- Vector stores: keep `VECTOR_STORE=pgvector` for the bundled default, or switch to an external provider and fill in that provider's variables.
- Object storage: keep `STORAGE_TYPE=opendal` for local AppData storage, or switch to S3-compatible/object-store settings.

## URLs And Reverse Proxies

Set `DIFY_AIO_PUBLIC_URL` for the common single-domain reverse-proxy case. It seeds console, app, trigger, file, and WebSocket URLs unless you override the individual upstream variables.

If you split domains or use an unusual proxy, set the individual `CONSOLE_*`, `APP_*`, `SERVICE_API_URL`, `TRIGGER_URL`, `FILES_URL`, `NEXT_PUBLIC_SOCKET_URL`, and cookie/CORS variables directly.

## Secrets

Leave secret fields blank unless you need explicit values. The container generates and persists these on first boot:

- `SECRET_KEY`
- `DB_PASSWORD`
- `REDIS_PASSWORD`
- `SANDBOX_API_KEY`
- `PLUGIN_DAEMON_KEY`
- `PLUGIN_DIFY_INNER_API_KEY`

Changing `SECRET_KEY` after setup can invalidate sessions, signed file URLs, and encrypted provider/plugin credentials.

## Extra Environment File

Use `/appdata/config/extra.env` for upstream Dify variables that are supported by Dify but intentionally left out of the Unraid form. The file is sourced during service startup.

Example:

```dotenv
SANDBOX_EXPIRED_RECORDS_CLEAN_TASK_LOCK_TTL=90000
QUEUE_MONITOR_INTERVAL=30
```

Keep secrets in the Unraid template fields when those fields exist. Use `extra.env` for rare or advanced variables, and document local changes because they are outside the curated CA surface.

## Sandbox And SSRF Proxy

The sandbox and SSRF proxy are part of the Dify self-hosted topology. Keep `DIFY_ENABLE_SANDBOX=true` unless you deliberately accept broken code-execution features.

If you need sandbox Python package access through a mirror, set `PIP_MIRROR_URL`. If you need tighter network control, review `SANDBOX_*` and `SSRF_*` together rather than changing one side only.

## Regenerating XML

After refreshing `docs/upstream/dify.env.example`, run:

```sh
python3 scripts/generate_dify_template.py
cd ../aio-fleet && python -m aio_fleet validate --repo dify-aio
pytest tests/template
```

Run `pytest tests/integration -m integration` whenever the Dockerfile, rootfs, service wiring, generated secrets, blank-value normalization, or defaults change.
