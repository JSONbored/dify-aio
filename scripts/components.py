#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tomllib
from dataclasses import asdict, dataclass

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPONENTS_FILE = ROOT / "components.toml"


@dataclass(frozen=True)
class Component:
    name: str
    type: str
    context: pathlib.Path
    dockerfile: pathlib.Path
    template: pathlib.Path
    image: str
    dockerhub_image: str
    cache_scope: str
    upstream_config: pathlib.Path
    release_suffix: str
    test_paths: tuple[pathlib.Path, ...]
    sync_paths: tuple[pathlib.Path, ...]

    def to_json(self) -> dict[str, object]:
        data = asdict(self)
        for key in ("context", "dockerfile", "template", "upstream_config"):
            data[key] = str(data[key])
        data["test_paths"] = [str(path) for path in self.test_paths]
        data["sync_paths"] = [str(path) for path in self.sync_paths]
        return data


def root_relative(path_value: str) -> pathlib.Path:
    return pathlib.Path(path_value)


def default_template_path() -> pathlib.Path:
    repo_xml = ROOT / f"{ROOT.name}.xml"
    if repo_xml.exists():
        return root_relative(repo_xml.name)

    xml_files = sorted(path for path in ROOT.glob("*.xml") if path.is_file())
    if len(xml_files) == 1:
        return root_relative(xml_files[0].name)

    return root_relative("template-aio.xml")


def default_component() -> Component:
    repo_name = ROOT.name
    template = default_template_path()
    return Component(
        name=repo_name,
        type="aio",
        context=root_relative("."),
        dockerfile=root_relative("Dockerfile"),
        template=template,
        image=f"jsonbored/{repo_name}",
        dockerhub_image=f"jsonbored/{repo_name}",
        cache_scope=f"{repo_name}-image",
        upstream_config=root_relative("upstream.toml"),
        release_suffix="aio",
        test_paths=(
            root_relative("tests/unit"),
            root_relative("tests/template"),
            root_relative("tests/integration"),
        ),
        sync_paths=(template, root_relative("assets/app-icon.png")),
    )


def load_components(path: pathlib.Path | None = None) -> list[Component]:
    if path is None:
        path = COMPONENTS_FILE
    if not path.exists():
        return [default_component()]

    data = tomllib.loads(path.read_text())
    raw_components = data.get("components", {})
    if not isinstance(raw_components, dict) or not raw_components:
        raise SystemExit(
            "components.toml must contain at least one [components.<name>] table"
        )

    components: list[Component] = []
    for name, raw in raw_components.items():
        if not isinstance(raw, dict):
            raise SystemExit(f"components.{name} must be a table")
        required = (
            "type",
            "context",
            "dockerfile",
            "template",
            "image",
            "dockerhub_image",
            "cache_scope",
            "upstream_config",
            "release_suffix",
            "test_paths",
        )
        missing = [key for key in required if key not in raw]
        if missing:
            raise SystemExit(
                f"components.{name} is missing required keys: {', '.join(missing)}"
            )

        test_paths = raw["test_paths"]
        if not isinstance(test_paths, list) or not all(
            isinstance(item, str) for item in test_paths
        ):
            raise SystemExit(f"components.{name}.test_paths must be a list of strings")

        raw_sync_paths = raw.get("sync_paths", [raw["template"], "assets/app-icon.png"])
        if not isinstance(raw_sync_paths, list) or not all(
            isinstance(item, str) for item in raw_sync_paths
        ):
            raise SystemExit(f"components.{name}.sync_paths must be a list of strings")

        components.append(
            Component(
                name=name,
                type=str(raw["type"]),
                context=root_relative(str(raw["context"])),
                dockerfile=root_relative(str(raw["dockerfile"])),
                template=root_relative(str(raw["template"])),
                image=str(raw["image"]),
                dockerhub_image=str(raw["dockerhub_image"]),
                cache_scope=str(raw["cache_scope"]),
                upstream_config=root_relative(str(raw["upstream_config"])),
                release_suffix=str(raw["release_suffix"]),
                test_paths=tuple(root_relative(item) for item in test_paths),
                sync_paths=tuple(root_relative(item) for item in raw_sync_paths),
            )
        )

    names = [component.name for component in components]
    if len(names) != len(set(names)):
        raise SystemExit("components.toml contains duplicate component names")

    return components


def get_component(name: str) -> Component:
    for component in load_components():
        if component.name == name:
            return component
    raise SystemExit(f"Unknown component: {name}")


def component_for_template(template: pathlib.Path) -> Component | None:
    normalized = pathlib.Path(template)
    for component in load_components():
        if component.template == normalized:
            return component
    return None


def changed_components(paths: list[str]) -> list[Component]:
    components = load_components()
    if not paths:
        return components

    shared_prefixes = (
        ".github/",
        ".trunk/",
        "scripts/",
        "tests/unit/",
        "tests/template/",
    )
    shared_files = {
        "CHANGELOG.md",
        "cliff.toml",
        "components.toml",
        "pyproject.toml",
        "requirements-dev.txt",
        "renovate.json",
    }
    selected: set[str] = set()
    for path in paths:
        if path in shared_files or path.startswith(shared_prefixes):
            return components
        for component in components:
            watched = {
                str(component.context).rstrip("/") + "/",
                str(component.dockerfile),
                str(component.template),
                str(component.upstream_config),
            }
            if path in watched or any(
                path.startswith(item) for item in watched if item.endswith("/")
            ):
                selected.add(component.name)

    return [component for component in components if component.name in selected]


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect suite components.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list")
    matrix_parser = subparsers.add_parser("matrix")
    matrix_parser.add_argument("paths", nargs="*")
    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("name")
    args = parser.parse_args()

    if args.command == "list":
        print(json.dumps([component.to_json() for component in load_components()]))
        return 0
    if args.command == "matrix":
        print(
            json.dumps(
                {
                    "include": [
                        component.to_json()
                        for component in changed_components(args.paths)
                    ]
                }
            )
        )
        return 0
    if args.command == "get":
        print(json.dumps(get_component(args.name).to_json()))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
