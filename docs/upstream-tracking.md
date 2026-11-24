# Upstream Tracking

Dify upstream tracking is owned by `aio-fleet`. This repo keeps the Dify Dockerfile pins and generated template inputs; `aio-fleet/fleet.yml` and `.aio-fleet.yml` carry the shared upstream/release policy.

Dify uses multiple companion images, so upstream bumps stay explicit and reviewed: API, web, sandbox, plugin daemon, and digest pins should move together.

Run `python3 scripts/refresh_upstream_inventory.py` before `python3 scripts/generate_dify_template.py` to refresh the curated Unraid controls from the pinned release’s modular service environment files.

## Validation

After changing upstream pins or generated env fixtures, run from `aio-fleet`:

```sh
python -m aio_fleet validate --repo dify-aio
python -m aio_fleet release status --repo dify-aio
```

Keep `strategy: notify` semantics in `aio-fleet` until companion-image digest refreshes are automated as one reviewed change.

Dify 1.20 no longer publishes `CODE_GENERATION_MAX_TOKENS` or `PROMPT_GENERATION_MAX_TOKENS` as application settings. They appeared in the older monolithic sample and remain in an upstream test fixture. Existing installations can retain their explicit settings through the upgrade.
