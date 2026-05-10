#!/usr/bin/env bash
# shellcheck shell=bash

AIO_TRUE_VALUES="1 true TRUE yes YES on ON"
AIO_APPDATA_DIR="/appdata"
AIO_CONFIG_DIR="${AIO_APPDATA_DIR}/config"
AIO_ENV_FILE="${AIO_CONFIG_DIR}/generated.env"
AIO_UPSTREAM_ENV_VARS_FILE="/opt/dify-aio/upstream-env-vars.txt"

AIO_BLANK_AS_UNSET_VARS=(
	APP_API_URL
	APP_WEB_URL
	CELERY_WORKER_AMOUNT
	CONSOLE_API_URL
	CONSOLE_WEB_URL
	DIFY_AIO_PUBLIC_URL
	DIFY_AIO_WAIT_TIMEOUT_SECONDS
	FILES_URL
	INIT_PASSWORD
	MAIL_DEFAULT_SEND_FROM
	MARKETPLACE_API_URL
	MARKETPLACE_URL
	NEXT_PUBLIC_COOKIE_DOMAIN
	NEXT_PUBLIC_SOCKET_URL
	OPENAI_API_BASE
	OPENAI_API_KEY
	PLUGIN_AWS_ACCESS_KEY
	PLUGIN_AWS_SECRET_KEY
	PLUGIN_S3_ENDPOINT
	PGVECTOR_HOST
	PGVECTOR_PASSWORD
	PGVECTOR_PORT
	PGVECTOR_USER
	RESEND_API_KEY
	S3_ACCESS_KEY
	S3_BUCKET_NAME
	S3_ENDPOINT
	S3_SECRET_KEY
	SERVICE_API_URL
	SMTP_PASSWORD
	SMTP_SERVER
	SMTP_USERNAME
	UNSTRUCTURED_API_KEY
	UNSTRUCTURED_API_URL
)

AIO_BLANK_IS_MEANINGFUL_VARS=(
	CHECK_UPDATE_URL
)

aio_log() {
	printf '[dify-aio] %s\n' "$*"
}

is_true() {
	local value="${1-}"
	for truthy in ${AIO_TRUE_VALUES}; do
		[[ ${value} == "${truthy}" ]] && return 0
	done
	return 1
}

blank_is_meaningful() {
	local candidate="$1"
	local name
	for name in "${AIO_BLANK_IS_MEANINGFUL_VARS[@]}"; do
		[[ ${candidate} == "${name}" ]] && return 0
	done
	return 1
}

normalize_blank_env() {
	local name
	for name in "$@"; do
		if [[ -v ${name} && -z ${!name} ]] && ! blank_is_meaningful "${name}"; then
			unset "${name}"
		fi
	done
}

normalize_blank_upstream_env() {
	if [[ ! -f ${AIO_UPSTREAM_ENV_VARS_FILE} ]]; then
		return
	fi

	local name
	while IFS= read -r name; do
		[[ -z ${name} || ${name} == \#* ]] && continue
		normalize_blank_env "${name}"
	done <"${AIO_UPSTREAM_ENV_VARS_FILE}"
}

load_generated_env() {
	[[ -f ${AIO_ENV_FILE} ]] || return

	local line key value
	while IFS= read -r line || [[ -n ${line} ]]; do
		line="${line#"${line%%[![:space:]]*}"}"
		line="${line%"${line##*[![:space:]]}"}"
		[[ -z ${line} || ${line} == \#* ]] && continue

		if [[ ! ${line} =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
			aio_log "Ignoring invalid generated env line: ${line%%=*}"
			continue
		fi

		key="${line%%=*}"
		value="${line#*=}"
		if [[ ${#value} -ge 2 ]]; then
			if [[ ${value:0:1} == '"' && ${value: -1} == '"' ]]; then
				value="${value:1:${#value}-2}"
			elif [[ ${value:0:1} == "'" && ${value: -1} == "'" ]]; then
				value="${value:1:${#value}-2}"
			fi
		fi

		if [[ -z ${!key-} ]]; then
			export "${key}=${value}"
		fi
	done <"${AIO_ENV_FILE}"
}

load_extra_env() {
	local extra_env_file="${DIFY_AIO_EXTRA_ENV_FILE:-/appdata/config/extra.env}"
	[[ -f ${extra_env_file} ]] || return

	local line key value
	while IFS= read -r line || [[ -n ${line} ]]; do
		line="${line#"${line%%[![:space:]]*}"}"
		line="${line%"${line##*[![:space:]]}"}"
		[[ -z ${line} || ${line} == \#* ]] && continue

		if [[ ! ${line} =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
			aio_log "Ignoring invalid extra env line: ${line%%=*}"
			continue
		fi

		key="${line%%=*}"
		value="${line#*=}"
		if [[ ${#value} -ge 2 ]]; then
			if [[ ${value:0:1} == '"' && ${value: -1} == '"' ]]; then
				value="${value:1:${#value}-2}"
			elif [[ ${value:0:1} == "'" && ${value: -1} == "'" ]]; then
				value="${value:1:${#value}-2}"
			fi
		fi
		export "${key}=${value}"
	done <"${extra_env_file}"
}

persist_if_missing() {
	local key="$1"
	local value="$2"
	if grep -q "^${key}=" "${AIO_ENV_FILE}" 2>/dev/null; then
		return
	fi
	printf '%s="%s"\n' "${key}" "${value}" >>"${AIO_ENV_FILE}"
}

persist_secret_if_unset() {
	local key="$1"
	if [[ -n ${!key-} ]]; then
		return
	fi
	local generated_secret
	generated_secret="$(openssl rand -hex 32)"
	generated_secret="${generated_secret//$'\n'/}"
	persist_if_missing "${key}" "${generated_secret}"
}

urlencode_value() {
	python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1"
}

wait_for_tcp() {
	local host="$1"
	local port="$2"
	local label="$3"
	local timeout="${DIFY_AIO_WAIT_TIMEOUT_SECONDS:-300}"
	local deadline=$((SECONDS + timeout))

	until bash -lc "exec 3<>/dev/tcp/${host}/${port}" >/dev/null 2>&1; do
		if ((SECONDS >= deadline)); then
			aio_log "Timed out waiting for ${label} at ${host}:${port}."
			return 1
		fi
		sleep 2
	done
}

wait_for_http_url() {
	local url="$1"
	local label="$2"
	local timeout="${DIFY_AIO_WAIT_TIMEOUT_SECONDS:-300}"
	local deadline=$((SECONDS + timeout))

	until curl -fsS "${url}" >/dev/null 2>&1; do
		if ((SECONDS >= deadline)); then
			aio_log "Timed out waiting for ${label} at ${url}."
			return 1
		fi
		sleep 2
	done
}

set_public_url_if_default() {
	local name="$1"
	local value="$2"
	local current="${!name-}"

	case "${current}" in
	"" | http://127.0.0.1:* | http://localhost:* | ws://127.0.0.1:* | ws://localhost:*)
		export "${name}=${value}"
		;;
	*) ;;
	esac
}

sanitize_generic_proxy_env() {
	if is_true "${DIFY_AIO_TRUST_INHERITED_PROXY_ENV:-false}"; then
		return
	fi

	unset HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY
	unset http_proxy https_proxy all_proxy no_proxy
}

configure_dify_env() {
	normalize_blank_upstream_env
	normalize_blank_env "${AIO_BLANK_AS_UNSET_VARS[@]}"
	load_generated_env
	load_extra_env
	sanitize_generic_proxy_env

	export EDITION="${EDITION:-SELF_HOSTED}"
	export DEPLOY_ENV="${DEPLOY_ENV:-PRODUCTION}"
	export LANG="${DIFY_AIO_LANG:-C.UTF-8}"
	export LC_ALL="${DIFY_AIO_LC_ALL:-C.UTF-8}"
	export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
	export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/.uv-cache}"
	export LOG_TZ="${LOG_TZ:-${TZ:-UTC}}"
	export LOG_LEVEL="${LOG_LEVEL:-INFO}"
	export LOG_OUTPUT_FORMAT="${LOG_OUTPUT_FORMAT:-text}"
	export LOG_FILE="${LOG_FILE:-/appdata/logs/server.log}"
	export NEXT_TELEMETRY_DISABLED="${NEXT_TELEMETRY_DISABLED:-1}"
	export CHECK_UPDATE_URL="${CHECK_UPDATE_URL-}"

	export DIFY_PORT="${DIFY_PORT:-5001}"
	export DIFY_BIND_ADDRESS="${DIFY_BIND_ADDRESS:-127.0.0.1}"
	export SERVER_WORKER_AMOUNT="${SERVER_WORKER_AMOUNT:-1}"
	export SERVER_WORKER_CLASS="${SERVER_WORKER_CLASS:-geventwebsocket.gunicorn.workers.GeventWebSocketWorker}"
	export SERVER_WORKER_CONNECTIONS="${SERVER_WORKER_CONNECTIONS:-10}"
	export GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-360}"
	export CELERY_WORKER_AMOUNT="${CELERY_WORKER_AMOUNT:-2}"
	export CELERY_WORKER_CLASS="${CELERY_WORKER_CLASS:-gevent}"

	export SECRET_KEY="${SECRET_KEY:?missing SECRET_KEY}"
	export DB_TYPE="${DB_TYPE:-postgresql}"
	export DB_USERNAME="${DB_USERNAME:-dify}"
	export DB_PASSWORD="${DB_PASSWORD:?missing DB_PASSWORD}"
	export DB_HOST="${DB_HOST:-127.0.0.1}"
	export DB_PORT="${DB_PORT:-5432}"
	export DB_DATABASE="${DB_DATABASE:-dify}"

	export REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
	export REDIS_PORT="${REDIS_PORT:-6379}"
	export REDIS_PASSWORD="${REDIS_PASSWORD:?missing REDIS_PASSWORD}"
	export REDIS_USE_SSL="${REDIS_USE_SSL:-false}"
	export REDIS_DB="${REDIS_DB:-0}"
	local celery_redis_password
	celery_redis_password="$(urlencode_value "${REDIS_PASSWORD}")"
	export CELERY_BROKER_URL="${CELERY_BROKER_URL:-redis://:${celery_redis_password}@${REDIS_HOST}:${REDIS_PORT}/1}"
	export CELERY_BACKEND="${CELERY_BACKEND:-redis}"
	export BROKER_USE_SSL="${BROKER_USE_SSL:-false}"

	export STORAGE_TYPE="${STORAGE_TYPE:-opendal}"
	export OPENDAL_SCHEME="${OPENDAL_SCHEME:-fs}"
	export OPENDAL_FS_ROOT="${OPENDAL_FS_ROOT:-/app/api/storage}"
	export VECTOR_STORE="${VECTOR_STORE:-pgvector}"
	export PGVECTOR_HOST="${PGVECTOR_HOST:-${DB_HOST}}"
	export PGVECTOR_PORT="${PGVECTOR_PORT:-${DB_PORT}}"
	export PGVECTOR_USER="${PGVECTOR_USER:-${DB_USERNAME}}"
	export PGVECTOR_PASSWORD="${PGVECTOR_PASSWORD:-${DB_PASSWORD}}"
	export PGVECTOR_DATABASE="${PGVECTOR_DATABASE:-${DB_DATABASE}}"

	export CODE_EXECUTION_ENDPOINT="${CODE_EXECUTION_ENDPOINT:-http://127.0.0.1:8194}"
	export CODE_EXECUTION_API_KEY="${CODE_EXECUTION_API_KEY:-${SANDBOX_API_KEY:?missing SANDBOX_API_KEY}}"
	export CODE_EXECUTION_SSL_VERIFY="${CODE_EXECUTION_SSL_VERIFY:-True}"
	export SANDBOX_API_KEY="${SANDBOX_API_KEY:?missing SANDBOX_API_KEY}"
	export SANDBOX_GIN_MODE="${SANDBOX_GIN_MODE:-release}"
	export SANDBOX_WORKER_TIMEOUT="${SANDBOX_WORKER_TIMEOUT:-15}"
	export SANDBOX_ENABLE_NETWORK="${SANDBOX_ENABLE_NETWORK:-true}"
	export SANDBOX_HTTP_PROXY="${SANDBOX_HTTP_PROXY:-http://127.0.0.1:3128}"
	export SANDBOX_HTTPS_PROXY="${SANDBOX_HTTPS_PROXY:-http://127.0.0.1:3128}"
	export SANDBOX_PORT="${SANDBOX_PORT:-8194}"

	export SSRF_HTTP_PORT="${SSRF_HTTP_PORT:-3128}"
	export SSRF_REVERSE_PROXY_PORT="${SSRF_REVERSE_PROXY_PORT:-8195}"
	export SSRF_SANDBOX_HOST="${SSRF_SANDBOX_HOST:-127.0.0.1}"
	export SSRF_DEFAULT_TIME_OUT="${SSRF_DEFAULT_TIME_OUT:-5}"
	export SSRF_DEFAULT_CONNECT_TIME_OUT="${SSRF_DEFAULT_CONNECT_TIME_OUT:-5}"
	export SSRF_DEFAULT_READ_TIME_OUT="${SSRF_DEFAULT_READ_TIME_OUT:-5}"
	export SSRF_DEFAULT_WRITE_TIME_OUT="${SSRF_DEFAULT_WRITE_TIME_OUT:-5}"
	export SSRF_PROXY_HTTP_URL="${SSRF_PROXY_HTTP_URL:-http://127.0.0.1:3128}"
	export SSRF_PROXY_HTTPS_URL="${SSRF_PROXY_HTTPS_URL:-http://127.0.0.1:3128}"

	export PLUGIN_DAEMON_PORT="${PLUGIN_DAEMON_PORT:-5002}"
	export PLUGIN_DAEMON_KEY="${PLUGIN_DAEMON_KEY:?missing PLUGIN_DAEMON_KEY}"
	export PLUGIN_DAEMON_URL="${PLUGIN_DAEMON_URL:-http://127.0.0.1:5002}"
	export PLUGIN_DIFY_INNER_API_KEY="${PLUGIN_DIFY_INNER_API_KEY:?missing PLUGIN_DIFY_INNER_API_KEY}"
	export PLUGIN_DIFY_INNER_API_URL="${PLUGIN_DIFY_INNER_API_URL:-http://127.0.0.1:5001}"
	export DB_PLUGIN_DATABASE="${DB_PLUGIN_DATABASE:-dify_plugin}"
	export PLUGIN_STORAGE_TYPE="${PLUGIN_STORAGE_TYPE:-local}"
	export PLUGIN_STORAGE_LOCAL_ROOT="${PLUGIN_STORAGE_LOCAL_ROOT:-/appdata/plugin_daemon}"
	export PLUGIN_WORKING_PATH="${PLUGIN_WORKING_PATH:-/appdata/plugin_daemon/cwd}"
	export PLUGIN_INSTALLED_PATH="${PLUGIN_INSTALLED_PATH:-plugin}"
	export PLUGIN_PACKAGE_CACHE_PATH="${PLUGIN_PACKAGE_CACHE_PATH:-plugin_packages}"
	export PLUGIN_MEDIA_CACHE_PATH="${PLUGIN_MEDIA_CACHE_PATH:-assets}"
	export FORCE_VERIFYING_SIGNATURE="${FORCE_VERIFYING_SIGNATURE:-true}"

	export NGINX_PORT="${NGINX_PORT:-8080}"
	export NGINX_SERVER_NAME="${NGINX_SERVER_NAME:-_}"
	export NGINX_CLIENT_MAX_BODY_SIZE="${NGINX_CLIENT_MAX_BODY_SIZE:-100M}"
	export NGINX_KEEPALIVE_TIMEOUT="${NGINX_KEEPALIVE_TIMEOUT:-65}"
	export NGINX_PROXY_READ_TIMEOUT="${NGINX_PROXY_READ_TIMEOUT:-3600s}"
	export NGINX_PROXY_SEND_TIMEOUT="${NGINX_PROXY_SEND_TIMEOUT:-3600s}"
	export NGINX_WORKER_PROCESSES="${NGINX_WORKER_PROCESSES:-auto}"
	export DIFY_WEB_PORT="${DIFY_WEB_PORT:-3000}"
	export DIFY_WEB_HOST="${DIFY_WEB_HOST:-127.0.0.1}"

	export MARKETPLACE_ENABLED="${MARKETPLACE_ENABLED:-true}"
	export MARKETPLACE_API_URL="${MARKETPLACE_API_URL:-https://marketplace.dify.ai}"
	export MARKETPLACE_URL="${MARKETPLACE_URL:-https://marketplace.dify.ai}"
	export NEXT_PUBLIC_SOCKET_URL="${NEXT_PUBLIC_SOCKET_URL-}"
	export ENABLE_WEBSITE_FIRECRAWL="${ENABLE_WEBSITE_FIRECRAWL:-true}"
	export ENABLE_WEBSITE_JINAREADER="${ENABLE_WEBSITE_JINAREADER:-true}"
	export ENABLE_WEBSITE_WATERCRAWL="${ENABLE_WEBSITE_WATERCRAWL:-true}"

	if [[ -n ${DIFY_AIO_PUBLIC_URL-} ]]; then
		local public_url="${DIFY_AIO_PUBLIC_URL%/}"
		local socket_url="${public_url/http/ws}"
		set_public_url_if_default "CONSOLE_WEB_URL" "${public_url}"
		set_public_url_if_default "CONSOLE_API_URL" "${public_url}"
		set_public_url_if_default "SERVICE_API_URL" "${public_url}"
		set_public_url_if_default "TRIGGER_URL" "${public_url}"
		set_public_url_if_default "APP_WEB_URL" "${public_url}"
		set_public_url_if_default "APP_API_URL" "${public_url}"
		set_public_url_if_default "FILES_URL" "${public_url}"
		set_public_url_if_default "NEXT_PUBLIC_SOCKET_URL" "${socket_url}"
	else
		export CONSOLE_WEB_URL="${CONSOLE_WEB_URL-}"
		export CONSOLE_API_URL="${CONSOLE_API_URL-}"
		export SERVICE_API_URL="${SERVICE_API_URL-}"
		export TRIGGER_URL="${TRIGGER_URL:-http://localhost}"
		export APP_WEB_URL="${APP_WEB_URL-}"
		export APP_API_URL="${APP_API_URL-}"
		export FILES_URL="${FILES_URL-}"
	fi
	export INTERNAL_FILES_URL="${INTERNAL_FILES_URL:-http://127.0.0.1:5001}"
}

configure_plugin_daemon_runtime() {
	export PATH="${PLUGIN_DAEMON_PATH:-/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin}"
	export PYTHON_ENV_INIT_TIMEOUT="${PYTHON_ENV_INIT_TIMEOUT:-${PLUGIN_PYTHON_ENV_INIT_TIMEOUT:-120}}"
	export PYTHON_INTERPRETER_PATH="${PYTHON_INTERPRETER_PATH:-/usr/local/bin/python3.12}"
	export UV_PATH="${UV_PATH:-/usr/local/bin/uv}"
	export PLUGIN_IGNORE_UV_LOCK="${PLUGIN_IGNORE_UV_LOCK:-false}"

	if [[ ! -x ${PYTHON_INTERPRETER_PATH} ]]; then
		aio_log "Plugin daemon Python interpreter is not executable: ${PYTHON_INTERPRETER_PATH}"
		return 1
	fi

	if ! "${PYTHON_INTERPRETER_PATH}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
		aio_log "Plugin daemon Python interpreter must be Python 3.11 or newer: ${PYTHON_INTERPRETER_PATH}"
		return 1
	fi

	if [[ ! -x ${UV_PATH} ]]; then
		aio_log "Plugin daemon uv path is not executable: ${UV_PATH}"
		return 1
	fi

	if ! "${UV_PATH}" --version >/dev/null 2>&1; then
		aio_log "Plugin daemon uv failed to execute: ${UV_PATH}"
		return 1
	fi

	if [[ -z ${PLUGIN_WORKING_PATH-} ]]; then
		aio_log "Plugin daemon working path is not configured."
		return 1
	fi

	if [[ -z ${PLUGIN_STORAGE_LOCAL_ROOT-} ]]; then
		aio_log "Plugin daemon local storage root is not configured."
		return 1
	fi

	if [[ ${UV_CACHE_DIR-} == "" || ${UV_CACHE_DIR} == "/tmp/.uv-cache" ]]; then
		export UV_CACHE_DIR="${PLUGIN_WORKING_PATH}/.uv-cache"
	fi

	mkdir -p "${PLUGIN_STORAGE_LOCAL_ROOT}" "${PLUGIN_WORKING_PATH}" "${UV_CACHE_DIR}"
}
