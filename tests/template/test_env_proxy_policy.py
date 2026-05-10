from __future__ import annotations

import os
import subprocess  # nosec B404 - tests execute trusted local shell snippets.
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROXY_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)


def test_configure_env_strips_inherited_generic_proxy_variables() -> None:
    output = _configure_env(
        {
            "HTTP_PROXY": "http://proxy.example:8080",
            "HTTPS_PROXY": "http://proxy.example:8080",
            "ALL_PROXY": "http://proxy.example:8080",
            "NO_PROXY": "localhost,fd07:b51a:cc66:f0::/64",
            "http_proxy": "http://proxy.example:8080",
            "https_proxy": "http://proxy.example:8080",
            "all_proxy": "http://proxy.example:8080",
            "no_proxy": "localhost,fd07:b51a:cc66:f0::/64",
        }
    )

    lines = output.splitlines()
    for key in PROXY_KEYS:
        assert not any(line.startswith(f"{key}=") for line in lines)  # nosec B101
    assert "SSRF_PROXY_HTTP_URL=http://127.0.0.1:3128" in output  # nosec B101
    assert "SANDBOX_HTTP_PROXY=http://127.0.0.1:3128" in output  # nosec B101


def test_configure_env_can_explicitly_keep_generic_proxy_variables() -> None:
    output = _configure_env(
        {
            "DIFY_AIO_TRUST_INHERITED_PROXY_ENV": "true",
            "HTTP_PROXY": "http://proxy.example:8080",
            "NO_PROXY": "localhost,127.0.0.1",
        }
    )

    assert "HTTP_PROXY=http://proxy.example:8080" in output  # nosec B101
    assert "NO_PROXY=localhost,127.0.0.1" in output  # nosec B101


def _configure_env(extra_env: dict[str, str]) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        generated_env = tmp_path / "generated.env"
        extra_env_file = tmp_path / "extra.env"
        generated_env.write_text("")
        extra_env_file.write_text("")
        env = {
            "PATH": os.environ["PATH"],
            "SECRET_KEY": "test-secret",
            "DB_PASSWORD": "test-db-password",
            "REDIS_PASSWORD": "test-redis-password",
            "SANDBOX_API_KEY": "test-sandbox-key",
            "PLUGIN_DAEMON_KEY": "test-plugin-daemon-key",
            "PLUGIN_DIFY_INNER_API_KEY": "test-plugin-inner-key",
            "DIFY_AIO_EXTRA_ENV_FILE": str(extra_env_file),
            **extra_env,
        }
        command = f"""
set -euo pipefail
. {ROOT / "rootfs/opt/dify-aio/lib/env.sh"}
AIO_ENV_FILE={generated_env}
configure_dify_env
for key in {" ".join(PROXY_KEYS)}; do
    if [[ -v "${{key}}" ]]; then
        printf '%s=%s\\n' "${{key}}" "${{!key}}"
    fi
done
printf 'SSRF_PROXY_HTTP_URL=%s\\n' "${{SSRF_PROXY_HTTP_URL}}"
printf 'SANDBOX_HTTP_PROXY=%s\\n' "${{SANDBOX_HTTP_PROXY}}"
"""
        result = subprocess.run(  # nosec B603 - static shell snippet for env probing.
            ["bash", "-lc", command],
            check=True,
            env=env,
            text=True,
            capture_output=True,
        )
        return result.stdout
