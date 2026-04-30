#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import re
import sys

try:
    from components import get_component
    from template_changes import (
        DEFAULT_CHANGELOG,
        build_changes_body,
        encode_for_template,
        extract_release_notes,
    )
except ImportError:  # pragma: no cover - used when imported as a package module
    from scripts.components import get_component
    from scripts.template_changes import (
        DEFAULT_CHANGELOG,
        build_changes_body,
        encode_for_template,
        extract_release_notes,
    )

ROOT = pathlib.Path(__file__).resolve().parents[1]


def resolve_template_path() -> pathlib.Path:
    repo_xml = ROOT / f"{ROOT.name}.xml"
    if repo_xml.exists():
        return repo_xml

    xml_files = sorted(ROOT.glob("*.xml"))
    if len(xml_files) == 1:
        return xml_files[0]

    return ROOT / "template-aio.xml"


def update_template(template_path: pathlib.Path, encoded_changes: str) -> None:
    content = template_path.read_text()
    pattern = re.compile(r"<Changes>.*?</Changes>", re.DOTALL)
    replacement = f"<Changes>{encoded_changes}</Changes>"
    updated, count = pattern.subn(replacement, content, count=1)
    if count != 1:
        raise SystemExit(f"Expected exactly one <Changes> block in {template_path}")
    template_path.write_text(updated)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update the template XML <Changes> block from CHANGELOG release notes."
    )
    parser.add_argument("version", help="Release version (example: v0.2.0)")
    parser.add_argument("--changelog", type=pathlib.Path, default=DEFAULT_CHANGELOG)
    parser.add_argument("--template", type=pathlib.Path, default=None)
    parser.add_argument(
        "--component",
        help="Component name from components.toml whose template should be updated.",
    )
    args = parser.parse_args()

    template_path = args.template
    if template_path is None and args.component:
        template_path = ROOT / get_component(args.component).template
    if template_path is None:
        template_path = resolve_template_path()
    notes = extract_release_notes(args.version, args.changelog)
    body = build_changes_body(args.version, notes, args.changelog)
    update_template(template_path, encode_for_template(body))
    print(
        f"Updated <Changes> in {template_path} from {args.changelog} for {args.version}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
