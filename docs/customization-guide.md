# Customization Guide

Use this when turning the template into a real app repo.

## First Pass

1. Rename `template-aio.xml` to your final repo slug, for example `myapp-aio.xml`.
2. Replace the placeholder upstream image in [`Dockerfile`](/tmp/unraid-aio-template/Dockerfile).
3. Replace [`assets/app-icon.png`](/tmp/unraid-aio-template/assets/app-icon.png).
4. Update [`README.md`](/tmp/unraid-aio-template/README.md), [`SECURITY.md`](/tmp/unraid-aio-template/SECURITY.md), and [`.github/FUNDING.yml`](/tmp/unraid-aio-template/.github/FUNDING.yml).
5. Replace the starter service command in [`rootfs/etc/services.d/app/run`](/tmp/unraid-aio-template/rootfs/etc/services.d/app/run).
6. Replace the starter pytest integration assertions in [`tests/integration/test_container_runtime.py`](/tmp/unraid-aio-template/tests/integration/test_container_runtime.py) with the real app lifecycle expectations.
7. Configure [`upstream.toml`](/tmp/unraid-aio-template/upstream.toml) and pin the upstream version in the Dockerfile.
8. Keep the XML `<Changes>` block in the date-first fleet format: `### YYYY-MM-DD` followed by short bullet lines only, then let [`scripts/update-template-changes.py`](/tmp/unraid-aio-template/scripts/update-template-changes.py) keep it synced from `CHANGELOG.md`.

## Files You Will Almost Always Touch

- [`Dockerfile`](/tmp/unraid-aio-template/Dockerfile)
- [`template-aio.xml`](/tmp/unraid-aio-template/template-aio.xml)
- [`README.md`](/tmp/unraid-aio-template/README.md)
- [`pyproject.toml`](/tmp/unraid-aio-template/pyproject.toml)
- [`tests/integration/test_container_runtime.py`](/tmp/unraid-aio-template/tests/integration/test_container_runtime.py)
- [`scripts/validate-template.py`](/tmp/unraid-aio-template/scripts/validate-template.py)
- [`scripts/update-template-changes.py`](/tmp/unraid-aio-template/scripts/update-template-changes.py)
- [`rootfs/etc/cont-init.d/01-bootstrap.sh`](/tmp/unraid-aio-template/rootfs/etc/cont-init.d/01-bootstrap.sh)
- [`rootfs/etc/services.d/app/run`](/tmp/unraid-aio-template/rootfs/etc/services.d/app/run)
- [`upstream.toml`](/tmp/unraid-aio-template/upstream.toml)

## Internal PostgreSQL

The template includes an optional PostgreSQL example because some AIO repos genuinely need an embedded database.

If the derived app does not need internal PostgreSQL, remove:

- [`rootfs/etc/cont-init.d/02-init-postgres.sh`](/tmp/unraid-aio-template/rootfs/etc/cont-init.d/02-init-postgres.sh)
- [`rootfs/etc/services.d/postgres/run`](/tmp/unraid-aio-template/rootfs/etc/services.d/postgres/run)

If the derived app does need internal PostgreSQL:

- install the required PostgreSQL packages in [`Dockerfile`](/tmp/unraid-aio-template/Dockerfile)
- replace the example init script with real cluster/bootstrap logic
- update the integration tests to validate persistence or first-boot expectations when relevant

## CI and Publishing

The build workflow publishes from `main` once the required registry and sync secrets are configured.

Before enabling it:

- run `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt`
- run `pytest tests/unit tests/template`
- run `pytest tests/integration -m integration`
- set all required repository variables and secrets
- confirm the XML, icon, and package names match the intended public repo
- confirm the upstream monitor matches the real upstream source and stable channel
- confirm `CHANGELOG.md` and the XML `<Changes>` block describe the same latest release

## Trust Signals To Add Before Public Launch

- one screenshot or meaningful demo visual if the app has a UI
- a real first-run section in the README
- an honest limitations or caveats section if the app has rough edges
- a clear `Support` and `Project` URL in the XML
