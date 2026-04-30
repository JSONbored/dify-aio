#!/usr/bin/env python3
from __future__ import annotations

import html
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CHANGELOG = ROOT / "CHANGELOG.md"
GENERATED_NOTE_TEXT = (
    "Generated from CHANGELOG.md during release preparation. Do not edit manually."
)
GENERATED_NOTE = f"- {GENERATED_NOTE_TEXT}"


def latest_changelog_version(changelog: pathlib.Path = DEFAULT_CHANGELOG) -> str | None:
    heading = re.compile(r"^##\s+(?:\[([^\]]+)\]\([^)]+\)|([^\s]+))(?:\s+-\s+.+)?$")
    for line in changelog.read_text().splitlines():
        match = heading.match(line.strip())
        if not match:
            continue
        version = match.group(1) or match.group(2)
        if version != "Unreleased":
            return version
    return None


def extract_release_notes(version: str, changelog: pathlib.Path) -> str:
    heading = re.compile(
        rf"^##\s+(?:\[{re.escape(version)}\]\([^)]+\)|{re.escape(version)})(?:\s+-\s+.+)?$"
    )
    next_heading = re.compile(r"^##\s+")

    lines = changelog.read_text().splitlines()
    start = None
    for idx, line in enumerate(lines):
        if heading.match(line.strip()):
            start = idx + 1
            break

    if start is None:
        raise SystemExit(f"Unable to find release section for {version} in {changelog}")

    end = len(lines)
    for idx in range(start, len(lines)):
        if next_heading.match(lines[idx].strip()):
            end = idx
            break

    notes = "\n".join(lines[start:end]).strip()
    if not notes:
        raise SystemExit(f"Release section for {version} in {changelog} is empty")
    return notes


def release_heading(version: str, changelog: pathlib.Path) -> str:
    heading = re.compile(
        rf"^##\s+(?:\[{re.escape(version)}\]\([^)]+\)|{re.escape(version)})(?:\s+-\s+(.+))?$"
    )
    for line in changelog.read_text().splitlines():
        match = heading.match(line.strip())
        if match:
            release_date = (match.group(1) or "").strip()
            if release_date:
                return f"### {release_date}"
            break
    return f"### {version}"


def build_changes_body(
    version: str,
    notes: str,
    changelog: pathlib.Path,
) -> str:
    lines: list[str] = [release_heading(version, changelog), GENERATED_NOTE]
    for line in notes.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            continue
        if re.match(r"^\[[^\]]+\]:\s+https?://", stripped):
            continue
        if stripped.startswith("Full Changelog:"):
            continue
        if stripped.startswith("## "):
            continue
        if stripped.startswith("### "):
            continue
        if stripped.startswith(("- ", "* ")):
            lines.append(f"- {stripped[2:].strip()}")
            continue
        lines.append(f"- {stripped}")

    if len(lines) == 2:
        raise SystemExit("Release notes did not produce any bullet lines for <Changes>")

    return "\n".join(lines).strip()


def changes_body_from_changelog(
    changelog: pathlib.Path = DEFAULT_CHANGELOG,
    fallback: str | None = None,
) -> str:
    version = latest_changelog_version(changelog)
    if version is None:
        if fallback is not None:
            return fallback
        raise SystemExit(f"Unable to find a released version heading in {changelog}")

    notes = extract_release_notes(version, changelog)
    return build_changes_body(version, notes, changelog)


def encode_for_template(body: str) -> str:
    escaped = html.escape(body, quote=False)
    return escaped.replace("\n", "&#xD;\n")
