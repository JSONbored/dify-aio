# Releases

`unraid-aio-template` uses normal semver releases such as `v0.1.0`.

This repository is not tied to a single wrapped upstream application, so it should not use the app-style `upstream-version-aio.N` format that the derived AIO repos use.

## What a template release means

A template release is a versioned milestone for the scaffolding itself, including:

- CI and workflow changes
- release automation updates
- documentation and support-thread templates
- XML and catalog sync defaults
- generic Docker and rootfs scaffolding improvements

## Release flow

1. Trigger **Prepare Release / Template** from `main`.
2. The workflow computes the next semver version and opens a release PR that updates `CHANGELOG.md`.
3. The same preparation flow also syncs the template XML `<Changes>` block from the latest `CHANGELOG.md` entry.
4. Review and merge that PR into `main`.
5. Trigger **Publish Release / Template** from `main`.
6. The workflow reads the merged `CHANGELOG.md` entry, creates the Git tag, and publishes the GitHub Release.
