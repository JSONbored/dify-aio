from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scripts import generate_dify_template
from tests.conftest import REPO_ROOT
from tests.helpers import run_command


def test_validate_template_script_passes() -> None:
    result = run_command(
        [sys.executable, "scripts/validate-template.py"], cwd=REPO_ROOT
    )
    assert "dify-aio.xml parsed successfully" in result.stdout  # nosec B101


def test_validate_template_all_script_passes() -> None:
    result = run_command(
        [sys.executable, "scripts/validate-template.py", "--all"], cwd=REPO_ROOT
    )
    assert "dify-aio.xml parsed successfully" in result.stdout  # nosec B101


def test_template_generator_uses_latest_changelog_release_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "\n".join(
            [
                "# Changelog",
                "",
                "## [9.9.9-aio.1](https://github.com/JSONbored/dify-aio/releases/tag/9.9.9-aio.1) - 2026-04-30",
                "",
                "### Features",
                "- Release-specific template note",
            ]
        )
    )

    monkeypatch.setattr(generate_dify_template, "CHANGELOG_PATH", changelog)
    rendered = generate_dify_template.render_template([])

    assert "<Changes>### 2026-04-30&#xD;" in rendered  # nosec B101
    assert "- Release-specific template note</Changes>" in rendered  # nosec B101
    assert (
        "Scaffold Dify AIO from the current Unraid AIO template" not in rendered
    )  # nosec B101
