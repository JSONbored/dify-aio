from __future__ import annotations

import shlex

import pytest

from tests.helpers import (
    DockerRuntime,
    docker_exec,
    docker_network,
    reserve_host_port,
    sidecar_container,
    wait_for_container_command,
    wait_for_host_http,
)

pytestmark = pytest.mark.extended_integration

POSTGRES_IMAGE = "pgvector/pgvector:pg15"
QDRANT_IMAGE = "qdrant/qdrant:v1.13.5"
REDIS_IMAGE = "redis:7-alpine"
MAILPIT_IMAGE = "axllent/mailpit:latest"
MINIO_IMAGE = "minio/minio:latest"


def _configured_env(container_name: str, keys: list[str]) -> dict[str, str]:
    keys_arg = " ".join(shlex.quote(key) for key in keys)
    script = f"""
. /opt/dify-aio/lib/env.sh
load_generated_env
configure_dify_env
for key in {keys_arg}; do
  value="${{!key}}"
  printf '%s=%s\\n' "$key" "$value"
done
"""
    result = docker_exec(container_name, "bash -lc " + shlex.quote(script))
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, value = line.split("=", 1)
        values[key] = value
    return values


def _write_extra_env(container_name: str, values: dict[str, str]) -> None:
    payload = "".join(
        f"{key}={shlex.quote(value)}\n" for key, value in values.items()
    )
    docker_exec(
        container_name,
        f"printf %s {shlex.quote(payload)} > /appdata/config/extra.env",
    )


def test_external_postgres_and_redis_modes_boot_against_sidecars(
    runtime: DockerRuntime,
) -> None:
    postgres_password = "external-dify-postgres-password"  # nosec B105
    redis_password = "external-dify-redis-password"  # nosec B105

    with docker_network("dify-aio-ext") as network:
        with sidecar_container(
            "dify-postgres",
            POSTGRES_IMAGE,
            network=network,
            network_alias="postgres",
            env={
                "POSTGRES_USER": "dify",
                "POSTGRES_PASSWORD": postgres_password,
                "POSTGRES_DB": "dify",
            },
        ) as postgres:
            wait_for_container_command(
                postgres,
                "pg_isready -U dify -d dify >/dev/null",
                timeout=180,
            )
            docker_exec(postgres, "createdb -U dify dify_plugin")
            docker_exec(
                postgres,
                "psql -U dify -d dify -v ON_ERROR_STOP=1 "
                "-c 'CREATE EXTENSION IF NOT EXISTS vector;'",
            )

            with sidecar_container(
                "dify-redis",
                REDIS_IMAGE,
                network=network,
                network_alias="redis",
                command_args=[
                    "redis-server",
                    "--requirepass",
                    redis_password,
                    "--appendonly",
                    "no",
                ],
            ) as redis:
                wait_for_container_command(
                    redis,
                    "redis-cli -a external-dify-redis-password ping | grep -q PONG",
                    timeout=120,
                )

                with runtime.container(
                    network=network,
                    env_overrides={
                        "DIFY_USE_INTERNAL_POSTGRES": "false",
                        "DB_HOST": "postgres",
                        "DB_PORT": "5432",
                        "DB_USERNAME": "dify",
                        "DB_PASSWORD": postgres_password,
                        "DB_DATABASE": "dify",
                        "DB_PLUGIN_DATABASE": "dify_plugin",
                        "DIFY_USE_INTERNAL_REDIS": "false",
                        "REDIS_HOST": "redis",
                        "REDIS_PORT": "6379",
                        "REDIS_PASSWORD": redis_password,
                    },
                ) as container:
                    container.wait_for_http(path="/", timeout=900)
                    env = _configured_env(
                        container.name,
                        [
                            "DIFY_USE_INTERNAL_POSTGRES",
                            "DB_HOST",
                            "DB_DATABASE",
                            "DIFY_USE_INTERNAL_REDIS",
                            "REDIS_HOST",
                        ],
                    )
                    assert env == {  # nosec B101
                        "DIFY_USE_INTERNAL_POSTGRES": "false",
                        "DB_HOST": "postgres",
                        "DB_DATABASE": "dify",
                        "DIFY_USE_INTERNAL_REDIS": "false",
                        "REDIS_HOST": "redis",
                    }
                    container.exec(
                        "bash -lc '. /opt/dify-aio/lib/env.sh; load_generated_env; "
                        "configure_dify_env; PGPASSWORD=\"$DB_PASSWORD\" pg_isready "
                        "-h \"$DB_HOST\" -p \"$DB_PORT\" -U \"$DB_USERNAME\" "
                        "-d \"$DB_DATABASE\" >/dev/null'"
                    )
                    container.exec(
                        "bash -lc '. /opt/dify-aio/lib/env.sh; load_generated_env; "
                        "configure_dify_env; redis-cli -a \"$REDIS_PASSWORD\" "
                        "-h \"$REDIS_HOST\" -p \"$REDIS_PORT\" ping | grep -q PONG'"
                    )

                    logs = container.logs()
                    assert (  # nosec B101
                        "External PostgreSQL mode enabled; skipping bundled PostgreSQL initialization."
                        in logs
                    )
                    assert (  # nosec B101
                        "External Redis mode enabled; keeping bundled Redis idle."
                        in logs
                    )


def test_qdrant_vector_store_configuration_boots_against_sidecar(
    runtime: DockerRuntime,
) -> None:
    qdrant_port = reserve_host_port()

    with docker_network("dify-aio-qdrant") as network:
        with sidecar_container(
            "dify-qdrant",
            QDRANT_IMAGE,
            network=network,
            network_alias="qdrant",
            ports={qdrant_port: 6333},
        ):
            wait_for_host_http(f"http://127.0.0.1:{qdrant_port}/", timeout=180)

            with runtime.container(
                network=network,
                env_overrides={
                    "VECTOR_STORE": "qdrant",
                    "QDRANT_URL": "http://qdrant:6333",
                    "QDRANT_CLIENT_TIMEOUT": "7",
                    "QDRANT_GRPC_ENABLED": "false",
                },
            ) as container:
                container.wait_for_http(path="/", timeout=900)
                container.exec("curl -fsS http://qdrant:6333/ >/dev/null")

                env = _configured_env(
                    container.name,
                    [
                        "VECTOR_STORE",
                        "QDRANT_URL",
                        "QDRANT_CLIENT_TIMEOUT",
                        "QDRANT_GRPC_ENABLED",
                    ],
                )
                assert env == {  # nosec B101
                    "VECTOR_STORE": "qdrant",
                    "QDRANT_URL": "http://qdrant:6333",
                    "QDRANT_CLIENT_TIMEOUT": "7",
                    "QDRANT_GRPC_ENABLED": "false",
                }


def test_s3_storage_and_smtp_configuration_boot_against_sidecars(
    runtime: DockerRuntime,
) -> None:
    minio_http_port = reserve_host_port()
    mailpit_http_port = reserve_host_port()

    with docker_network("dify-aio-storage-mail") as network:
        with sidecar_container(
            "dify-minio",
            MINIO_IMAGE,
            network=network,
            network_alias="minio",
            ports={minio_http_port: 9000},
            env={
                "MINIO_ROOT_USER": "minioadmin",
                "MINIO_ROOT_PASSWORD": "minioadmin",
            },
            command_args=[
                "server",
                "/data",
                "--address",
                ":9000",
                "--console-address",
                ":9001",
            ],
        ):
            wait_for_host_http(
                f"http://127.0.0.1:{minio_http_port}/minio/health/ready",
                timeout=180,
            )

            with sidecar_container(
                "dify-mailpit",
                MAILPIT_IMAGE,
                network=network,
                network_alias="mailpit",
                ports={mailpit_http_port: 8025},
            ):
                wait_for_host_http(
                    f"http://127.0.0.1:{mailpit_http_port}/",
                    timeout=120,
                )

                with runtime.container(
                    network=network,
                    env_overrides={
                        "STORAGE_TYPE": "s3",
                        "S3_ENDPOINT": "http://minio:9000",
                        "S3_REGION": "us-east-1",
                        "S3_BUCKET_NAME": "dify-files",
                        "S3_ACCESS_KEY": "minioadmin",
                        "S3_SECRET_KEY": "minioadmin",
                        "S3_ADDRESS_STYLE": "path",
                        "MAIL_TYPE": "smtp",
                        "MAIL_DEFAULT_SEND_FROM": "noreply@example.test",
                        "SMTP_SERVER": "mailpit",
                        "SMTP_PORT": "1025",
                        "SMTP_USE_TLS": "false",
                        "SMTP_OPPORTUNISTIC_TLS": "false",
                    },
                ) as container:
                    container.wait_for_http(path="/", timeout=900)
                    container.exec(
                        "curl -fsS http://minio:9000/minio/health/ready >/dev/null"
                    )
                    container.exec("bash -lc 'exec 3<>/dev/tcp/mailpit/1025'")

                    env = _configured_env(
                        container.name,
                        [
                            "STORAGE_TYPE",
                            "S3_ENDPOINT",
                            "S3_BUCKET_NAME",
                            "S3_ADDRESS_STYLE",
                            "MAIL_TYPE",
                            "SMTP_SERVER",
                            "SMTP_PORT",
                            "SMTP_USE_TLS",
                            "SMTP_OPPORTUNISTIC_TLS",
                        ],
                    )
                    assert env == {  # nosec B101
                        "STORAGE_TYPE": "s3",
                        "S3_ENDPOINT": "http://minio:9000",
                        "S3_BUCKET_NAME": "dify-files",
                        "S3_ADDRESS_STYLE": "path",
                        "MAIL_TYPE": "smtp",
                        "SMTP_SERVER": "mailpit",
                        "SMTP_PORT": "1025",
                        "SMTP_USE_TLS": "false",
                        "SMTP_OPPORTUNISTIC_TLS": "false",
                    }


def test_extra_env_supports_common_optional_provider_surface(
    runtime: DockerRuntime,
) -> None:
    provider_env = {
        "STORAGE_TYPE": "s3",
        "S3_ENDPOINT": "http://minio:9000",
        "S3_REGION": "us-east-1",
        "S3_BUCKET_NAME": "dify-files",
        "S3_ACCESS_KEY": "dify-minio",
        "S3_SECRET_KEY": "dify-minio-secret",
        "S3_ADDRESS_STYLE": "path",
        "MAIL_TYPE": "smtp",
        "MAIL_DEFAULT_SEND_FROM": "noreply@example.test",
        "SMTP_SERVER": "mailpit",
        "SMTP_PORT": "1025",
        "SMTP_USE_TLS": "false",
        "SMTP_OPPORTUNISTIC_TLS": "false",
        "PLUGIN_STORAGE_TYPE": "s3",
        "PLUGIN_STORAGE_OSS_BUCKET": "dify-plugin-files",
        "PLUGIN_S3_ENDPOINT": "http://minio:9000",
        "PLUGIN_S3_USE_PATH_STYLE": "true",
        "PLUGIN_AWS_ACCESS_KEY": "dify-plugin-minio",
        "PLUGIN_AWS_SECRET_KEY": "dify-plugin-minio-secret",
        "PLUGIN_AWS_REGION": "us-east-1",
        "VECTOR_STORE": "weaviate",
        "WEAVIATE_ENDPOINT": "http://weaviate:8080",
        "WEAVIATE_GRPC_ENDPOINT": "weaviate:50051",
        "MILVUS_URI": "http://milvus:19530",
        "CHROMA_HOST": "chroma",
        "CHROMA_PORT": "8000",
        "OPENSEARCH_HOST": "opensearch",
        "OPENSEARCH_PORT": "9200",
        "ELASTICSEARCH_HOST": "elasticsearch",
        "ELASTICSEARCH_PORT": "9200",
        "UNSTRUCTURED_API_URL": "http://unstructured:8000/general/v0/general",
        "NOTION_INTEGRATION_TYPE": "internal",
        "NOTION_INTERNAL_SECRET": "notion-internal-secret",
        "ENABLE_OTEL": "true",
        "OTLP_TRACE_ENDPOINT": "http://otel-collector:4318/v1/traces",
        "OTEL_EXPORTER_TYPE": "otlp",
        "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
        "SENTRY_DSN": "https://public@example.test/1",
        "PLUGIN_SENTRY_ENABLED": "true",
        "PLUGIN_SENTRY_DSN": "https://plugin@example.test/1",
    }

    with runtime.container() as container:
        container.wait_for_http(path="/", timeout=900)
        _write_extra_env(container.name, provider_env)
        assert _configured_env(container.name, list(provider_env)) == provider_env  # nosec B101
