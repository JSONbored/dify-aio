#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "dify-aio.xml"
UPSTREAM_ENV_PATH = ROOT / "docs/upstream/dify.env.example"
UPSTREAM_ENV_VARS_PATH = ROOT / "rootfs/opt/dify-aio/upstream-env-vars.txt"

GENERATED_CHANGELOG_NOTE = (
    "Generated from CHANGELOG.md during release preparation. Do not edit manually."
)

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
    "your-",
    "your_",
)

URL_PUBLIC_TARGETS = {
    "APP_API_URL",
    "APP_WEB_URL",
    "CONSOLE_API_URL",
    "CONSOLE_WEB_URL",
    "FILES_URL",
    "INTERNAL_FILES_URL",
    "NEXT_PUBLIC_SOCKET_URL",
    "SERVICE_API_URL",
    "TRIGGER_URL",
}

INTERNAL_SERVICE_TARGETS = {
    "CELERY_BROKER_URL",
    "CODE_EXECUTION_API_KEY",
    "CODE_EXECUTION_ENDPOINT",
    "LOG_FILE",
    "LOG_TZ",
    "OPENDAL_FS_ROOT",
    "PGVECTOR_DATABASE",
    "PGVECTOR_HOST",
    "PGVECTOR_PASSWORD",
    "PGVECTOR_PORT",
    "PGVECTOR_USER",
    "PLUGIN_DAEMON_URL",
    "PLUGIN_DIFY_INNER_API_URL",
    "SANDBOX_API_KEY",
    "SANDBOX_HTTP_PROXY",
    "SANDBOX_HTTPS_PROXY",
    "SANDBOX_PORT",
    "SSRF_PROXY_HTTP_URL",
    "SSRF_PROXY_HTTPS_URL",
    "SSRF_REVERSE_PROXY_PORT",
    "SSRF_SANDBOX_HOST",
    "VECTOR_STORE",
}

CURATED_UPSTREAM_PREFIXES = (
    "ACCESS_TOKEN",
    "ALIYUN_OSS",
    "API_TOOL",
    "APP_",
    "ARCHIVE_STORAGE",
    "ATTACHMENT",
    "AZURE_BLOB",
    "CELERY",
    "CHROMA",
    "CODE_EXECUTION",
    "CONSOLE_CORS",
    "COOKIE",
    "DEBUG",
    "ELASTICSEARCH",
    "ENABLE_COLLABORATION",
    "ENABLE_REQUEST",
    "ENABLE_WEBSITE",
    "ETL",
    "FILES_ACCESS",
    "FLASK",
    "GOOGLE_STORAGE",
    "HTTP_REQUEST_NODE",
    "HUAWEI_OBS",
    "LOG",
    "MAIL",
    "MIGRATION",
    "MILVUS",
    "MULTIMODAL",
    "MYSQL",
    "NEXT_PUBLIC",
    "NOTION",
    "OPENAI_API_BASE",
    "OPENSEARCH",
    "OTEL",
    "PGVECTOR",
    "PLUGIN",
    "POSITION",
    "POSTGRES",
    "QDRANT",
    "REDIS",
    "REFRESH_TOKEN",
    "RESEND",
    "S3",
    "SANDBOX",
    "SENTRY",
    "SMTP",
    "SQLALCHEMY",
    "SSRF",
    "STORAGE_TYPE",
    "SUPABASE",
    "TENCENT_COS",
    "TIDB_ON_QDRANT",
    "TIDB_VECTOR",
    "UNSTRUCTURED",
    "UPLOAD",
    "UPSTASH",
    "VECTOR",
    "VOLCENGINE_TOS",
    "WEB_API",
    "WEAVIATE",
)

CURATED_UPSTREAM_EXCLUDED_PREFIXES = (
    "CHROMA_IS_PERSISTENT",
    "CHROMA_SERVER_AUTHN",
    "MYSQL_HOST_VOLUME",
    "OPENSEARCH_BOOTSTRAP",
    "OPENSEARCH_DISCOVERY",
    "OPENSEARCH_INITIAL_ADMIN_PASSWORD",
    "OPENSEARCH_JAVA",
    "OPENSEARCH_MEMLOCK",
    "OPENSEARCH_NOFILE",
    "PGVECTOR_PGDATA",
    "PGVECTOR_PGUSER",
    "PGVECTOR_POSTGRES",
    "PLUGIN_BASED_TOKEN_COUNTING_ENABLED",
    "PLUGIN_DAEMON_TIMEOUT",
    "PLUGIN_INSTALLED_PATH",
    "PLUGIN_MAX_EXECUTION_TIMEOUT",
    "PLUGIN_MEDIA_CACHE_PATH",
    "PLUGIN_MODEL_SCHEMA_CACHE_TTL",
    "PLUGIN_PACKAGE_CACHE_PATH",
    "PLUGIN_PPROF",
    "PLUGIN_PYTHON_ENV_INIT_TIMEOUT",
    "PLUGIN_STDIO",
    "PLUGIN_STORAGE_LOCAL_ROOT",
    "PLUGIN_WORKING_PATH",
    "SANDBOX_EXPIRED",
    "SSRF_COREDUMP",
    "TIDB_API_URL",
    "TIDB_IAM_API_URL",
    "TIDB_PRIVATE_KEY",
    "TIDB_PROJECT_ID",
    "TIDB_PUBLIC_KEY",
    "TIDB_REGION",
    "TIDB_SPEND_LIMIT",
    "WEAVIATE_AUTHENTICATION_ANONYMOUS",
    "WEAVIATE_AUTHENTICATION_APIKEY",
    "WEAVIATE_AUTHORIZATION_ADMINLIST",
    "WEAVIATE_CLUSTER",
    "WEAVIATE_DEFAULT_VECTORIZER",
    "WEAVIATE_DISABLE_TELEMETRY",
    "WEAVIATE_ENABLE_TOKENIZER",
    "WEAVIATE_PERSISTENCE",
    "WEAVIATE_QUERY_DEFAULTS",
)


@dataclass(frozen=True)
class Config:
    name: str
    target: str
    default: str
    description: str
    type: str = "Variable"
    display: str = "advanced"
    required: bool = False
    mask: bool = False
    mode: str = ""
    selected: str | None = None


def clean_description(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    return textwrap.shorten(text, width=280, placeholder="...")


def parse_upstream_env(path: Path) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    comments: list[str] = []

    for raw_line in path.read_text().splitlines():
        line = raw_line.rstrip()
        if not line:
            comments = []
            continue
        if line.lstrip().startswith("#"):
            comment = line.lstrip()[1:].strip()
            if comment and not set(comment) <= {"-"}:
                comments.append(comment)
            continue

        match = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
        if not match:
            comments = []
            continue

        name, value = match.groups()
        entries.append((name, value, clean_description(" ".join(comments))))
        comments = []

    return entries


def is_secret_target(target: str) -> bool:
    upper = target.upper()
    if upper.endswith("_PATH") or upper.endswith("_URL") or upper.endswith("_HOST"):
        return False
    return any(keyword in upper for keyword in SECRET_KEYWORDS)


def is_placeholder_default(default: str) -> bool:
    value = default.strip().lower()
    if not value:
        return False
    return value.startswith("your") or any(
        marker in value for marker in PLACEHOLDER_DEFAULT_MARKERS
    )


def is_curated_upstream_target(target: str) -> bool:
    return any(
        target.startswith(prefix) for prefix in CURATED_UPSTREAM_PREFIXES
    ) and not any(
        target.startswith(prefix) for prefix in CURATED_UPSTREAM_EXCLUDED_PREFIXES
    )


def selected_default_for(target: str, default: str) -> tuple[str, str]:
    if is_secret_target(target):
        return "", ""
    if is_placeholder_default(default):
        return "", ""
    if target in URL_PUBLIC_TARGETS:
        return "", ""
    if target in INTERNAL_SERVICE_TARGETS:
        return "", ""

    lowered = default.lower()
    if lowered == "true":
        opposite = (
            "FALSE"
            if default.isupper()
            else "False" if default[:1].isupper() else "false"
        )
        return f"{default}|{opposite}", default
    if lowered == "false":
        opposite = (
            "TRUE" if default.isupper() else "True" if default[:1].isupper() else "true"
        )
        return f"{default}|{opposite}", default
    if "|" in default:
        return "", default
    return default, default


def attr(value: str) -> str:
    return escape(value, {'"': "&quot;", "'": "&apos;"})


def text(value: str) -> str:
    return escape(value)


def render_config(config: Config) -> str:
    selected = config.default if config.selected is None else config.selected
    attrs = {
        "Name": config.name,
        "Target": config.target,
        "Default": config.default,
        "Mode": config.mode,
        "Description": config.description,
        "Type": config.type,
        "Display": config.display,
        "Required": "true" if config.required else "false",
        "Mask": "true" if config.mask else "false",
    }
    rendered_attrs = " ".join(f'{key}="{attr(value)}"' for key, value in attrs.items())
    if selected:
        return f"  <Config {rendered_attrs}>{text(selected)}</Config>"
    return f"  <Config {rendered_attrs}/>"


def core_configs() -> list[Config]:
    return [
        Config(
            "Web UI Port",
            "8080",
            "8080",
            "Dify Web UI and API gateway port.",
            type="Port",
            display="always",
            required=True,
            mode="tcp",
            selected="8080",
        ),
        Config(
            "AppData",
            "/appdata",
            "/mnt/user/appdata/dify-aio",
            "Persistent Dify data, generated secrets, PostgreSQL data, Redis data, uploads, plugin storage, and sandbox configuration.",
            type="Path",
            display="always",
            required=True,
            mode="rw",
            selected="/mnt/user/appdata/dify-aio",
        ),
        Config(
            "Public URL",
            "DIFY_AIO_PUBLIC_URL",
            "",
            "Optional external base URL such as https://dify.example.com. Used to default Dify console, app, trigger, WebSocket, and file URLs.",
            display="always",
        ),
        Config(
            "Initial Admin Password",
            "INIT_PASSWORD",
            "",
            "Optional initial admin password. Dify limits this value to 30 characters. Leave blank to set the admin account during first-run setup.",
            display="always",
            mask=True,
        ),
        Config(
            "Timezone",
            "TZ",
            "UTC",
            "Container timezone.",
            display="always",
            selected="UTC",
        ),
        Config(
            "Secret Key",
            "SECRET_KEY",
            "",
            "Dify application secret key. Leave blank to generate and persist one on first boot. Changing this after setup invalidates encrypted credentials and sessions.",
            mask=True,
        ),
        Config(
            "Use Internal PostgreSQL",
            "DIFY_USE_INTERNAL_POSTGRES",
            "true|false",
            "Use the bundled PostgreSQL 15 database with pgvector. Set false only when using an external PostgreSQL-compatible database.",
            required=True,
            selected="true",
        ),
        Config(
            "Database Type",
            "DB_TYPE",
            "postgresql",
            "Database type used by Dify. The bundled AIO database is PostgreSQL.",
            required=True,
            selected="postgresql",
        ),
        Config(
            "Database Host",
            "DB_HOST",
            "127.0.0.1",
            "PostgreSQL host. Keep 127.0.0.1 for bundled PostgreSQL.",
            required=True,
            selected="127.0.0.1",
        ),
        Config(
            "Database Port",
            "DB_PORT",
            "5432",
            "PostgreSQL port.",
            required=True,
            selected="5432",
        ),
        Config(
            "Database User",
            "DB_USERNAME",
            "dify",
            "PostgreSQL user for Dify.",
            required=True,
            selected="dify",
        ),
        Config(
            "Database Password",
            "DB_PASSWORD",
            "",
            "PostgreSQL password. Leave blank to generate and persist one on first boot.",
            mask=True,
        ),
        Config(
            "Database Name",
            "DB_DATABASE",
            "dify",
            "PostgreSQL database used by the Dify API.",
            required=True,
            selected="dify",
        ),
        Config(
            "Plugin Database Name",
            "DB_PLUGIN_DATABASE",
            "dify_plugin",
            "PostgreSQL database used by the Dify plugin daemon.",
            required=True,
            selected="dify_plugin",
        ),
        Config(
            "Use Internal Redis",
            "DIFY_USE_INTERNAL_REDIS",
            "true|false",
            "Use the bundled Redis instance. Set false only when using an external Redis service.",
            required=True,
            selected="true",
        ),
        Config(
            "Redis Host",
            "REDIS_HOST",
            "127.0.0.1",
            "Redis host. Keep 127.0.0.1 for bundled Redis.",
            required=True,
            selected="127.0.0.1",
        ),
        Config(
            "Redis Port",
            "REDIS_PORT",
            "6379",
            "Redis port.",
            required=True,
            selected="6379",
        ),
        Config(
            "Redis Password",
            "REDIS_PASSWORD",
            "",
            "Redis password. Leave blank to generate and persist one on first boot.",
            mask=True,
        ),
        Config(
            "Celery Broker URL",
            "CELERY_BROKER_URL",
            "",
            "Optional explicit Celery broker URL. Leave blank to derive it from Redis settings.",
        ),
        Config(
            "Console API URL",
            "CONSOLE_API_URL",
            "",
            "Optional public console API URL. Leave blank to derive from Public URL or incoming requests.",
        ),
        Config(
            "Console Web URL",
            "CONSOLE_WEB_URL",
            "",
            "Optional public console web URL. Leave blank to derive from Public URL or incoming requests.",
        ),
        Config(
            "Service API URL",
            "SERVICE_API_URL",
            "",
            "Optional public Service API URL shown inside Dify. Leave blank to derive from Public URL or incoming requests.",
        ),
        Config(
            "Trigger URL",
            "TRIGGER_URL",
            "",
            "Optional public trigger URL. Leave blank to derive from Public URL or use Dify defaults.",
        ),
        Config(
            "App API URL",
            "APP_API_URL",
            "",
            "Optional published-app API URL. Leave blank to derive from Public URL or incoming requests.",
        ),
        Config(
            "App Web URL",
            "APP_WEB_URL",
            "",
            "Optional published-app web URL. Leave blank to derive from Public URL or incoming requests.",
        ),
        Config(
            "Files URL",
            "FILES_URL",
            "",
            "Optional public file preview/download URL. Leave blank to derive from Public URL.",
        ),
        Config(
            "Internal Files URL",
            "INTERNAL_FILES_URL",
            "",
            "Internal file URL used by Dify services. Leave blank for the AIO localhost default.",
        ),
        Config(
            "Next Public Socket URL",
            "NEXT_PUBLIC_SOCKET_URL",
            "",
            "Optional WebSocket URL for collaboration mode. Leave blank to derive from Public URL when provided.",
        ),
        Config(
            "Log File",
            "LOG_FILE",
            "",
            "Optional Dify log file path. Leave blank for /appdata/logs/server.log.",
        ),
        Config(
            "Log Timezone",
            "LOG_TZ",
            "",
            "Optional Dify log timezone. Leave blank to inherit TZ.",
        ),
        Config(
            "Server Workers",
            "SERVER_WORKER_AMOUNT",
            "1",
            "Dify API worker count. Increase only if the host has enough CPU and memory.",
            selected="1",
        ),
        Config(
            "Server Worker Class",
            "SERVER_WORKER_CLASS",
            "geventwebsocket.gunicorn.workers.GeventWebSocketWorker",
            "Gunicorn worker class. The AIO default supports collaboration WebSockets.",
            selected="geventwebsocket.gunicorn.workers.GeventWebSocketWorker",
        ),
        Config(
            "Celery Workers",
            "CELERY_WORKER_AMOUNT",
            "2",
            "Dify background worker count. Increase for indexing-heavy workloads on larger hosts.",
            selected="2",
        ),
        Config(
            "Celery Worker Class",
            "CELERY_WORKER_CLASS",
            "gevent",
            "Celery worker class. Keep gevent unless debugging an upstream-specific issue.",
            selected="gevent",
        ),
        Config(
            "Gunicorn Timeout",
            "GUNICORN_TIMEOUT",
            "360",
            "API request timeout in seconds.",
            selected="360",
        ),
        Config(
            "Vector Store",
            "VECTOR_STORE",
            "pgvector|weaviate|qdrant|milvus|myscale|relyt|pgvecto-rs|chroma|opensearch|oracle|tencent|elasticsearch|elasticsearch-ja|analyticdb|couchbase|vikingdb|opengauss|tablestore|vastbase|tidb|tidb_on_qdrant|baidu|lindorm|huawei_cloud|upstash|matrixone|clickzetta|alibabacloud_mysql|iris|hologres",
            "Dify vector database backend. The default uses bundled PostgreSQL with pgvector. Non-pgvector choices require external services and matching variables.",
            required=True,
            selected="pgvector",
        ),
        Config(
            "PGVector Host",
            "PGVECTOR_HOST",
            "",
            "Optional pgvector host override. Leave blank to reuse the Dify database host.",
        ),
        Config(
            "PGVector Port",
            "PGVECTOR_PORT",
            "",
            "Optional pgvector port override. Leave blank to reuse the Dify database port.",
        ),
        Config(
            "PGVector User",
            "PGVECTOR_USER",
            "",
            "Optional pgvector user override. Leave blank to reuse the Dify database user.",
        ),
        Config(
            "PGVector Password",
            "PGVECTOR_PASSWORD",
            "",
            "Optional pgvector password override. Leave blank to reuse the Dify database password.",
            mask=True,
        ),
        Config(
            "PGVector Database",
            "PGVECTOR_DATABASE",
            "",
            "Optional pgvector database override. Leave blank to reuse the Dify database name.",
        ),
        Config(
            "Qdrant URL",
            "QDRANT_URL",
            "",
            "External Qdrant URL when Vector Store is qdrant.",
        ),
        Config(
            "Qdrant API Key",
            "QDRANT_API_KEY",
            "",
            "External Qdrant API key when required.",
            mask=True,
        ),
        Config(
            "Weaviate Endpoint",
            "WEAVIATE_ENDPOINT",
            "",
            "External Weaviate HTTP endpoint when Vector Store is weaviate.",
        ),
        Config(
            "Weaviate API Key",
            "WEAVIATE_API_KEY",
            "",
            "External Weaviate API key when required.",
            mask=True,
        ),
        Config(
            "Weaviate GRPC Endpoint",
            "WEAVIATE_GRPC_ENDPOINT",
            "",
            "External Weaviate gRPC endpoint when required.",
        ),
        Config(
            "Storage Type",
            "STORAGE_TYPE",
            "opendal|s3|azure-blob|google-storage|aliyun-oss|tencent-cos|huawei-obs|volcengine-tos|supabase",
            "Dify file storage backend. The default uses local OpenDAL filesystem storage under AppData.",
            required=True,
            selected="opendal",
        ),
        Config(
            "OpenDAL Scheme",
            "OPENDAL_SCHEME",
            "fs",
            "OpenDAL storage scheme. The AIO default uses local filesystem storage.",
            selected="fs",
        ),
        Config(
            "OpenDAL Filesystem Root",
            "OPENDAL_FS_ROOT",
            "",
            "OpenDAL filesystem root. Leave blank for /app/api/storage, symlinked to AppData.",
        ),
        Config(
            "S3 Endpoint",
            "S3_ENDPOINT",
            "",
            "S3-compatible storage endpoint when using S3 storage.",
        ),
        Config(
            "S3 Region", "S3_REGION", "us-east-1", "S3 region.", selected="us-east-1"
        ),
        Config("S3 Bucket Name", "S3_BUCKET_NAME", "", "S3 bucket for Dify files."),
        Config("S3 Access Key", "S3_ACCESS_KEY", "", "S3 access key.", mask=True),
        Config("S3 Secret Key", "S3_SECRET_KEY", "", "S3 secret key.", mask=True),
        Config(
            "Enable Sandbox",
            "DIFY_ENABLE_SANDBOX",
            "true|false",
            "Run the bundled Dify sandbox used for code execution. Disabling it breaks code-execution features.",
            required=True,
            selected="true",
        ),
        Config(
            "Sandbox API Key",
            "SANDBOX_API_KEY",
            "",
            "Sandbox API key. Leave blank to generate and persist one on first boot.",
            mask=True,
        ),
        Config(
            "Code Execution Endpoint",
            "CODE_EXECUTION_ENDPOINT",
            "",
            "Dify sandbox endpoint. Leave blank for the AIO localhost sandbox.",
        ),
        Config(
            "Code Execution API Key",
            "CODE_EXECUTION_API_KEY",
            "",
            "Dify sandbox API key used by the API service. Leave blank to mirror Sandbox API Key.",
            mask=True,
        ),
        Config(
            "Sandbox Network Access",
            "SANDBOX_ENABLE_NETWORK",
            "true|false",
            "Allow sandboxed code to access the network through the bundled SSRF proxy.",
            required=True,
            selected="true",
        ),
        Config(
            "Sandbox Worker Timeout",
            "SANDBOX_WORKER_TIMEOUT",
            "15",
            "Sandbox execution timeout in seconds.",
            selected="15",
        ),
        Config(
            "Sandbox Port",
            "SANDBOX_PORT",
            "",
            "Sandbox service port. Leave blank for 8194.",
        ),
        Config(
            "Sandbox HTTP Proxy",
            "SANDBOX_HTTP_PROXY",
            "",
            "HTTP proxy used by sandboxed code. Leave blank for the bundled SSRF proxy.",
        ),
        Config(
            "Sandbox HTTPS Proxy",
            "SANDBOX_HTTPS_PROXY",
            "",
            "HTTPS proxy used by sandboxed code. Leave blank for the bundled SSRF proxy.",
        ),
        Config(
            "SSRF HTTP Proxy URL",
            "SSRF_PROXY_HTTP_URL",
            "",
            "Internal HTTP proxy URL used by Dify. Leave blank for the bundled SSRF proxy.",
        ),
        Config(
            "SSRF HTTPS Proxy URL",
            "SSRF_PROXY_HTTPS_URL",
            "",
            "Internal HTTPS proxy URL used by Dify. Leave blank for the bundled SSRF proxy.",
        ),
        Config(
            "SSRF Reverse Proxy Port",
            "SSRF_REVERSE_PROXY_PORT",
            "",
            "Internal reverse proxy port. Leave blank for the AIO non-conflicting default.",
        ),
        Config(
            "SSRF Sandbox Host",
            "SSRF_SANDBOX_HOST",
            "",
            "Sandbox host name used by the SSRF proxy. Leave blank for localhost.",
        ),
        Config(
            "Plugin Daemon Key",
            "PLUGIN_DAEMON_KEY",
            "",
            "Plugin daemon server key. Leave blank to generate and persist one on first boot.",
            mask=True,
        ),
        Config(
            "Plugin Inner API Key",
            "PLUGIN_DIFY_INNER_API_KEY",
            "",
            "Shared inner API key used between Dify and the plugin daemon. Leave blank to generate and persist one on first boot.",
            mask=True,
        ),
        Config(
            "Plugin Daemon URL",
            "PLUGIN_DAEMON_URL",
            "",
            "Plugin daemon URL used by Dify. Leave blank for the AIO localhost plugin daemon.",
        ),
        Config(
            "Plugin Inner API URL",
            "PLUGIN_DIFY_INNER_API_URL",
            "",
            "Inner API URL used by the plugin daemon. Leave blank for the AIO localhost API.",
        ),
        Config(
            "Verify Plugin Signatures",
            "FORCE_VERIFYING_SIGNATURE",
            "true|false",
            "Require signed plugins where Dify supports signature verification.",
            required=True,
            selected="true",
        ),
        Config(
            "Marketplace Enabled",
            "MARKETPLACE_ENABLED",
            "true|false",
            "Enable the Dify plugin marketplace integration.",
            required=True,
            selected="true",
        ),
        Config(
            "Mail Type",
            "MAIL_TYPE",
            "resend|smtp",
            "Mail provider used by Dify.",
            selected="resend",
        ),
        Config(
            "Resend API Key",
            "RESEND_API_KEY",
            "",
            "Resend API key when Mail Type is resend.",
            mask=True,
        ),
        Config("SMTP Server", "SMTP_SERVER", "", "SMTP host when Mail Type is smtp."),
        Config("SMTP Port", "SMTP_PORT", "465", "SMTP port.", selected="465"),
        Config("SMTP Username", "SMTP_USERNAME", "", "SMTP username.", mask=True),
        Config("SMTP Password", "SMTP_PASSWORD", "", "SMTP password.", mask=True),
        Config(
            "Mail From",
            "MAIL_DEFAULT_SEND_FROM",
            "",
            "Default sender address for Dify email.",
        ),
        Config(
            "Nginx Port",
            "NGINX_PORT",
            "8080",
            "Internal Nginx listen port. Keep this aligned with the Web UI Port mapping.",
            selected="8080",
        ),
        Config(
            "Nginx Server Name",
            "NGINX_SERVER_NAME",
            "_",
            "Nginx server_name value.",
            selected="_",
        ),
        Config(
            "Nginx Client Max Body Size",
            "NGINX_CLIENT_MAX_BODY_SIZE",
            "100M",
            "Maximum request body size accepted by the bundled Nginx gateway.",
            selected="100M",
        ),
        Config(
            "Nginx Proxy Read Timeout",
            "NGINX_PROXY_READ_TIMEOUT",
            "3600s",
            "Bundled Nginx proxy read timeout.",
            selected="3600s",
        ),
        Config(
            "Nginx Proxy Send Timeout",
            "NGINX_PROXY_SEND_TIMEOUT",
            "3600s",
            "Bundled Nginx proxy send timeout.",
            selected="3600s",
        ),
        Config(
            "Website Firecrawl",
            "ENABLE_WEBSITE_FIRECRAWL",
            "true|false",
            "Expose Firecrawl as a Dify website datasource option. Configure Firecrawl credentials inside Dify where required.",
            required=True,
            selected="true",
        ),
        Config(
            "Website Jina Reader",
            "ENABLE_WEBSITE_JINAREADER",
            "true|false",
            "Expose Jina Reader as a Dify website datasource option.",
            required=True,
            selected="true",
        ),
        Config(
            "Website WaterCrawl",
            "ENABLE_WEBSITE_WATERCRAWL",
            "true|false",
            "Expose WaterCrawl as a Dify website datasource option.",
            required=True,
            selected="true",
        ),
        Config(
            "AIO Wait Timeout Seconds",
            "DIFY_AIO_WAIT_TIMEOUT_SECONDS",
            "300",
            "Startup wait timeout for internal service readiness checks.",
            selected="300",
        ),
        Config(
            "AIO Extra Env File",
            "DIFY_AIO_EXTRA_ENV_FILE",
            "/appdata/config/extra.env",
            "Optional dotenv-style file for rare upstream Dify variables that are intentionally not shown in the Unraid template.",
            selected="/appdata/config/extra.env",
        ),
        Config(
            "AIO LANG Override",
            "DIFY_AIO_LANG",
            "",
            "Optional locale override for LANG. Leave blank for C.UTF-8.",
        ),
        Config(
            "AIO LC_ALL Override",
            "DIFY_AIO_LC_ALL",
            "",
            "Optional locale override for LC_ALL. Leave blank for C.UTF-8.",
        ),
        Config(
            "Dify Web Port",
            "DIFY_WEB_PORT",
            "3000",
            "Internal Dify web service port. Keep aligned with the bundled Nginx proxy.",
            selected="3000",
        ),
        Config(
            "Dify Web Host",
            "DIFY_WEB_HOST",
            "0.0.0.0",
            "Internal Dify web service bind host.",
            selected="0.0.0.0",
        ),
        Config(
            "Plugin Platform",
            "PLUGIN_PLATFORM",
            "local",
            "Plugin daemon platform mode. The AIO default is local.",
            selected="local",
        ),
        Config(
            "Plugin Remote Installing Host",
            "PLUGIN_DEBUGGING_HOST",
            "0.0.0.0",
            "Plugin remote-install/debug host used by the plugin daemon.",
            selected="0.0.0.0",
        ),
        Config(
            "Plugin Remote Installing Port",
            "PLUGIN_DEBUGGING_PORT",
            "5003",
            "Plugin remote-install/debug port used by the plugin daemon.",
            selected="5003",
        ),
        Config(
            "Plugin Max Package Size",
            "PLUGIN_MAX_PACKAGE_SIZE",
            "52428800",
            "Maximum plugin package size accepted by the plugin daemon, in bytes.",
            selected="52428800",
        ),
        Config(
            "Plugin Daemon Port",
            "PLUGIN_DAEMON_PORT",
            "5002",
            "Internal plugin daemon port. Keep aligned with the bundled Nginx /e/ route.",
            selected="5002",
        ),
        Config(
            "Plugin DB SSL Mode",
            "DB_SSL_MODE",
            "disable",
            "Plugin daemon database SSL mode.",
            selected="disable",
        ),
        Config(
            "Sandbox Pip Mirror URL",
            "PIP_MIRROR_URL",
            "",
            "Optional Python package mirror URL used by the Dify sandbox.",
        ),
        Config(
            "Disable Next Telemetry",
            "NEXT_TELEMETRY_DISABLED",
            "1",
            "Disable telemetry from the bundled Next.js web runtime.",
            selected="1",
        ),
    ]


def generated_upstream_configs(
    entries: list[tuple[str, str, str]], existing: set[str]
) -> list[Config]:
    configs: list[Config] = []
    for target, raw_default, comment in entries:
        if target in existing or not is_curated_upstream_target(target):
            continue

        default, selected = selected_default_for(target, raw_default)
        if is_secret_target(target) and raw_default:
            suffix = " Upstream ships a sample value; the AIO template intentionally leaves it blank."
        elif is_placeholder_default(raw_default):
            suffix = " Upstream ships a placeholder value; the AIO template intentionally leaves it blank."
        elif raw_default and not default:
            suffix = f" Official default: {raw_default!r}."
        else:
            suffix = ""

        description = clean_description(
            (comment or "Upstream Dify self-hosted environment variable.") + suffix
        )
        configs.append(
            Config(
                name=f"Dify Env: {target}",
                target=target,
                default=default,
                description=description,
                mask=is_secret_target(target),
                selected=selected,
            )
        )

    return configs


def render_template(configs: list[Config]) -> str:
    config_lines = "\n".join(render_config(config) for config in configs)
    return f"""<?xml version="1.0"?>
<Container version="2">
  <Name>dify-aio</Name>
  <Repository>ghcr.io/jsonbored/dify-aio:latest</Repository>
  <Registry>https://ghcr.io/jsonbored/dify-aio</Registry>
  <Network>bridge</Network>
  <MyIP/>
  <Shell>sh</Shell>
  <Privileged>false</Privileged>
  <Support>https://github.com/JSONbored/dify-aio/issues</Support>
  <Project>https://github.com/JSONbored/dify-aio</Project>
  <Overview>Dify AIO packages the Dify self-hosted stack for Unraid in one practical container: API, workers, web UI, plugin daemon, code sandbox, SSRF proxy, Nginx, PostgreSQL with pgvector, and Redis. Leave the defaults in place for a first install, open the Web UI, and create the initial admin account. Secrets are generated on first boot under /appdata/config/generated.env. Advanced users can point Dify at external PostgreSQL, Redis, object storage, vector databases, SMTP, reverse proxy URLs, observability endpoints, and the broader upstream Dify environment surface.</Overview>
  <Changes>### 2026-04-29&#xD;
- {GENERATED_CHANGELOG_NOTE}&#xD;
- Scaffold Dify AIO from the current Unraid AIO template.&#xD;
- Bundle Dify API, web, worker, beat, sandbox, plugin daemon, PostgreSQL/pgvector, Redis, Nginx, and SSRF proxy defaults.&#xD;
</Changes>
  <Category>AI: Productivity: Tools:Utilities</Category>
  <WebUI>http://[IP]:[PORT:8080]</WebUI>
  <TemplateURL>https://raw.githubusercontent.com/JSONbored/awesome-unraid/main/dify-aio.xml</TemplateURL>
  <Icon>https://raw.githubusercontent.com/JSONbored/awesome-unraid/main/icons/dify.png</Icon>
  <ExtraSearchTerms>ai agent workflow llm rag chatbot mcp openai anthropic ollama app builder knowledge base</ExtraSearchTerms>
  <Requires>Dify is a heavier multi-service application. Plan for at least 2 CPU cores and 4 GiB RAM, with more memory for real workloads. Public exposure should be placed behind a trusted reverse proxy with TLS. Model-provider API keys, SMTP, object storage, and external vector stores are optional but may be required for production use.</Requires>
  <ExtraParams/>
  <PostArgs/>
  <CPUset/>
  <DateInstalled/>
  <DonateText>Support JSONbored on GitHub Sponsors.</DonateText>
  <DonateLink>https://github.com/sponsors/JSONbored</DonateLink>
  <Description/>
  <Networking>
    <Mode>bridge</Mode>
    <Publish>
      <Port>
        <HostPort>8080</HostPort>
        <ContainerPort>8080</ContainerPort>
        <Protocol>tcp</Protocol>
      </Port>
    </Publish>
  </Networking>
  <Data>
    <Volume>
      <HostDir>/mnt/user/appdata/dify-aio</HostDir>
      <ContainerDir>/appdata</ContainerDir>
      <Mode>rw</Mode>
    </Volume>
  </Data>
  <Environment/>

{config_lines}
</Container>
"""


def build_configs() -> tuple[list[Config], list[str]]:
    entries = parse_upstream_env(UPSTREAM_ENV_PATH)
    configs = core_configs()
    targets = {config.target for config in configs}
    configs.extend(generated_upstream_configs(entries, targets))
    upstream_targets = [target for target, _, _ in entries]
    return configs, upstream_targets


def write_outputs() -> None:
    configs, upstream_targets = build_configs()
    TEMPLATE_PATH.write_text(render_template(configs))
    UPSTREAM_ENV_VARS_PATH.parent.mkdir(parents=True, exist_ok=True)
    UPSTREAM_ENV_VARS_PATH.write_text("\n".join(upstream_targets) + "\n")


def check_outputs() -> int:
    configs, upstream_targets = build_configs()
    expected_template = render_template(configs)
    expected_env_vars = "\n".join(upstream_targets) + "\n"
    failures: list[str] = []
    if TEMPLATE_PATH.read_text() != expected_template:
        failures.append(
            f"{TEMPLATE_PATH} is out of date; run scripts/generate_dify_template.py"
        )
    if (
        not UPSTREAM_ENV_VARS_PATH.exists()
        or UPSTREAM_ENV_VARS_PATH.read_text() != expected_env_vars
    ):
        failures.append(
            f"{UPSTREAM_ENV_VARS_PATH} is out of date; run scripts/generate_dify_template.py"
        )
    if failures:
        print("\n".join(failures))
        return 1
    print(
        f"{TEMPLATE_PATH.name} and {UPSTREAM_ENV_VARS_PATH.relative_to(ROOT)} are generated and current"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Dify Unraid template.")
    parser.add_argument(
        "--check", action="store_true", help="Check generated files without writing."
    )
    args = parser.parse_args()

    if args.check:
        return check_outputs()
    write_outputs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
