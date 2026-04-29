#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import subprocess  # nosec B404 - release helpers shell out only to trusted local git
from typing import Iterable

try:
    from components import get_component
except ImportError:  # pragma: no cover - used when imported as a package module
    from scripts.components import get_component

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CHANGELOG = ROOT / "CHANGELOG.md"
GIT_BIN = shutil.which("git")


SEMVER_TAG = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def git(*args: str) -> str:
    if GIT_BIN is None:
        raise SystemExit("git is required to run release helpers")
    return subprocess.check_output(  # nosec B603 - arguments are fixed git subcommands
        [GIT_BIN, *args],
        cwd=ROOT,
        text=True,
    ).strip()


def semver_key(tag: str) -> tuple[int, int, int] | None:
    match = SEMVER_TAG.match(tag)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def latest_semver_tag() -> str | None:
    tags = []
    for tag in git("tag", "--list").splitlines():
        tag = tag.strip()
        if not tag:
            continue
        key = semver_key(tag)
        if key is not None:
            tags.append((key, tag if tag.startswith("v") else f"v{tag}"))
    if not tags:
        return None
    tags.sort(key=lambda item: item[0])
    return tags[-1][1]


def latest_release_tag() -> str | None:
    return latest_semver_tag()


def commits_since(ref: str | None) -> Iterable[str]:
    args = ["log", "--format=%s"]
    if ref:
        args.append(f"{ref}..HEAD")
    output = git(*args)
    return [line.strip() for line in output.splitlines() if line.strip()]


def has_unreleased_changes() -> bool:
    latest = latest_semver_tag()
    return any(commits_since(latest))


def next_release_version() -> str:
    latest = latest_semver_tag()
    if latest is None:
        return "v0.1.0"

    major, minor, patch = semver_key(latest)  # type: ignore[arg-type]
    commit_messages = list(commits_since(latest))

    has_breaking = any(
        "BREAKING CHANGE" in message or re.match(r"^[a-z]+(\(.+\))?!:", message)
        for message in commit_messages
    )
    has_feature = any(
        re.match(r"^feat(\(.+\))?:", message) for message in commit_messages
    )

    if has_breaking:
        major += 1
        minor = 0
        patch = 0
    elif has_feature:
        minor += 1
        patch = 0
    else:
        patch += 1

    return f"v{major}.{minor}.{patch}"


def latest_changelog_version(changelog: pathlib.Path) -> str:
    pattern = re.compile(r"^##\s+([^\s]+)")
    for line in changelog.read_text().splitlines():
        match = pattern.match(line.strip())
        if match and match.group(1) != "Unreleased":
            return match.group(1)
    raise SystemExit(f"Unable to find a released version heading in {changelog}")


def extract_release_notes(version: str, changelog: pathlib.Path) -> str:
    heading = re.compile(rf"^##\s+{re.escape(version)}(?:\s+-\s+.+)?$")
    next_heading = re.compile(r"^##\s+")

    lines = changelog.read_text().splitlines()
    start = None
    for index, line in enumerate(lines):
        if heading.match(line.strip()):
            start = index + 1
            break

    if start is None:
        raise SystemExit(f"Unable to find release section for {version} in {changelog}")

    end = len(lines)
    for index in range(start, len(lines)):
        if next_heading.match(lines[index].strip()):
            end = index
            break

    notes = "\n".join(lines[start:end]).strip()
    if not notes:
        raise SystemExit(f"Release section for {version} in {changelog} is empty")
    return notes


def find_release_commit(version: str) -> str:
    exact = f"chore(release): {version}"
    with_suffix = re.compile(rf"^{re.escape(exact)} \(#\d+\)$")

    output = git("log", "--format=%H\t%s", "HEAD")
    for line in output.splitlines():
        if not line.strip():
            continue
        sha, subject = line.split("\t", 1)
        if subject == exact or with_suffix.match(subject):
            return sha

    raise SystemExit(
        f"Unable to find a merged release commit for {version} on main. "
        f"Expected '{exact}' or '{exact} (#123)'."
    )


def git_completed(*args: str) -> subprocess.CompletedProcess[str]:
    if GIT_BIN is None:
        raise SystemExit("git is required to run release helpers")
    return subprocess.run(
        [GIT_BIN, *args], cwd=ROOT, text=True, capture_output=True, check=False
    )  # nosec


def git_is_ancestor(ancestor: str, descendant: str) -> bool:
    return (
        git_completed("merge-base", "--is-ancestor", ancestor, descendant).returncode
        == 0
    )


def find_release_target_commit(version: str) -> str:
    release_commit = find_release_commit(version)
    head = git("rev-parse", "HEAD").strip()

    if release_commit == head:
        return release_commit

    if not git_is_ancestor(release_commit, head):
        raise SystemExit(
            f"Release commit {release_commit} for {version} is not reachable from HEAD."
        )

    first_parent_commits = git(
        "rev-list", "--first-parent", "--reverse", "HEAD"
    ).splitlines()
    for candidate in first_parent_commits:
        if git_is_ancestor(release_commit, candidate):
            return candidate

    return release_commit


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Release helpers for semver-based repos."
    )
    parser.add_argument(
        "--component",
        help="Optional component name from components.toml. Semver template releases are repo-wide, so this only validates the component exists.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("next-version")
    subparsers.add_parser("has-unreleased-changes")
    subparsers.add_parser("latest-release-tag")

    latest_parser = subparsers.add_parser("latest-changelog-version")
    latest_parser.add_argument(
        "--changelog", type=pathlib.Path, default=DEFAULT_CHANGELOG
    )

    notes_parser = subparsers.add_parser("extract-release-notes")
    notes_parser.add_argument("version")
    notes_parser.add_argument(
        "--changelog", type=pathlib.Path, default=DEFAULT_CHANGELOG
    )

    commit_parser = subparsers.add_parser("find-release-commit")
    commit_parser.add_argument("version")
    target_parser = subparsers.add_parser("find-release-target-commit")
    target_parser.add_argument("version")

    args = parser.parse_args()
    if args.component:
        get_component(args.component)

    if args.command == "next-version":
        print(next_release_version())
        return
    if args.command == "has-unreleased-changes":
        print("true" if has_unreleased_changes() else "false")
        return
    if args.command == "latest-release-tag":
        latest_tag = latest_release_tag()
        if latest_tag:
            print(latest_tag)
        return
    if args.command == "latest-changelog-version":
        print(latest_changelog_version(args.changelog))
        return
    if args.command == "extract-release-notes":
        print(extract_release_notes(args.version, args.changelog))
        return
    if args.command == "find-release-commit":
        print(find_release_commit(args.version))
        return
    if args.command == "find-release-target-commit":
        print(find_release_target_commit(args.version))
        return

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
