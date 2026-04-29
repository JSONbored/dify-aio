# Recommended GitHub Settings

Apply these to every derived repo before it becomes public.

## General

- Keep the repo private until the container, docs, and Actions are validated
- Enable Issues and Discussions only if you plan to support them
- Disable Wikis and Projects unless you actively use them
- Add a social preview image before the repo goes public
- Set a clear About description and relevant GitHub topics
- Mark the GHCR package public only after the first successful publish
- Make sure the repo description clearly reflects the wrapped upstream app

## Branch Protection

Create a ruleset for `main`:

- require pull request before merge
- require status checks to pass before merge
- require signed commits
- require linear history
- block force pushes
- block branch deletion
- include administrators

Suggested required checks:

- `validate-template`
- `pinned-actions`
- `dependency-review`
- `unit-tests`
- `integration-tests`

## Actions

- Set `Workflow permissions` to `Read repository contents and packages`
- Enable `Allow GitHub Actions to create and approve pull requests` only if you explicitly want that
- Prefer `Allow select actions and reusable workflows`
- Allow GitHub-authored actions and verified creators
- Keep default `GITHUB_TOKEN` permissions minimal and only elevate inside jobs that publish
- Keep manual dispatch enabled so you can re-run validation or a controlled publish without making a noop commit
- Keep scheduled workflows enabled so upstream monitoring can run automatically

## Security

- Enable the dependency graph and GitHub vulnerability alerts
- Enable secret scanning
- Enable push protection
- Enable private vulnerability reporting
- Enable code scanning later if you add a relevant analyzer
- Use Renovate for update PRs instead of Dependabot update PRs

## Packages

- After the first successful publish, make the GHCR package public if the repo is public
- Verify the package name matches the intended CA XML repository value

## Secrets and Variables

No Actions variables are required by default.

Optional variables:

- `IMAGE_NAME_OVERRIDE`
- `TEMPLATE_XML`
- `AWESOME_UNRAID_REPOSITORY`
- `AWESOME_UNRAID_XML_NAME`
- `AWESOME_UNRAID_ICON_NAME`
- `TEMPLATE_ICON_PATH`

Required secret:

- `SYNC_TOKEN`

Default sync behavior without overrides:

- XML source: `<repo-name>.xml`
- awesome-unraid target repo: `JSONbored/awesome-unraid`
- target XML name: `<repo-name>.xml`
- target icon path source: `assets/app-icon.png`
- target icon name: derived from the XML name, for example `dify-aio.xml -> dify.png`

## Maintenance

- install the Renovate GitHub App on each derived repo
- let Renovate manage pinned GitHub Action SHAs and Docker dependency updates
- review Renovate PRs manually before merging

## Derived Repo Checks Before Enabling Automation

- `dify-aio.xml` is the only root XML template
- starter base image comment is gone
- upstream version is pinned explicitly instead of relying on a floating stable tag
- integration tests assert the real readiness signal and health endpoint
- README no longer contains placeholder language
- XML points at the correct repo, icon, and support URLs
- `pytest tests/unit tests/template` passes locally, including the placeholder and XML checks
- `upstream.toml` matches the real upstream app and update strategy
