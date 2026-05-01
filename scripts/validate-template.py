#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess  # nosec B404
import sys
from pathlib import Path

from defusedxml import ElementTree as ET

try:
    from components import load_components
except (
    ImportError
):  # pragma: no cover - used when imported as scripts.validate_template
    from scripts.components import load_components

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_ENV_PATH = ROOT / "docs/upstream/dify.env.example"
UPSTREAM_ENV_VARS_PATH = ROOT / "rootfs/opt/dify-aio/upstream-env-vars.txt"

GENERATED_CHANGELOG_NOTE = (
    "Generated from CHANGELOG.md during release preparation. Do not edit manually."
)
GENERATED_CHANGELOG_BULLET = f"- {GENERATED_CHANGELOG_NOTE}"
CHANGELOG_HEADER_PATTERN = re.compile(
    r"^### (?:\d{4}-\d{2}-\d{2}|Replace with release date)$"
)
LEGACY_CHANGELOG_MARKERS = (
    "[b]Latest release[/b]",
    "GitHub Releases",
    "Full changelog and release notes:",
)

REQUIRED_TEXT_FIELDS = (
    "Support",
    "Project",
    "Registry",
    "ReadMe",
    "Overview",
    "Category",
    "TemplateURL",
    "Icon",
    "Changes",
)

REQUIRED_DIFY_TARGETS = {
    "/appdata",
    "8080",
    "DB_SSL_MODE",
    "DIFY_AIO_EXTRA_ENV_FILE",
    "DIFY_AIO_PUBLIC_URL",
    "DIFY_AIO_WAIT_TIMEOUT_SECONDS",
    "DIFY_ENABLE_SANDBOX",
    "DIFY_BIND_ADDRESS",
    "DIFY_WEB_HOST",
    "DIFY_WEB_PORT",
    "DEPLOY_ENV",
    "DIFY_USE_INTERNAL_POSTGRES",
    "DIFY_USE_INTERNAL_REDIS",
    "NEXT_TELEMETRY_DISABLED",
    "PIP_MIRROR_URL",
    "PLUGIN_DEBUGGING_HOST",
    "PLUGIN_DEBUGGING_PORT",
    "PLUGIN_MAX_PACKAGE_SIZE",
    "PLUGIN_PLATFORM",
    "SENDGRID_API_KEY",
    "TZ",
    "WORKFLOW_NODE_EXECUTION_STORAGE",
}

DIFY_CATEGORY_TOKENS = {"AI", "Productivity", "Tools:Utilities"}


def run_common_template_validation() -> int:
    candidates = []
    explicit = os.environ.get("AIO_FLEET_MANIFEST", "").strip()
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend(
        [
            ROOT / ".aio-fleet" / "fleet.yml",
            ROOT.parent / "aio-fleet" / "fleet.yml",
        ]
    )
    manifest = next((candidate for candidate in candidates if candidate.exists()), None)
    if manifest is None:
        print(
            "warning: aio-fleet manifest not found; skipping common template validation",
            file=sys.stderr,
        )
        return 0

    env = os.environ.copy()
    fleet_src = manifest.parent / "src"
    if fleet_src.exists():
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{fleet_src}{os.pathsep}{existing}" if existing else str(fleet_src)
        )
    python = sys.executable
    fleet_python = manifest.parent / ".venv" / "bin" / "python"
    if fleet_python.exists():
        python = str(fleet_python)

    result = subprocess.run(  # nosec B603
        [
            python,
            "-m",
            "aio_fleet.cli",
            "--manifest",
            str(manifest),
            "validate-template-common",
            "--repo",
            ROOT.name,
            "--repo-path",
            str(ROOT),
        ],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    return result.returncode


def resolve_template_path() -> Path:
    explicit = os.environ.get("TEMPLATE_XML", "").strip()
    if explicit:
        return ROOT / explicit

    repo_xml = ROOT / f"{ROOT.name}.xml"
    if repo_xml.exists():
        return repo_xml

    xml_files = sorted(ROOT.glob("*.xml"))
    if len(xml_files) == 1:
        return xml_files[0]

    return ROOT / "template-aio.xml"


def is_placeholder_template(xml_path: Path) -> bool:
    return xml_path.name == "template-aio.xml" or ROOT.name == "unraid-aio-template"


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def validate_changes_block(xml_path: Path, changes: str) -> int:
    for marker in LEGACY_CHANGELOG_MARKERS:
        if marker in changes:
            return fail(
                f"{xml_path.name} <Changes> still includes the legacy release-link format: {marker}"
            )

    lines = [line.strip() for line in changes.splitlines() if line.strip()]
    if len(lines) < 2:
        return fail(
            f"{xml_path.name} <Changes> must contain a date heading and bullet lines"
        )

    if not CHANGELOG_HEADER_PATTERN.fullmatch(lines[0]):
        return fail(
            f"{xml_path.name} <Changes> must start with '### YYYY-MM-DD' or the template placeholder heading"
        )

    if lines[1] != GENERATED_CHANGELOG_BULLET:
        return fail(
            f"{xml_path.name} <Changes> second line should be '{GENERATED_CHANGELOG_BULLET}'"
        )

    invalid_lines = [line for line in lines[1:] if not line.startswith("- ")]
    if invalid_lines:
        return fail(
            f"{xml_path.name} <Changes> must use bullet lines only after the heading; found {invalid_lines[0]!r}"
        )

    return 0


def validate_template(xml_path: Path) -> int:
    if not xml_path.exists():
        return fail(f"Template XML not found: {xml_path}")

    tree = ET.parse(xml_path)
    root = tree.getroot()
    if root.tag != "Container":
        return fail(f"{xml_path.name} root tag should be <Container>")
    if root.attrib.get("version") != "2":
        return fail(f'{xml_path.name} should declare <Container version="2">')

    for field in REQUIRED_TEXT_FIELDS:
        value = (root.findtext(field) or "").strip()
        if not value:
            return fail(f"{xml_path.name} is missing a non-empty <{field}> field")

    template_url = (root.findtext("TemplateURL") or "").strip()
    if "awesome-unraid/main/" not in template_url:
        return fail(
            f"{xml_path.name} TemplateURL should point at raw awesome-unraid/main XML"
        )

    icon_url = (root.findtext("Icon") or "").strip()
    if "awesome-unraid/main/icons/" not in icon_url:
        return fail(
            f"{xml_path.name} Icon should point at raw awesome-unraid/main/icons asset"
        )

    changes = (root.findtext("Changes") or "").strip()
    if GENERATED_CHANGELOG_NOTE not in changes:
        return fail(
            f"{xml_path.name} <Changes> should include the generated-from-CHANGELOG note"
        )
    changes_status = validate_changes_block(xml_path, changes)
    if changes_status:
        return changes_status

    invalid_option_configs: list[str] = []
    invalid_pipe_configs: list[str] = []
    for config in root.findall(".//Config"):
        name = config.attrib.get("Name", config.attrib.get("Target", "<unnamed>"))
        if config.findall("Option"):
            invalid_option_configs.append(name)

        default = config.attrib.get("Default", "")
        if "|" not in default:
            continue

        allowed_values = default.split("|")
        if any(value == "" for value in allowed_values):
            invalid_pipe_configs.append(
                f"{name} (allowed={allowed_values!r}, empty pipe options are not allowed)"
            )
            continue

        selected_value = (config.text or "").strip()
        if selected_value not in allowed_values:
            invalid_pipe_configs.append(
                f"{name} (selected={selected_value!r}, allowed={allowed_values!r})"
            )

    if invalid_option_configs:
        print(
            f"{xml_path.name} uses nested <Option> tags, which are not allowed by the catalog-safe template format:",
            file=sys.stderr,
        )
        for name in invalid_option_configs:
            print(f"  - {name}", file=sys.stderr)
        return 1

    if invalid_pipe_configs:
        print(
            f"{xml_path.name} has pipe-delimited defaults whose selected value is not one of the allowed options:",
            file=sys.stderr,
        )
        for detail in invalid_pipe_configs:
            print(f"  - {detail}", file=sys.stderr)
        return 1

    if xml_path.name == "dify-aio.xml":
        category = (root.findtext("Category") or "").strip()
        category_tokens = set(category.split())
        if category_tokens != DIFY_CATEGORY_TOKENS or any(
            token.endswith(":") for token in category_tokens
        ):
            return fail(
                f"{xml_path.name} Category should be 'AI Productivity Tools:Utilities'"
            )

        repository = (root.findtext("Repository") or "").strip()
        registry = (root.findtext("Registry") or "").strip()
        if repository != "jsonbored/dify-aio:latest":
            return fail(
                f"{xml_path.name} Repository should point at the Docker Hub CA image"
            )
        if registry != "https://hub.docker.com/r/jsonbored/dify-aio":
            return fail(
                f"{xml_path.name} Registry should point at the Docker Hub repository"
            )

        coverage_status = validate_dify_env_surface(root)
        if coverage_status:
            return coverage_status

    template_kind = "placeholder " if is_placeholder_template(xml_path) else ""
    print(
        f"{xml_path.name} parsed successfully and passed {template_kind}catalog-safe validation"
    )
    return 0


def parse_upstream_env_targets(path: Path) -> list[str]:
    targets: list[str] = []
    for line in path.read_text().splitlines():
        match = re.match(r"^([A-Z_][A-Z0-9_]*)=", line)
        if match:
            targets.append(match.group(1))
    return targets


def validate_dify_env_surface(root: ET.Element) -> int:
    if not UPSTREAM_ENV_PATH.exists():
        return fail(f"Missing Dify upstream environment fixture: {UPSTREAM_ENV_PATH}")

    configs_by_target = {
        config.attrib["Target"]: config
        for config in root.findall(".//Config")
        if config.attrib.get("Target")
    }
    targets = set(configs_by_target)
    upstream_targets = parse_upstream_env_targets(UPSTREAM_ENV_PATH)

    try:
        from generate_dify_template import is_curated_upstream_target
    except ImportError:  # pragma: no cover - package import path for tests
        from scripts.generate_dify_template import is_curated_upstream_target

    curated_upstream_targets = {
        target for target in upstream_targets if is_curated_upstream_target(target)
    }
    missing = sorted((curated_upstream_targets | REQUIRED_DIFY_TARGETS) - targets)
    if missing:
        print(
            "dify-aio.xml is missing required Dify upstream/runtime targets:",
            file=sys.stderr,
        )
        for target in missing:
            print(f"  - {target}", file=sys.stderr)
        return 1

    if not UPSTREAM_ENV_VARS_PATH.exists():
        return fail(
            f"Missing generated upstream env-var list: {UPSTREAM_ENV_VARS_PATH}"
        )

    actual_env_vars = [
        line.strip()
        for line in UPSTREAM_ENV_VARS_PATH.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if actual_env_vars != upstream_targets:
        print(
            "rootfs/opt/dify-aio/upstream-env-vars.txt drifted from docs/upstream/dify.env.example:",
            file=sys.stderr,
        )
        expected_set = set(upstream_targets)
        actual_set = set(actual_env_vars)
        for target in sorted(expected_set - actual_set):
            print(f"  - missing from env-var list: {target}", file=sys.stderr)
        for target in sorted(actual_set - expected_set):
            print(f"  - stale in env-var list: {target}", file=sys.stderr)
        if expected_set == actual_set:
            print(
                "  - env-var list order differs from the upstream fixture",
                file=sys.stderr,
            )
        return 1

    try:
        from generate_dify_template import check_outputs
    except ImportError:  # pragma: no cover - package import path for tests
        from scripts.generate_dify_template import check_outputs

    if check_outputs():
        return 1

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Unraid template XML.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate every template referenced by components.toml.",
    )
    args = parser.parse_args()

    common_status = run_common_template_validation()
    if common_status:
        return common_status

    if args.all:
        failures = 0
        for component in load_components():
            failures += validate_template(ROOT / component.template)
        return 1 if failures else 0

    return validate_template(resolve_template_path())


if __name__ == "__main__":
    raise SystemExit(main())
