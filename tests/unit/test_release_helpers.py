from __future__ import annotations

from subprocess import (  # nosec B404 - tests construct return objects only
    CompletedProcess,
)

import pytest

from scripts import release


def test_find_release_target_commit_returns_squash_release_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_git(*args: str) -> str:
        if args == ("log", "--format=%H\t%s", "HEAD"):
            return "release-sha\tchore(release): v1.2.3"
        if args == ("rev-parse", "HEAD"):
            return "release-sha"
        raise AssertionError(f"unexpected git args: {args}")

    monkeypatch.setattr(release, "git", fake_git)

    assert release.find_release_target_commit("v1.2.3") == "release-sha"  # nosec B101


def test_find_release_target_commit_returns_merge_commit_after_intervening_main_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_git(*args: str) -> str:
        if args == ("log", "--format=%H\t%s", "HEAD"):
            return "\n".join(
                [
                    "later-sha\tfix(release): later workflow fix",
                    "merge-sha\tMerge pull request #15 from JSONbored/release/v1.2.3",
                    "main-sha\tfix(ci): intervening main change",
                    "release-sha\tchore(release): v1.2.3",
                ]
            )
        if args == ("rev-parse", "HEAD"):
            return "later-sha"
        if args == ("rev-list", "--first-parent", "--reverse", "HEAD"):
            return "main-sha\nmerge-sha\nlater-sha"
        raise AssertionError(f"unexpected git args: {args}")

    def fake_git_completed(*args: str) -> CompletedProcess[str]:
        ancestor_pairs = {
            ("release-sha", "later-sha"),
            ("release-sha", "merge-sha"),
        }
        if args[:2] == ("merge-base", "--is-ancestor"):
            return CompletedProcess(
                args=args,
                returncode=0 if (args[2], args[3]) in ancestor_pairs else 1,
            )
        raise AssertionError(f"unexpected git_completed args: {args}")

    monkeypatch.setattr(release, "git", fake_git)
    monkeypatch.setattr(release, "git_completed", fake_git_completed)

    assert release.find_release_target_commit("v1.2.3") == "merge-sha"  # nosec B101
