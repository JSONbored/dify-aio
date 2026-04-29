# AGENTS.md

This repository is the canonical baseline for current and future Unraid AIO repositories.

## Repository intent

- Treat this repo as the reference implementation for shared AIO patterns.
- Prefer template-first changes when a behavior should apply across the broader repo fleet.
- Keep the template practical, minimal, and reusable.

## Engineering expectations

- New shared conventions should land here before they spread elsewhere when practical.
- Avoid repo-specific assumptions that do not generalize.
- Keep CI and release behavior aligned with the current portfolio standard.
- Respect protected branches and PR-based automation.

## Release model

- Packages or derived artifacts may publish from downstream repos automatically.
- This repo itself uses normal semver releases such as `v0.1.0`.
- Formal changelog updates and GitHub Releases are release-driven.
- Keep changelog-friendly Conventional Commit titles and PR titles.

## Template expectations

- Optimize for maintainability and reuse.
- Preserve sane defaults for:
  - CI/CD
  - release automation
  - Unraid template metadata
  - support/community files
- Document tradeoffs plainly and avoid overstating what the template guarantees.

## Community expectations

- Future repos derived from this template should be able to support:
  - `awesome-unraid` sync
  - CA-ready metadata
  - per-app support threads
  - release-driven changelogs
