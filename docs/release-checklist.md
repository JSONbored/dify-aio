# Release Checklist

## Before First Public Push

- replace every placeholder value and example hostname
- replace `assets/app-icon.png`
- confirm `dify-aio.xml` is the only root XML template
- confirm README, SECURITY, and FUNDING are accurate
- confirm `Support`, `Project`, `TemplateURL`, and `Icon` URLs are correct
- pin the upstream version explicitly
- confirm `.aio-fleet.yml` matches the central `aio-fleet` manifest
- add a screenshot or demo visual if the app has a UI
- set the repo About description, topics, and social preview image
- run `pytest tests/unit tests/template`
- run `pytest tests/integration -m integration`
- run `pytest tests/integration -m extended_integration` before public submission or major upstream/config changes

## Before Enabling Actions

- add optional sync override variables only if you need to diverge from the repo-name defaults
- confirm the `aio-fleet` GitHub App is installed on this repo and `awesome-unraid`
- confirm shared dependency/upstream automation is represented in `aio-fleet`
- verify branch protection and secret scanning are enabled
- confirm `aio-fleet / required` passes before allowing publish

## Before Unraid Submission

- install from the XML in a clean Unraid environment
- verify first boot works with defaults
- verify advanced settings stay optional
- verify generated credentials persist if applicable
- confirm the Docker Hub image is public and pullable
- confirm `awesome-unraid` contains the XML and icon
- confirm the README first-run notes match the real install behavior
- confirm version tags such as `1.14.0-aio.1` publish the expected image tags
- confirm the upstream monitor opens the expected PR or issue path
