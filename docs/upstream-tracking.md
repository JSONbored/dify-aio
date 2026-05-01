# Upstream Tracking

Dify upstream tracking is owned by `aio-fleet`. This repo keeps the Dify Dockerfile pins and generated template inputs; `aio-fleet/fleet.yml` and `.aio-fleet.yml` carry the shared upstream/release policy.

Dify uses multiple companion images, so upstream bumps stay explicit and reviewed: API, web, sandbox, plugin daemon, and digest pins should move together.

## Validation

After changing upstream pins or generated env fixtures, run from `aio-fleet`:

```sh
python -m aio_fleet validate --repo dify-aio
python -m aio_fleet release status --repo dify-aio
```

Keep `strategy: notify` semantics in `aio-fleet` until companion-image digest refreshes are automated as one reviewed change.
