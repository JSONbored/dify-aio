from __future__ import annotations

import shlex
import time
from collections import defaultdict

import pytest

from tests.helpers import DockerRuntime, create_docker_volume, remove_docker_volume

pytestmark = pytest.mark.integration

LISTENERS_SCRIPT = r"""
python3 - <<'PY'
import socket

def parse_ipv4(raw):
    if raw == "00000000":
        return "0.0.0.0"
    return socket.inet_ntoa(bytes.fromhex(raw)[::-1])

def parse_ipv6(raw):
    if raw == "0" * 32:
        return "::"
    if raw == "00000000000000000000000001000000":
        return "::1"
    return raw

for path, parser in (("/proc/net/tcp", parse_ipv4), ("/proc/net/tcp6", parse_ipv6)):
    with open(path) as handle:
        for line in handle.read().splitlines()[1:]:
            parts = line.split()
            if parts[3] != "0A":
                continue
            raw_host, raw_port = parts[1].rsplit(":", 1)
            print(f"{int(raw_port, 16)} {parser(raw_host)}")
PY
"""


def _listeners_by_port(container) -> dict[int, set[str]]:
    result = container.exec(LISTENERS_SCRIPT)
    listeners: dict[int, set[str]] = defaultdict(set)
    for line in result.stdout.splitlines():
        port, host = line.split(" ", 1)
        listeners[int(port)].add(host)
    return listeners


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
            'configure_dify_env; PGPASSWORD="$DB_PASSWORD" pg_isready '
            '-h 127.0.0.1 -p "$DB_PORT" -U "$DB_USERNAME" >/dev/null\''
        )
        container.exec(
            "bash -lc '. /opt/dify-aio/lib/env.sh; load_generated_env; "
            'configure_dify_env; redis-cli -a "$REDIS_PASSWORD" '
            '-h 127.0.0.1 -p "$REDIS_PORT" ping | grep -q PONG\''
        )

        container.restart()
        container.wait_for_http(path="/", timeout=900)

        secret_after = container.exec(
            "awk -F= '/^SECRET_KEY=/{print $2}' /appdata/config/generated.env"
        ).stdout.strip()
        assert secret_after == secret_before  # nosec B101


def test_plugin_daemon_runtime_can_resolve_uv_and_python(
    runtime: DockerRuntime,
) -> None:
    with runtime.container() as container:
        container.wait_for_http(path="/", timeout=900)
        result = container.exec(
            'pid="$(for proc in /proc/[0-9]*; do '
            "cmd=\"$(tr '\\000' ' ' < \"$proc/cmdline\" 2>/dev/null || true)\"; "
            "case \"$cmd\" in '/opt/dify-plugin-daemon/main '*) "
            "printf '%s\\n' \"${proc##*/}\"; break;; esac; "
            'done)"; '
            'if [ -z "$pid" ]; then exit 1; fi; '
            "tr '\\000' '\\n' < \"/proc/${pid}/environ\" "
            "| awk -F= '/^(PATH|UV_PATH|PYTHON_INTERPRETER_PATH|"
            "PYTHON_ENV_INIT_TIMEOUT|PLUGIN_WORKING_PATH|UV_CACHE_DIR)=/{print}'"
        )
        daemon_env = dict(
            line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
        )

        assert daemon_env["UV_PATH"] == "/usr/local/bin/uv"  # nosec B101
        assert (  # nosec B101
            daemon_env["PYTHON_INTERPRETER_PATH"] == "/usr/local/bin/python3.12"
        )
        assert daemon_env["PYTHON_ENV_INIT_TIMEOUT"] == "120"  # nosec B101
        assert (  # nosec B101
            daemon_env["PLUGIN_WORKING_PATH"] == "/appdata/plugin_daemon/cwd"
        )
        assert (  # nosec B101
            daemon_env["UV_CACHE_DIR"] == "/appdata/plugin_daemon/cwd/.uv-cache"
        )
        assert "/usr/local/bin" in daemon_env["PATH"].split(":")  # nosec B101

        uv_path = shlex.quote(daemon_env["UV_PATH"])
        python_path = shlex.quote(daemon_env["PYTHON_INTERPRETER_PATH"])
        container.exec(f"{uv_path} --version >/dev/null")
        container.exec(
            f"{python_path} -c "
            "'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'"
        )
        container.exec("test -d /appdata/plugin_daemon/cwd/.uv-cache")


def test_generated_secret_files_are_owner_only(runtime: DockerRuntime) -> None:
    with runtime.container() as container:
        container.wait_for_http(path="/", timeout=900)
        result = container.exec(
            "stat -c '%a %U:%G %n' "
            "/appdata/config "
            "/appdata/config/generated.env "
            "/appdata/config/extra.env"
        )

        assert result.stdout.splitlines() == [  # nosec B101
            "700 root:root /appdata/config",
            "600 root:root /appdata/config/generated.env",
            "600 root:root /appdata/config/extra.env",
        ]


def test_internal_listeners_default_to_localhost_where_supported(
    runtime: DockerRuntime,
) -> None:
    with runtime.container() as container:
        container.wait_for_http(path="/", timeout=900)
        listeners = _listeners_by_port(container)
        wildcard_hosts = {"0.0.0.0", "::"}  # nosec B104 - asserted against below.

        assert listeners[8080] & wildcard_hosts  # nosec B101
        for port in (3000, 3128, 5001, 5003, 5432, 6379, 8195):
            if port in listeners:
                assert not (  # nosec B101
                    listeners[port] & wildcard_hosts
                ), f"port {port} should not listen on all interfaces: {listeners[port]}"


def test_sandbox_can_be_disabled_for_installations_without_code_execution(
    runtime: DockerRuntime,
) -> None:
    with runtime.container(env_overrides={"DIFY_ENABLE_SANDBOX": "false"}) as container:
        container.wait_for_http(path="/", timeout=900)

        assert "Dify sandbox disabled; code execution features will not work." in (
            container.logs()
        )  # nosec B101
        sandbox_health = container.exec(
            "curl -fsS http://127.0.0.1:8194/health >/dev/null",
            check=False,
        )
        assert sandbox_health.returncode != 0  # nosec B101
        container.exec("curl -fsS http://127.0.0.1:5001/health >/dev/null")


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


def test_explicit_secret_overrides_generated_env_after_first_boot(
    runtime: DockerRuntime,
) -> None:
    appdata_volume = create_docker_volume("dify-aio-pytest-secret-override")
    try:
        with runtime.container(appdata_volume=appdata_volume) as container:
            container.wait_for_http(path="/", timeout=900)
            generated_secret = container.exec(
                "awk -F= '/^SECRET_KEY=/{print $2}' /appdata/config/generated.env"
            ).stdout.strip()
            assert generated_secret  # nosec B101

        explicit_values = {
            "DB_PASSWORD": "explicit-db-password",  # nosec B105 - local test fixture.
            "PLUGIN_DAEMON_KEY": "explicit-plugin-daemon-key",
            "PLUGIN_DIFY_INNER_API_KEY": "explicit-plugin-inner-key",
            "REDIS_PASSWORD": "explicit-redis-password",  # nosec B105
            "SANDBOX_API_KEY": "explicit-sandbox-key",
            "SECRET_KEY": "explicit-dify-secret-value",  # nosec B105
        }
        with runtime.container(
            appdata_volume=appdata_volume,
            env_overrides=explicit_values,
        ) as container:
            container.wait_for_http(path="/", timeout=900)
            result = container.exec(
                "bash -lc '. /opt/dify-aio/lib/env.sh; load_generated_env; "
                'configure_dify_env; printf "%s\\n%s\\n%s\\n%s\\n%s\\n%s\\n" '
                '"$SECRET_KEY" "$DB_PASSWORD" "$REDIS_PASSWORD" '
                '"$SANDBOX_API_KEY" "$PLUGIN_DAEMON_KEY" '
                '"$PLUGIN_DIFY_INNER_API_KEY"\''
            )
            assert result.stdout.splitlines() == [  # nosec B101
                explicit_values["SECRET_KEY"],
                explicit_values["DB_PASSWORD"],
                explicit_values["REDIS_PASSWORD"],
                explicit_values["SANDBOX_API_KEY"],
                explicit_values["PLUGIN_DAEMON_KEY"],
                explicit_values["PLUGIN_DIFY_INNER_API_KEY"],
            ]

            generated_secret_after = container.exec(
                "awk -F= '/^SECRET_KEY=/{print $2}' /appdata/config/generated.env"
            ).stdout.strip()
            assert generated_secret_after == generated_secret  # nosec B101
    finally:
        remove_docker_volume(appdata_volume)


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
            'configure_dify_env; printf "%s\\n%s\\n%s\\n%s\\n" '
            '"$CODE_EXECUTION_API_KEY" "$SANDBOX_API_KEY" "$LOG_FILE" "$TRIGGER_URL"\''
        )
        code_key, sandbox_key, log_file, trigger_url = result.stdout.splitlines()
        assert code_key == sandbox_key  # nosec B101
        assert log_file == "/appdata/logs/server.log"  # nosec B101
        assert trigger_url == "http://localhost"  # nosec B101


def test_blank_check_update_url_is_preserved_for_privacy(
    runtime: DockerRuntime,
) -> None:
    with runtime.container(env_overrides={"CHECK_UPDATE_URL": ""}) as container:
        container.wait_for_http(path="/", timeout=900)
        result = container.exec(
            "bash -lc '. /opt/dify-aio/lib/env.sh; load_generated_env; "
            'configure_dify_env; printf "<%s>\\n" "$CHECK_UPDATE_URL"\''
        )
        assert result.stdout.strip() == "<>"  # nosec B101


def test_internal_postgres_rejects_unsafe_database_identifiers(
    runtime: DockerRuntime,
) -> None:
    with runtime.container(
        env_overrides={"DB_USERNAME": "dify;bad"},
    ) as container:
        deadline = time.time() + 120
        logs = ""
        while time.time() < deadline:
            logs = container.logs()
            if "Invalid bundled PostgreSQL user" in logs:
                break
            if not container.is_running():
                break
            time.sleep(1)

        assert "Invalid bundled PostgreSQL user" in logs  # nosec B101
        health = container.exec(
            "curl -fsS http://127.0.0.1:5001/health >/dev/null",
            check=False,
        )
        assert health.returncode != 0  # nosec B101


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
            'configure_dify_env; printf "%s\\n%s\\n%s\\n%s\\n%s\\n%s\\n%s\\n" '
            '"$CONSOLE_WEB_URL" "$CONSOLE_API_URL" "$SERVICE_API_URL" '
            '"$TRIGGER_URL" "$APP_WEB_URL" "$FILES_URL" "$NEXT_PUBLIC_SOCKET_URL"\''
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
            'configure_dify_env; printf "%s\\n" '
            '"$SANDBOX_EXPIRED_RECORDS_CLEAN_TASK_LOCK_TTL"\''
        )
        assert result.stdout.strip() == "12345"  # nosec B101


def test_extra_env_file_is_parsed_without_shell_execution(
    runtime: DockerRuntime,
) -> None:
    with runtime.container() as container:
        container.wait_for_http(path="/", timeout=900)
        container.exec(
            "cat > /appdata/config/extra.env <<'EOF'\n"
            "SAFE_EXTRA_TEST=from-extra\n"
            "QUOTED_EXTRA_TEST='quoted value'\n"
            "MALICIOUS_EXTRA_TEST=$(touch /appdata/config/extra-env-executed)\n"
            "EOF"
        )
        result = container.exec(
            "bash -lc '. /opt/dify-aio/lib/env.sh; load_generated_env; "
            'configure_dify_env; printf "%s\\n%s\\n%s\\n" '
            '"$SAFE_EXTRA_TEST" "$QUOTED_EXTRA_TEST" "$MALICIOUS_EXTRA_TEST"\''
        )

        assert result.stdout.splitlines() == [  # nosec B101
            "from-extra",
            "quoted value",
            "$(touch /appdata/config/extra-env-executed)",
        ]
        assert not container.path_exists(  # nosec B101
            "/appdata/config/extra-env-executed"
        )
