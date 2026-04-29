from __future__ import annotations

import pytest

from tests.helpers import DockerRuntime, docker_available

IMAGE_TAG = "aio-template:pytest"
pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def runtime() -> DockerRuntime:
    if not docker_available():
        pytest.skip("Docker is unavailable; integration tests require Docker/OrbStack.")

    runtime = DockerRuntime(IMAGE_TAG)
    runtime.build()
    return runtime


def test_happy_path_boot_and_restart_persists_generated_env(
    runtime: DockerRuntime,
) -> None:
    with runtime.container() as container:
        container.wait_for_http()
        assert container.path_exists("/config/aio/generated.env")  # nosec B101

        secret_before = container.exec(
            "awk -F= '/^APP_SECRET_KEY=/{print $2}' /config/aio/generated.env"
        ).stdout.strip()
        assert secret_before  # nosec B101

        container.restart()
        container.wait_for_http()

        secret_after = container.exec(
            "awk -F= '/^APP_SECRET_KEY=/{print $2}' /config/aio/generated.env"
        ).stdout.strip()
        assert secret_after == secret_before  # nosec B101


def test_explicit_secret_override_skips_generated_secret(
    runtime: DockerRuntime,
) -> None:
    with runtime.container(
        env_overrides={"APP_SECRET_KEY": "explicit-template-value"}  # nosec B105
    ) as container:
        container.wait_for_http()
        result = container.exec(
            "grep '^APP_SECRET_KEY=' /config/aio/generated.env || true"
        )
        assert result.stdout.strip() == ""  # nosec B101
