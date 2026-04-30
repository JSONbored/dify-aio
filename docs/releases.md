# Releases

`dify-aio` uses upstream-version-plus-AIO-revision releases such as `1.14.0-aio.1`.

## Version Format

- first wrapper release for upstream `1.14.0`: `1.14.0-aio.1`
- second wrapper-only release on the same upstream: `1.14.0-aio.2`
- first wrapper release after upgrading upstream again: `vX.Y.Z-aio.1`

## Published Image Tags

Every `main` build publishes:

- `latest`
- the exact pinned upstream Dify version
- `sha-<commit>`

Release commits also publish the exact immutable release package tag, for example `1.14.0-aio.1`. Ordinary `main` pushes do not overwrite that release tag.

## What A Dify AIO Release Means

A release means the wrapper has been validated against a specific upstream Dify version and its companion images:

- `langgenius/dify-api`
- `langgenius/dify-web`
- `langgenius/dify-sandbox`
- `langgenius/dify-plugin-daemon`

## Release Flow

1. Trigger **Prepare Release / Dify AIO** from `main`.
2. The workflow computes the next `upstream-aio.N` version, updates `CHANGELOG.md`, syncs the XML `<Changes>` block, and opens a release PR.
3. Review and merge that PR into `main`.
4. Wait for the `CI / Dify AIO` run on the release target commit to finish green. That same `main` push also publishes the updated package tags automatically.
5. Trigger **Publish Release / Dify AIO** from `main`.
6. The workflow verifies CI on the exact release target commit, creates the Git tag if needed, and publishes the GitHub Release.

## Deep Provider Validation

The normal release path requires the standard integration suite. Run the manual extended integration suite before Community Applications submission, before large Dify upstream jumps, or when changing database, Redis, vector, storage, mail, plugin, or observability configuration behavior.
