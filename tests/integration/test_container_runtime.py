from __future__ import annotations

import pytest

from tests.helpers import DockerRuntime

pytestmark = pytest.mark.integration


def test_happy_path_boot_and_restart_persists_generated_env(
    runtime: DockerRuntime,
) -> None:
    with runtime.container() as container:
        container.wait_for_http(path="/", timeout=900)
        assert container.path_exists("/appdata/config/generated.env")  # nosec B101
        assert container.path_exists("/appdata/config/extra.env")  # nosec B101

        expected_generated_keys = {
            "DB_PASSWORD",
            "PLUGIN_DAEMON_KEY",
            "PLUGIN_DIFY_INNER_API_KEY",
            "REDIS_PASSWORD",
            "SANDBOX_API_KEY",
            "SECRET_KEY",
        }
        generated_keys = set(
            container.exec(
                "awk -F= '/^[A-Z0-9_]+=/{print $1}' /appdata/config/generated.env"
            ).stdout.splitlines()
        )
        assert expected_generated_keys <= generated_keys  # nosec B101

        secret_before = container.exec(
            "awk -F= '/^SECRET_KEY=/{print $2}' /appdata/config/generated.env"
        ).stdout.strip()
        assert secret_before  # nosec B101

        container.exec("curl -fsS http://127.0.0.1:5001/health >/dev/null")
        container.exec("curl -fsS http://127.0.0.1:8194/health >/dev/null")
        container.exec(
            "bash -lc '. /opt/dify-aio/lib/env.sh; load_generated_env; "
            "configure_dify_env; PGPASSWORD=\"$DB_PASSWORD\" pg_isready "
            "-h 127.0.0.1 -p \"$DB_PORT\" -U \"$DB_USERNAME\" >/dev/null'"
        )
        container.exec(
            "bash -lc '. /opt/dify-aio/lib/env.sh; load_generated_env; "
            "configure_dify_env; redis-cli -a \"$REDIS_PASSWORD\" "
            "-h 127.0.0.1 -p \"$REDIS_PORT\" ping | grep -q PONG'"
        )

        container.restart()
        container.wait_for_http(path="/", timeout=900)

        secret_after = container.exec(
            "awk -F= '/^SECRET_KEY=/{print $2}' /appdata/config/generated.env"
        ).stdout.strip()
        assert secret_after == secret_before  # nosec B101


def test_explicit_secret_override_skips_generated_secret(
    runtime: DockerRuntime,
) -> None:
    with runtime.container(
        env_overrides={"SECRET_KEY": "explicit-dify-secret-value"}  # nosec B105
    ) as container:
        container.wait_for_http(path="/", timeout=900)
        result = container.exec(
            "grep '^SECRET_KEY=' /appdata/config/generated.env || true"
        )
        assert result.stdout.strip() == ""  # nosec B101


def test_blank_unraid_variables_do_not_override_aio_defaults(
    runtime: DockerRuntime,
) -> None:
    with runtime.container(
        env_overrides={
            "CODE_EXECUTION_API_KEY": "",
            "LOG_FILE": "",
            "NEXT_PUBLIC_SOCKET_URL": "",
            "TRIGGER_URL": "",
        }
    ) as container:
        container.wait_for_http(path="/", timeout=900)
        result = container.exec(
            "bash -lc '. /opt/dify-aio/lib/env.sh; load_generated_env; "
            "configure_dify_env; printf \"%s\\n%s\\n%s\\n%s\\n\" "
            "\"$CODE_EXECUTION_API_KEY\" \"$SANDBOX_API_KEY\" \"$LOG_FILE\" \"$TRIGGER_URL\"'"
        )
        code_key, sandbox_key, log_file, trigger_url = result.stdout.splitlines()
        assert code_key == sandbox_key  # nosec B101
        assert log_file == "/appdata/logs/server.log"  # nosec B101
        assert trigger_url == "http://localhost"  # nosec B101


def test_public_url_seeds_dify_external_urls(runtime: DockerRuntime) -> None:
    public_url = "https://dify.example.test"
    with runtime.container(
        env_overrides={
            "DIFY_AIO_PUBLIC_URL": public_url,
            "NEXT_PUBLIC_SOCKET_URL": "",
        }
    ) as container:
        container.wait_for_http(path="/", timeout=900)
        result = container.exec(
            "bash -lc '. /opt/dify-aio/lib/env.sh; load_generated_env; "
            "configure_dify_env; printf \"%s\\n%s\\n%s\\n%s\\n%s\\n%s\\n%s\\n\" "
            "\"$CONSOLE_WEB_URL\" \"$CONSOLE_API_URL\" \"$SERVICE_API_URL\" "
            "\"$TRIGGER_URL\" \"$APP_WEB_URL\" \"$FILES_URL\" \"$NEXT_PUBLIC_SOCKET_URL\"'"
        )
        values = result.stdout.splitlines()
        assert values[:6] == [public_url] * 6  # nosec B101
        assert values[6] == "wss://dify.example.test"  # nosec B101


def test_extra_env_file_supports_non_template_upstream_variables(
    runtime: DockerRuntime,
) -> None:
    with runtime.container() as container:
        container.wait_for_http(path="/", timeout=900)
        container.exec(
            "printf '%s\\n' "
            "'SANDBOX_EXPIRED_RECORDS_CLEAN_TASK_LOCK_TTL=12345' "
            "> /appdata/config/extra.env"
        )
        result = container.exec(
            "bash -lc '. /opt/dify-aio/lib/env.sh; load_generated_env; "
            "configure_dify_env; printf \"%s\\n\" "
            "\"$SANDBOX_EXPIRED_RECORDS_CLEAN_TASK_LOCK_TTL\"'"
        )
        assert result.stdout.strip() == "12345"  # nosec B101
