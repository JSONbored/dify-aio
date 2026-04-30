from __future__ import annotations

from pathlib import Path

BUILD_WORKFLOW = Path(".github/workflows/build.yml")
PYTEST_ACTION = Path(".github/actions/run-pytest/action.yml")


def test_pytest_jobs_use_shared_local_action() -> None:
    workflow = BUILD_WORKFLOW.read_text()

    assert workflow.count("uses: ./.github/actions/run-pytest") == 3  # nosec B101
    assert "Upload unit test results to Trunk" not in workflow  # nosec B101
    assert "Upload integration test results to Trunk" not in workflow  # nosec B101
    assert "trunk-io/analytics-uploader@" in PYTEST_ACTION.read_text()  # nosec B101


def test_integration_and_publish_share_docker_cache_scope() -> None:
    workflow = BUILD_WORKFLOW.read_text()

    assert "DOCKER_CACHE_SCOPE: dify-aio-image" in workflow  # nosec B101
    assert (  # nosec B101
        workflow.count("cache-from: type=gha,scope=${{ env.DOCKER_CACHE_SCOPE }}") == 3
    )
    assert (  # nosec B101
        workflow.count(
            "cache-to: type=gha,mode=max,scope=${{ env.DOCKER_CACHE_SCOPE }}"
        )
        == 3
    )


def test_publish_mirrors_tags_to_docker_hub_when_configured() -> None:
    workflow = BUILD_WORKFLOW.read_text()

    assert "Resolve Docker Hub publish settings" in workflow  # nosec B101
    assert "Login to Docker Hub" in workflow  # nosec B101
    assert "secrets.DOCKERHUB_USERNAME" in workflow  # nosec B101
    assert "secrets.DOCKERHUB_TOKEN" in workflow  # nosec B101
    assert "vars.DOCKERHUB_IMAGE_NAME" in workflow  # nosec B101
    assert 'if [[ "${DOCKERHUB_ENABLED}" == "true" ]]; then' in workflow  # nosec B101
    assert 'echo "${image_dockerhub}:latest"' in workflow  # nosec B101
    assert 'echo "${image_dockerhub}:sha-${GITHUB_SHA}"' in workflow  # nosec B101


def test_template_release_changes_publish_but_unit_test_changes_do_not() -> None:
    workflow = BUILD_WORKFLOW.read_text()

    assert (
        "publish_related: ${{ steps.filter.outputs.publish_related }}" in workflow
    )  # nosec B101
    assert "publish_related=false" in workflow  # nosec B101
    assert "publish_related=true" in workflow  # nosec B101
    assert "Dockerfile|upstream.toml|rootfs/*)" in workflow  # nosec B101
    assert "CHANGELOG.md)" in workflow  # nosec B101
    assert "cliff.toml|scripts/*|.trunk/*|tests/*)" in workflow  # nosec B101
    assert (
        "tests/integration/*|tests/helpers.py|tests/conftest.py" in workflow
    )  # nosec B101
    assert (  # nosec B101
        "needs.detect-changes.outputs.run_tests_requested == 'true' && "
        "(needs.detect-changes.outputs.build_related == 'true' || "
        "(github.event_name == 'push' && github.ref == 'refs/heads/main' && "
        "needs.detect-changes.outputs.publish_requested == 'true' && "
        "needs.detect-changes.outputs.publish_related == 'true'))"
    ) in workflow
    assert (  # nosec B101
        "needs.detect-changes.outputs.publish_related == 'true' && "
        "github.event_name == 'push'"
    ) in workflow
    assert (  # nosec B101
        "github.event_name == 'push' && github.ref == 'refs/heads/main' && "
        "needs.detect-changes.outputs.publish_requested == 'true'))"
    ) not in workflow


def test_release_image_tags_use_release_target_commit() -> None:
    workflow = BUILD_WORKFLOW.read_text()

    assert "fetch-depth: 0" in workflow  # nosec B101
    assert (  # nosec B101
        'release_target_commit="$(python3 scripts/release.py find-release-target-commit "${changelog_version}"'
        in workflow
    )
    assert '"${release_target_commit}" == "${GITHUB_SHA}"' in workflow  # nosec B101
    assert "release_commit_pattern=" not in workflow  # nosec B101


def test_local_actions_participate_in_ci_change_detection_and_pin_checks() -> None:
    workflow = BUILD_WORKFLOW.read_text()

    assert "- .github/actions/**" in workflow  # nosec B101
    assert ".github/actions/**|.github/workflows/*)" in workflow  # nosec B101
    assert (
        'pathlib.Path(".github/actions").glob("*/action.yml")' in workflow
    )  # nosec B101


def test_extended_integration_is_manual_and_uses_marker() -> None:
    workflow = BUILD_WORKFLOW.read_text()

    assert "run_extended_integration" in workflow  # nosec B101
    assert (  # nosec B101
        "github.event_name == 'workflow_dispatch' && "
        "inputs.run_extended_integration == true"
    ) in workflow
    assert (
        "pytest-args: tests/integration -m extended_integration" in workflow
    )  # nosec B101
