# Unraid AIO Template

A hardened starter for future `*-aio` repositories: one public repo per app, one companion GHCR image, one Unraid CA XML, and one beginner-first experience that still leaves room for power-user overrides.

This template is opinionated on purpose. It is built for repos that should be:

- easy for newcomers to install
- honest about what is embedded versus external
- reproducible in CI before publishing `latest`
- cleanly syncable into `awesome-unraid`

## What This Template Ships With

- starter [`Dockerfile`](/tmp/unraid-aio-template/Dockerfile) for wrapping an upstream image with `s6-overlay`
- starter CA XML at [`template-aio.xml`](/tmp/unraid-aio-template/template-aio.xml)
- shared pytest harness under [`tests/`](/tmp/unraid-aio-template/tests)
- generic XML validator at [`scripts/validate-template.py`](/tmp/unraid-aio-template/scripts/validate-template.py)
- optional suite component manifest support via [`components.toml`](/tmp/unraid-aio-template/docs/suite-components.md)
- CI gate helper at [`scripts/ci_flags.py`](/tmp/unraid-aio-template/scripts/ci_flags.py)
- changelog-to-XML sync helper at [`scripts/update-template-changes.py`](/tmp/unraid-aio-template/scripts/update-template-changes.py)
- derived-repo guardrail script at [`scripts/validate-derived-repo.sh`](/tmp/unraid-aio-template/scripts/validate-derived-repo.sh)
- upstream monitor scaffold at [`upstream.toml`](/tmp/unraid-aio-template/upstream.toml)
- GitHub Actions for validation, pytest-backed integration gating, main-branch publish, security checks, and optional `awesome-unraid` sync
- starter docs, changelog, funding, issue templates, and security policy
- public repo checklists under [`docs/`](/tmp/unraid-aio-template/docs)

## Design Principles

- single-container first when it is realistic and not misleading
- safe defaults for beginners, advanced knobs for power users
- generated first-run secrets only when the app truly needs them
- no publish until placeholders are gone and pytest passes
- pinned workflow action SHAs and Renovate-managed dependency updates
- stable-only upstream tracking with PR-first updates
- optional upstream image digest tracking for repos that pin immutable manifests
- update automation opens PRs, but merge decisions stay manual
- public repos stay public-facing and product-facing only

## Recommended Workflow

1. Create a new private repo from this template.
2. Rename `template-aio.xml` to the final app slug, for example `myapp-aio.xml`.
3. Replace placeholders in the Dockerfile, XML, rootfs scripts, pytest harness, README, funding file, and security policy.
4. Replace [`assets/app-icon.png`](/tmp/unraid-aio-template/assets/app-icon.png) with the real icon.
5. Follow [`docs/customization-guide.md`](/tmp/unraid-aio-template/docs/customization-guide.md).
6. Follow [`docs/repo-settings.md`](/tmp/unraid-aio-template/docs/repo-settings.md).
7. Once secrets are configured, let `main` pushes handle package publishing and downstream XML sync PRs automatically.
8. Install the Renovate GitHub App for the derived repo so pinned actions and Docker dependencies stay current.
9. Configure [`upstream.toml`](/tmp/unraid-aio-template/upstream.toml) so the repo can monitor the wrapped upstream app.
10. Keep the XML `<Changes>` block in the fleet-standard date-first format: `### YYYY-MM-DD` followed by short bullet lines only.

For ecosystems that need companion images such as agents, workers, or proxies,
use the optional suite component pattern in
[`docs/suite-components.md`](/tmp/unraid-aio-template/docs/suite-components.md).
Most repos should still stay single-component unless the companion is tightly
bound to the same upstream product and support surface.

## Actions Variables

No Actions variables are required for the default JSONbored workflow.

Optional overrides:

- `IMAGE_NAME_OVERRIDE=jsonbored/yourapp-aio`
- `TEMPLATE_XML=yourapp-aio.xml`
- `AWESOME_UNRAID_REPOSITORY=JSONbored/awesome-unraid`
- `AWESOME_UNRAID_XML_NAME=yourapp-aio.xml`
- `AWESOME_UNRAID_ICON_NAME=yourapp.png`
- `TEMPLATE_ICON_PATH=assets/app-icon.png`

If you do not set the optional sync overrides, the workflow defaults to:

- target repo: `JSONbored/awesome-unraid`
- XML name: `<repo-name>.xml`
- icon path: `assets/app-icon.png`
- icon name: derived from the XML name, for example `yourapp-aio.xml -> yourapp.png`

## Required Actions Secret

- `SYNC_TOKEN`
  - fine-grained PAT
  - repository access: `JSONbored/awesome-unraid`
  - permission: `Contents: Read and write`

## Files To Customize First

- [`Dockerfile`](/tmp/unraid-aio-template/Dockerfile)
- [`template-aio.xml`](/tmp/unraid-aio-template/template-aio.xml)
- [`pyproject.toml`](/tmp/unraid-aio-template/pyproject.toml)
- [`tests/`](/tmp/unraid-aio-template/tests/)
- [`scripts/validate-template.py`](/tmp/unraid-aio-template/scripts/validate-template.py)
- [`scripts/update-template-changes.py`](/tmp/unraid-aio-template/scripts/update-template-changes.py)
- [`scripts/components.py`](/tmp/unraid-aio-template/scripts/components.py)
- [`rootfs/etc/cont-init.d/01-bootstrap.sh`](/tmp/unraid-aio-template/rootfs/etc/cont-init.d/01-bootstrap.sh)
- [`rootfs/etc/services.d/app/run`](/tmp/unraid-aio-template/rootfs/etc/services.d/app/run)
- [`README.md`](/tmp/unraid-aio-template/README.md)
- [`.github/FUNDING.yml`](/tmp/unraid-aio-template/.github/FUNDING.yml)
- [`SECURITY.md`](/tmp/unraid-aio-template/SECURITY.md)
- [`upstream.toml`](/tmp/unraid-aio-template/upstream.toml)

## Validation Flow

Derived repos created from this template should follow this order:

1. local placeholder cleanup
2. `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt`
3. `pytest tests/unit tests/template`
4. `pytest tests/integration -m integration`
5. `pytest tests/unit tests/template --junit-xml=reports/pytest-unit.xml -o junit_family=xunit1`
6. `pytest tests/integration -m integration --junit-xml=reports/pytest-integration.xml -o junit_family=xunit1`
7. `./trunk-analytics-cli validate --junit-paths "reports/pytest-unit.xml,reports/pytest-integration.xml"`
8. enable automation
9. CI validation and publish
10. `awesome-unraid` sync using the repo-name-derived defaults or your optional overrides
11. real Unraid install validation

CI cost model for derived repos:

- run unit/template tests on relevant PRs and `main` pushes
- run Docker-backed integration tests on build-relevant `main` pushes, on release-metadata `main` pushes that are still publish-eligible, and on manual workflow dispatches
- require integration success before publish jobs can push images
- keep local integration runs explicit instead of binding them to every pre-commit or pre-push hook by default

Use [`docs/release-checklist.md`](/tmp/unraid-aio-template/docs/release-checklist.md) before making a derived repo public or submitting it to CA.

## Upstream Tracking

Use [`docs/upstream-tracking.md`](/tmp/unraid-aio-template/docs/upstream-tracking.md) to wire the derived repo to the stable upstream app it wraps.

## Releases

This template should use normal semver releases such as `v0.1.0`, not upstream-aligned app versions.

See [`docs/releases.md`](/tmp/unraid-aio-template/docs/releases.md) for the protected-branch-safe release workflow and changelog process.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=JSONbored/unraid-aio-template&type=date&legend=top-left)](https://www.star-history.com/#JSONbored/unraid-aio-template&Date)
