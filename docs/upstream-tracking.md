# Upstream Tracking

Every derived AIO repo should declare the upstream app it wraps and how updates should be handled.

## Why This Exists

Without upstream monitoring, each AIO repo becomes a manual memory problem. The goal is simple:

- detect new stable upstream versions
- open a controlled PR or issue
- let the normal repo CI validate the update before it ships

## Files

- [`upstream.toml`](/tmp/unraid-aio-template/upstream.toml)
- [`scripts/check-upstream.py`](/tmp/unraid-aio-template/scripts/check-upstream.py)
- [`.github/workflows/check-upstream.yml`](/tmp/unraid-aio-template/.github/workflows/check-upstream.yml)

## Recommended Default

Use stable-only monitoring with `strategy = "pr"`.

That means the repo:

- checks upstream on a schedule
- opens a PR when a new stable version appears
- runs the normal validation and pytest flow
- leaves the final merge decision to you

## Supported Upstream Types

- `github-tag`
- `github-release`
- `ghcr-container-tag`

## Optional Digest Pinning

When the wrapped upstream publishes immutable image manifests, you can track both the human version and the exact image digest. This is the right fit for repos that pin `FROM upstream-image:<tag>@sha256:<digest>` and want upstream-monitor PRs to catch digest-only refreshes too.

Example:

```toml
[upstream]
name = "Infisical"
type = "github-release"
repo = "Infisical/infisical"
image = "infisical/infisical"
version_source = "dockerfile-arg"
version_key = "UPSTREAM_VERSION"
digest_source = "dockerhub-manifest"
digest_key = "UPSTREAM_IMAGE_DIGEST"
strategy = "pr"
stable_only = true

[notifications]
release_notes_url = "https://github.com/Infisical/infisical/releases"
```

## Example

```toml
[upstream]
name = "Sure"
type = "github-tag"
repo = "we-promise/sure"
version_source = "dockerfile-arg"
version_key = "UPSTREAM_VERSION"
strategy = "pr"
stable_only = true

[notifications]
release_notes_url = "https://github.com/we-promise/sure/releases"
```

## Version Pinning Pattern

Pin the wrapped upstream version explicitly in the Dockerfile:

```dockerfile
ARG UPSTREAM_VERSION=v0.6.8
FROM ghcr.io/we-promise/sure:${UPSTREAM_VERSION}
```

This gives the upstream monitor a concrete value to compare and update.

## Stable First

The default template policy is stable only. Do not expose prerelease channels until the derived repo has:

- strong integration tests
- confidence in upgrade safety
- a clear reason to offer beta or RC tags publicly
