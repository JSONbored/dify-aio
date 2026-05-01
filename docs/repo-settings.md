# Recommended GitHub Settings

Apply these to every derived repo before it becomes public.

## General

- Keep the repo private until the container, docs, and Actions are validated
- Enable Issues and Discussions only if you plan to support them
- Disable Wikis and Projects unless you actively use them
- Add a social preview image before the repo goes public
- Set a clear About description and relevant GitHub topics
- Confirm the Docker Hub repository is public and pullable after the first successful publish
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

- `aio-fleet / required`

## Actions

- Set `Workflow permissions` to `Read repository contents and packages`
- Enable `Allow GitHub Actions to create and approve pull requests` only if you explicitly want that
- Prefer `Allow select actions and reusable workflows`
- Allow GitHub-authored actions and verified creators
- Keep default `GITHUB_TOKEN` permissions minimal and only elevate inside jobs that publish
- Keep manual dispatch enabled so you can re-run validation or a controlled publish without making a noop commit
- Keep the central `aio-fleet` scheduled workflow enabled so upstream monitoring can run automatically

## Security

- Enable the dependency graph and GitHub vulnerability alerts
- Enable secret scanning
- Enable push protection
- Enable private vulnerability reporting
- Enable code scanning later if you add a relevant analyzer
- Keep shared dependency and upstream policy in `aio-fleet`

## Packages

- After the first successful publish, verify the Docker Hub repository is public if the repo is public
- Verify the Docker Hub image name matches the intended CA XML repository value

## Secrets and Variables

App repos should not carry repo-local workflow secrets for shared automation. Configure the GitHub App, Docker Hub credentials, and GHCR token in `aio-fleet`; keep app-local secrets only when the runtime itself needs them.

## Maintenance

- keep shared dependency and upstream policy in `aio-fleet`
- let `aio-fleet` own shared workflow, Trunk, and upstream automation
- review generated automation PRs manually before merging

## Derived Repo Checks Before Enabling Automation

- `dify-aio.xml` is the only root XML template
- starter base image comment is gone
- upstream version is pinned explicitly instead of relying on a floating stable tag
- integration tests assert the real readiness signal and health endpoint
- README no longer contains placeholder language
- XML points at the correct repo, icon, and support URLs
- `pytest tests/template` passes locally for app-specific template policy checks
- `.aio-fleet.yml` matches the central `aio-fleet` manifest and Dify update strategy
