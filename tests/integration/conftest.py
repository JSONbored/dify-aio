from __future__ import annotations

import pytest

from tests.helpers import DockerRuntime, docker_available

IMAGE_TAG = "dify-aio:pytest"


@pytest.fixture(scope="session")
def runtime() -> DockerRuntime:
    if not docker_available():
        pytest.skip("Docker is unavailable; integration tests require Docker/OrbStack.")

    runtime = DockerRuntime(IMAGE_TAG)
    runtime.build()
    return runtime
