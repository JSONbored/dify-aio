from __future__ import annotations

from aio_fleet.app_testing import DockerRuntime as BaseDockerRuntime
from aio_fleet.app_testing import *  # noqa: F403
from aio_fleet.app_testing import (
    PortMapping,
    VolumeMount,
    configure_docker_exec,
    configure_repo_root,
)

from tests.conftest import REPO_ROOT

configure_repo_root(REPO_ROOT)
configure_docker_exec(clear_proxy_env=True)


class DockerRuntime(BaseDockerRuntime):
    def __init__(self, image_tag: str) -> None:
        super().__init__(
            image_tag,
            name_prefix="dify-aio-pytest",
            port_mappings=(PortMapping("http_port", 8080),),
            volume_mounts=(VolumeMount("appdata_volume", "/appdata", "appdata"),),
            exec_clears_proxy_env=True,
        )
