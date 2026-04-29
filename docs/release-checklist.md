# Release Checklist

## Before First Public Push

- replace every placeholder value and example hostname
- replace `assets/app-icon.png`
- rename `template-aio.xml`
- confirm README, SECURITY, and FUNDING are accurate
- confirm `Support`, `Project`, `TemplateURL`, and `Icon` URLs are correct
- pin the upstream version explicitly
- configure `upstream.toml`
- add a screenshot or demo visual if the app has a UI
- set the repo About description, topics, and social preview image
- run `pytest tests/unit tests/template`
- run `pytest tests/integration -m integration`

## Before Enabling Actions

- add optional sync override variables only if you need to diverge from the repo-name defaults
- add `SYNC_TOKEN`
- confirm Renovate is installed for the repo
- verify branch protection and secret scanning are enabled
- confirm `validate-template`, `unit-tests`, and `integration-tests` pass before allowing publish

## Before Unraid Submission

- install from the XML in a clean Unraid environment
- verify first boot works with defaults
- verify advanced settings stay optional
- verify generated credentials persist if applicable
- confirm GHCR package is public and pullable
- confirm `awesome-unraid` contains the XML and icon
- confirm the README first-run notes match the real install behavior
- if using release tags, confirm version tags such as `v1.2.3` publish the expected image tags
- confirm the upstream monitor opens the expected PR or issue path
