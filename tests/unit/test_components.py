from __future__ import annotations

from pathlib import Path

from scripts import components


def test_load_components_reads_suite_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "components.toml"
    manifest.write_text("""
[components.primary]
type = "aio"
context = "."
dockerfile = "Dockerfile"
template = "primary.xml"
image = "jsonbored/primary"
dockerhub_image = "jsonbored/primary"
cache_scope = "primary-image"
upstream_config = "upstream.toml"
release_suffix = "aio"
test_paths = ["tests/unit", "tests/template"]

[components.agent]
type = "agent"
context = "components/agent"
dockerfile = "components/agent/Dockerfile"
template = "agent.xml"
image = "jsonbored/agent"
dockerhub_image = "jsonbored/agent"
cache_scope = "agent-image"
upstream_config = "components/agent/upstream.toml"
release_suffix = "agent"
test_paths = ["tests/unit", "tests/template", "tests/integration_agent"]
sync_paths = ["agent.xml", "icons/agent.png"]
""".strip())

    loaded = components.load_components(manifest)

    assert [component.name for component in loaded] == [  # nosec B101
        "primary",
        "agent",
    ]
    assert loaded[1].template == Path("agent.xml")  # nosec B101
    assert loaded[1].sync_paths == (
        Path("agent.xml"),
        Path("icons/agent.png"),
    )  # nosec B101


def test_changed_components_selects_component_specific_paths(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = tmp_path / "components.toml"
    manifest.write_text("""
[components.primary]
type = "aio"
context = "."
dockerfile = "Dockerfile"
template = "primary.xml"
image = "jsonbored/primary"
dockerhub_image = "jsonbored/primary"
cache_scope = "primary-image"
upstream_config = "upstream.toml"
release_suffix = "aio"
test_paths = ["tests/unit", "tests/template"]

[components.agent]
type = "agent"
context = "components/agent"
dockerfile = "components/agent/Dockerfile"
template = "agent.xml"
image = "jsonbored/agent"
dockerhub_image = "jsonbored/agent"
cache_scope = "agent-image"
upstream_config = "components/agent/upstream.toml"
release_suffix = "agent"
test_paths = ["tests/unit", "tests/template", "tests/integration_agent"]
""".strip())
    monkeypatch.setattr(components, "COMPONENTS_FILE", manifest)

    selected = components.changed_components(["components/agent/Dockerfile"])
    assert [component.name for component in selected] == ["agent"]  # nosec B101

    selected = components.changed_components(["scripts/components.py"])
    assert [component.name for component in selected] == [  # nosec B101
        "primary",
        "agent",
    ]
