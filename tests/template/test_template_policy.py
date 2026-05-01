from __future__ import annotations

import json
import re
from pathlib import Path

from defusedxml import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "Dockerfile"

SECRET_KEYWORDS = (
    "ACCESS_KEY",
    "ACCOUNT_KEY",
    "ALLOWED_KEYS",
    "API_KEY",
    "AUTH_TOKEN",
    "CONNECTION_STRING",
    "CLIENT_SECRET",
    "CREDENTIAL",
    "DSN",
    "KEY_ID",
    "PASSWORD",
    "PRIVATE_KEY",
    "SERVICE_ACCOUNT",
    "SECRET",
    "TOKEN",
)

PLACEHOLDER_DEFAULT_MARKERS = (
    "<your",
    "example.com",
    "example.test",
    "xxx-",
    "xxx.",
    "xxx_",
    "your-",
    "your_",
)

NON_SECRET_TARGETS = {
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "CHANGE_EMAIL_TOKEN_EXPIRY_MINUTES",
    "CODE_GENERATION_MAX_TOKENS",
    "EMAIL_REGISTER_TOKEN_EXPIRY_MINUTES",
    "HOLOGRES_TOKENIZER",
    "INDEXING_MAX_SEGMENTATION_TOKENS_LENGTH",
    "OWNER_TRANSFER_TOKEN_EXPIRY_MINUTES",
    "PROMPT_GENERATION_MAX_TOKENS",
    "REFRESH_TOKEN_EXPIRE_DAYS",
    "RESET_PASSWORD_TOKEN_EXPIRY_MINUTES",
    "WEAVIATE_TOKENIZATION",
}


def _template_path() -> Path:
    candidates = sorted(ROOT.glob("*.xml"))
    assert candidates, "repository must include an Unraid XML template"  # nosec B101
    return candidates[0]


def _template_root() -> ET.Element:
    return ET.parse(_template_path()).getroot()


def _dockerfile_text() -> str:
    return DOCKERFILE.read_text()


def _dockerfile_volumes() -> set[str]:
    volumes: set[str] = set()
    for match in re.finditer(r"(?m)^VOLUME\s+(\[[^\]]+\])", _dockerfile_text()):
        volumes.update(json.loads(match.group(1)))
    return volumes


def _exposed_ports() -> set[str]:
    ports: set[str] = set()
    for line in _dockerfile_text().splitlines():
        if not line.startswith("EXPOSE "):
            continue
        for token in line.split()[1:]:
            ports.add(token.split("/", 1)[0])
    return ports


def _arg_defaults() -> dict[str, str]:
    defaults: dict[str, str] = {}
    for line in _dockerfile_text().splitlines():
        if not line.startswith("ARG ") or "=" not in line:
            continue
        name, value = line.removeprefix("ARG ").split("=", 1)
        defaults[name] = value
    return defaults


def _config_elements() -> list[ET.Element]:
    return list(_template_root().findall("Config"))


def _configs_by_target() -> dict[str, ET.Element]:
    return {
        config.attrib["Target"]: config
        for config in _config_elements()
        if config.attrib.get("Target")
    }


def test_unraid_metadata_contract_is_complete_and_unprivileged() -> None:
    root = _template_root()

    assert root.findtext("Privileged") == "false"  # nosec B101
    for tag in (
        "Name",
        "Repository",
        "Registry",
        "ReadMe",
        "Support",
        "Project",
        "TemplateURL",
        "Icon",
        "Category",
        "WebUI",
    ):
        value = root.findtext(tag)
        assert value and value.strip(), f"{tag} must be populated"  # nosec B101
    assert (
        _config_elements()
    ), "template must expose configurable settings"  # nosec B101
    assert root.findtext("Repository") == "jsonbored/dify-aio:latest"  # nosec B101
    assert (  # nosec B101
        root.findtext("Registry") == "https://hub.docker.com/r/jsonbored/dify-aio"
    )
    assert root.findtext("Category") == "AI Productivity Tools:Utilities"  # nosec B101
    assert (
        root.findtext("ReadMe") == "https://github.com/JSONbored/dify-aio#readme"
    )  # nosec B101


def test_overview_includes_beginner_and_power_user_guidance() -> None:
    overview = _template_root().findtext("Overview") or ""

    expected_fragments = [
        "[b]All-In-One Unraid Edition[/b]",
        "[b]Quick Install (Beginners)[/b]",
        "[b]Power Users (Advanced View)[/b]",
        "[b]Important Notes[/b]",
        "[code]Web UI Port[/code]",
        "[code]Public URL[/code]",
        "[code]/appdata/config/generated.env[/code]",
        "[code]/appdata/config/extra.env[/code]",
        "[code]CHECK_UPDATE_URL[/code]",
    ]
    for fragment in expected_fragments:
        assert fragment in overview  # nosec B101


def test_only_install_critical_fields_are_required() -> None:
    required_configs = {
        config.get("Target"): config
        for config in _config_elements()
        if config.get("Required") == "true"
    }

    assert set(required_configs) == {"8080", "/appdata"}  # nosec B101
    for config in required_configs.values():
        assert config.get("Display") == "always"  # nosec B101


def test_secret_like_template_variables_are_masked() -> None:
    for config in _config_elements():
        name = config.get("Name") or ""
        target = config.get("Target") or ""
        default = config.get("Default") or ""
        if target in NON_SECRET_TARGETS:
            continue
        if (
            target.endswith("_PATH")
            or target.endswith("_ENABLED")
            or target.startswith(("MAX_", "MIN_"))
            or name.upper().endswith(" PATH")
            or set(default.split("|")) == {"false", "true"}
        ):
            continue
        haystack = " ".join(filter(None, (name, target))).upper()
        if any(keyword in haystack for keyword in SECRET_KEYWORDS):
            assert (
                config.get("Mask") == "true"
            ), (  # nosec B101
                f"{config.get('Name') or config.get('Target')} should be masked"
            )


def test_known_non_secret_token_fields_are_not_masked() -> None:
    configs = _configs_by_target()

    expected = {
        "ACCESS_TOKEN_EXPIRE_MINUTES": "60",  # nosec B105 - duration, not a secret.
        "CHANGE_EMAIL_TOKEN_EXPIRY_MINUTES": "5",
        "CODE_GENERATION_MAX_TOKENS": "1024",
        "EMAIL_REGISTER_TOKEN_EXPIRY_MINUTES": "5",
        "HOLOGRES_TOKENIZER": "jieba",
        "INDEXING_MAX_SEGMENTATION_TOKENS_LENGTH": "4000",
        "OWNER_TRANSFER_TOKEN_EXPIRY_MINUTES": "5",
        "PROMPT_GENERATION_MAX_TOKENS": "512",
        "REFRESH_TOKEN_EXPIRE_DAYS": "30",  # nosec B105 - duration, not a secret.
        "RESET_PASSWORD_TOKEN_EXPIRY_MINUTES": "5",
        "WEAVIATE_TOKENIZATION": "word",
    }
    for target, selected in expected.items():
        config = configs[target]
        assert config.get("Mask") == "false"  # nosec B101
        assert config.get("Default") == selected  # nosec B101
        assert (config.text or "").strip() == selected  # nosec B101

    for target in ("MILVUS_TOKEN", "UPSTASH_VECTOR_TOKEN"):
        assert configs[target].get("Mask") == "true"  # nosec B101


def test_preconfigured_template_options_are_pipe_delimited_and_selected() -> None:
    configs = _configs_by_target()
    expected_options = {
        "DEPLOY_ENV": ("PRODUCTION|TESTING", "PRODUCTION"),
        "DB_TYPE": ("postgresql|mysql|oceanbase|seekdb", "postgresql"),
        "LOG_LEVEL": ("DEBUG|INFO|WARNING|ERROR|CRITICAL", "INFO"),
        "LOG_OUTPUT_FORMAT": ("text|json", "text"),
        "REDIS_SSL_CERT_REQS": (
            "CERT_NONE|CERT_OPTIONAL|CERT_REQUIRED",
            "CERT_NONE",
        ),
        "MAIL_TYPE": ("resend|smtp|sendgrid", "resend"),
        "ETL_TYPE": ("dify|Unstructured", "dify"),
        "WORKFLOW_NODE_EXECUTION_STORAGE": ("rdbms|hybrid", "rdbms"),
        "PLUGIN_STORAGE_TYPE": (
            "local|aws_s3|tencent_cos|azure_blob|aliyun_oss|volcengine_tos",
            "local",
        ),
        "STORAGE_TYPE": (
            "opendal|s3|azure-blob|google-storage|aliyun-oss|tencent-cos|huawei-obs|oci-storage|volcengine-tos|baidu-obs|supabase|clickzetta-volume",
            "opendal",
        ),
    }

    for target, (default, selected) in expected_options.items():
        config = configs[target]
        assert config.get("Default") == default  # nosec B101
        assert (config.text or "").strip() == selected  # nosec B101


def test_template_does_not_select_placeholder_integration_values() -> None:
    for config in _config_elements():
        default = (config.get("Default") or "").lower()
        selected = (config.text or "").strip().lower()
        haystack = " ".join((default, selected))

        assert not haystack.startswith("your")  # nosec B101
        for marker in PLACEHOLDER_DEFAULT_MARKERS:
            assert (
                marker not in haystack
            ), f"{config.get('Name') or config.get('Target')} includes placeholder value {marker!r}"  # nosec B101


def test_required_appdata_paths_are_declared_as_container_volumes() -> None:
    volumes = _dockerfile_volumes()
    assert volumes, "Dockerfile must declare persistent volumes"  # nosec B101

    for config in _config_elements():
        if config.get("Type") != "Path" or config.get("Required") != "true":
            continue
        default = config.get("Default") or config.text or ""
        target = config.get("Target") or ""
        if not default.startswith("/mnt/user/appdata"):
            continue
        assert any(
            target == volume or target.startswith(f"{volume.rstrip('/')}/")
            for volume in volumes
        ), f"{target} must be covered by a Dockerfile VOLUME"  # nosec B101


def test_template_ports_are_exposed_by_image() -> None:
    exposed_ports = _exposed_ports()
    assert exposed_ports, "Dockerfile must expose template ports"  # nosec B101

    for config in _config_elements():
        if config.get("Type") == "Port":
            assert config.get("Target") in exposed_ports  # nosec B101


def test_template_surface_is_curated_but_upstream_tracked() -> None:
    config_targets = {
        config.get("Target") for config in _config_elements() if config.get("Target")
    }
    upstream_targets = {
        line.strip()
        for line in (ROOT / "rootfs/opt/dify-aio/upstream-env-vars.txt")
        .read_text()
        .splitlines()
        if line.strip()
    }

    assert 500 <= len(config_targets) <= 650  # nosec B101
    assert len(upstream_targets) > len(config_targets)  # nosec B101
    assert "DIFY_AIO_EXTRA_ENV_FILE" in config_targets  # nosec B101
    assert "CHECK_UPDATE_URL" in config_targets  # nosec B101
    assert "DIFY_BIND_ADDRESS" in config_targets  # nosec B101
    assert "QDRANT_URL" in config_targets  # nosec B101
    assert "WEAVIATE_ENDPOINT" in config_targets  # nosec B101
    assert "MYSCALE_HOST" in config_targets  # nosec B101
    assert "ORACLE_DSN" in config_targets  # nosec B101
    assert "CLICKZETTA_USERNAME" in config_targets  # nosec B101
    assert "ELASTICSEARCH_HOST" in config_targets  # nosec B101
    assert "S3_ENDPOINT" in config_targets  # nosec B101
    assert "OCI_ENDPOINT" in config_targets  # nosec B101
    assert "BAIDU_OBS_BUCKET_NAME" in config_targets  # nosec B101
    assert "CLICKZETTA_VOLUME_TYPE" in config_targets  # nosec B101
    assert "SMTP_SERVER" in config_targets  # nosec B101
    assert "OTEL_EXPORTER_TYPE" in config_targets  # nosec B101
    assert "SANDBOX_EXPIRED_RECORDS_CLEAN_TASK_LOCK_TTL" in config_targets  # nosec B101
    assert "OPENSEARCH_INITIAL_ADMIN_PASSWORD" not in config_targets  # nosec B101


def test_advertised_vector_store_options_have_companion_configs() -> None:
    configs = _configs_by_target()
    options = set(configs["VECTOR_STORE"].get("Default", "").split("|"))
    expected_companions = {
        "pgvector": "PGVECTOR_HOST",
        "weaviate": "WEAVIATE_ENDPOINT",
        "qdrant": "QDRANT_URL",
        "milvus": "MILVUS_URI",
        "myscale": "MYSCALE_HOST",
        "relyt": "RELYT_HOST",
        "pgvecto-rs": "PGVECTO_RS_HOST",
        "chroma": "CHROMA_HOST",
        "opensearch": "OPENSEARCH_HOST",
        "oracle": "ORACLE_DSN",
        "tencent": "TENCENT_VECTOR_DB_URL",
        "elasticsearch": "ELASTICSEARCH_HOST",
        "elasticsearch-ja": "ELASTICSEARCH_HOST",
        "analyticdb": "ANALYTICDB_HOST",
        "couchbase": "COUCHBASE_CONNECTION_STRING",
        "vikingdb": "VIKINGDB_HOST",
        "opengauss": "OPENGAUSS_HOST",
        "tablestore": "TABLESTORE_ENDPOINT",
        "vastbase": "VASTBASE_HOST",
        "tidb": "TIDB_VECTOR_HOST",
        "tidb_on_qdrant": "TIDB_ON_QDRANT_URL",
        "baidu": "BAIDU_VECTOR_DB_ENDPOINT",
        "lindorm": "LINDORM_URL",
        "huawei_cloud": "HUAWEI_CLOUD_HOSTS",
        "upstash": "UPSTASH_VECTOR_URL",
        "matrixone": "MATRIXONE_HOST",
        "clickzetta": "CLICKZETTA_USERNAME",
        "alibabacloud_mysql": "ALIBABACLOUD_MYSQL_HOST",
        "iris": "IRIS_HOST",
        "hologres": "HOLOGRES_HOST",
    }

    assert options == set(expected_companions)  # nosec B101
    for companion in expected_companions.values():
        assert companion in configs  # nosec B101


def test_advertised_storage_options_have_companion_configs() -> None:
    configs = _configs_by_target()
    options = set(configs["STORAGE_TYPE"].get("Default", "").split("|"))
    expected_companions = {
        "opendal": "OPENDAL_SCHEME",
        "s3": "S3_ENDPOINT",
        "azure-blob": "AZURE_BLOB_ACCOUNT_NAME",
        "google-storage": "GOOGLE_STORAGE_BUCKET_NAME",
        "aliyun-oss": "ALIYUN_OSS_BUCKET_NAME",
        "tencent-cos": "TENCENT_COS_BUCKET_NAME",
        "huawei-obs": "HUAWEI_OBS_BUCKET_NAME",
        "oci-storage": "OCI_ENDPOINT",
        "volcengine-tos": "VOLCENGINE_TOS_BUCKET_NAME",
        "baidu-obs": "BAIDU_OBS_BUCKET_NAME",
        "supabase": "SUPABASE_URL",
        "clickzetta-volume": "CLICKZETTA_VOLUME_TYPE",
    }

    assert options == set(expected_companions)  # nosec B101
    for companion in expected_companions.values():
        assert companion in configs  # nosec B101


def test_privacy_sensitive_update_check_is_blank_by_default() -> None:
    config = _configs_by_target()["CHECK_UPDATE_URL"]

    assert config.get("Default") == ""  # nosec B101
    assert (config.text or "").strip() == ""  # nosec B101


def test_new_secret_like_integration_fields_are_masked() -> None:
    configs = _configs_by_target()
    expected_masked = {
        "ALIBABACLOUD_MYSQL_PASSWORD",
        "ANALYTICDB_KEY_SECRET",
        "BAIDU_OBS_SECRET_KEY",
        "BAIDU_VECTOR_DB_API_KEY",
        "COUCHBASE_PASSWORD",
        "HOLOGRES_ACCESS_KEY_SECRET",
        "IRIS_PASSWORD",
        "LINDORM_PASSWORD",
        "OCI_SECRET_KEY",
        "ORACLE_PASSWORD",
        "TENCENT_VECTOR_DB_API_KEY",
        "VIKINGDB_SECRET_KEY",
    }

    for target in expected_masked:
        assert configs[target].get("Mask") == "true"  # nosec B101


def test_internal_service_bind_defaults_prefer_localhost() -> None:
    configs = _configs_by_target()
    expected = {
        "DIFY_BIND_ADDRESS": "127.0.0.1",
        "DIFY_WEB_HOST": "127.0.0.1",
        "PLUGIN_DEBUGGING_HOST": "127.0.0.1",
    }

    for target, selected in expected.items():
        config = configs[target]
        assert config.get("Default") == selected  # nosec B101
        assert (config.text or "").strip() == selected  # nosec B101


def test_dockerfile_has_runtime_safety_contract() -> None:
    dockerfile = _dockerfile_text()
    arg_defaults = _arg_defaults()
    from_lines = [
        line.split()[1] for line in dockerfile.splitlines() if line.startswith("FROM ")
    ]

    assert from_lines, "Dockerfile must declare at least one base image"  # nosec B101
    for image in from_lines:
        digest_arg = re.search(r"@\$\{([^}]+)\}", image)
        assert "@sha256:" in image or (  # nosec B101
            digest_arg
            and arg_defaults.get(digest_arg.group(1), "").startswith("sha256:")
        ), f"{image} must be digest-pinned"

    assert "HEALTHCHECK" in dockerfile  # nosec B101
    assert "curl -fsS" in dockerfile  # nosec B101
    assert 'ENTRYPOINT ["/init"]' in dockerfile  # nosec B101
    assert "S6_CMD_WAIT_FOR_SERVICES_MAXTIME" in dockerfile  # nosec B101
    assert "S6_BEHAVIOUR_IF_STAGE2_FAILS=2" in dockerfile  # nosec B101


def test_docker_socket_mount_is_advanced_and_documented_when_present() -> None:
    for config in _config_elements():
        if config.get("Target") != "/var/run/docker.sock":
            continue
        description = (config.get("Description") or "").lower()
        assert config.get("Display") == "advanced"  # nosec B101
        assert config.get("Required") == "false"  # nosec B101
        assert "socket" in description and "security" in description  # nosec B101
