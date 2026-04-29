# Upstream Tracking

Every derived AIO repo should declare the upstream app it wraps and how updates should be handled.

## Why This Exists

Without upstream monitoring, each AIO repo becomes a manual memory problem. The goal is simple:

- detect new stable upstream versions
- open a controlled PR or issue
- let the normal repo CI validate the update before it ships

## Files

- [`upstream.toml`](../upstream.toml)
- [`scripts/check-upstream.py`](../scripts/check-upstream.py)
- [`.github/workflows/check-upstream.yml`](../.github/workflows/check-upstream.yml)

## Recommended Default

Use stable-only monitoring with `strategy = "notify"` until the update workflow can refresh all Dify companion image digests together.

That means the repo:

- checks upstream on a schedule
- opens an issue when a new stable version appears
- leaves the digest refresh and validation pass explicit

## Supported Upstream Types

- `github-tag`
- `github-release`
- `ghcr-container-tag`

## Optional Digest Pinning

When the wrapped upstream publishes immutable image manifests, you can track both the human version and the exact image digest. Dify uses multiple companion images, so digest updates should be handled as one explicit release task instead of allowing the single-image monitor to update only one digest.

Example:

```toml
[upstream]
name = "Dify"
type = "github-release"
repo = "langgenius/dify"
version_source = "dockerfile-arg"
version_key = "UPSTREAM_DIFY_VERSION"
strategy = "notify"
stable_only = true

[notifications]
release_notes_url = "https://github.com/langgenius/dify/releases"
```

## Example

```toml
[upstream]
name = "Dify"
type = "github-release"
repo = "langgenius/dify"
version_source = "dockerfile-arg"
version_key = "UPSTREAM_DIFY_VERSION"
strategy = "notify"
stable_only = true

[notifications]
release_notes_url = "https://github.com/langgenius/dify/releases"
```

## Version Pinning Pattern

Pin the wrapped upstream version explicitly in the Dockerfile:

```dockerfile
ARG UPSTREAM_DIFY_VERSION=1.14.0
ARG UPSTREAM_DIFY_API_DIGEST=sha256:...
FROM langgenius/dify-api:${UPSTREAM_DIFY_VERSION}@${UPSTREAM_DIFY_API_DIGEST}
```

This gives the upstream monitor a concrete value to compare and update.

## Stable First

The default template policy is stable only. Do not expose prerelease channels until the derived repo has:

- strong integration tests
- confidence in upgrade safety
- a clear reason to offer beta or RC tags publicly
