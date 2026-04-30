#!/command/with-contenv bash
# shellcheck shell=bash
set -euo pipefail

# shellcheck source=/dev/null
. /opt/dify-aio/lib/env.sh

mkdir -p \
	"${AIO_CONFIG_DIR}" \
	/appdata/logs \
	/appdata/nginx \
	/appdata/plugin_daemon \
	/appdata/postgres \
	/appdata/redis \
	/appdata/sandbox/conf \
	/appdata/sandbox/dependencies \
	/appdata/storage \
	/run/postgresql

touch "${AIO_ENV_FILE}"
touch "${DIFY_AIO_EXTRA_ENV_FILE:-/appdata/config/extra.env}"
chmod 700 "${AIO_CONFIG_DIR}"
chmod 600 "${AIO_ENV_FILE}"
chmod 600 "${DIFY_AIO_EXTRA_ENV_FILE:-/appdata/config/extra.env}"

persist_secret_if_unset "SECRET_KEY"
persist_secret_if_unset "DB_PASSWORD"
persist_secret_if_unset "REDIS_PASSWORD"
persist_secret_if_unset "SANDBOX_API_KEY"
persist_secret_if_unset "PLUGIN_DAEMON_KEY"
persist_secret_if_unset "PLUGIN_DIFY_INNER_API_KEY"

load_generated_env
configure_dify_env

rm -rf /app/api/storage
ln -sfn /appdata/storage /app/api/storage

cp -n /opt/dify-sandbox/conf/config.yaml /appdata/sandbox/conf/config.yaml 2>/dev/null || true
cp -n /opt/dify-sandbox/dependencies/python-requirements.txt /appdata/sandbox/dependencies/python-requirements.txt 2>/dev/null || true
rm -rf /conf /dependencies
ln -sfn /appdata/sandbox/conf /conf
ln -sfn /appdata/sandbox/dependencies /dependencies

chown -R dify:dify /appdata/storage /appdata/plugin_daemon /app/api/storage /opt/dify-web
chown -R postgres:postgres /appdata/postgres /run/postgresql
chown -R proxy:proxy /var/log/squid /var/spool/squid
chmod 700 /appdata/postgres

aio_log "Generated first-run secrets are stored at ${AIO_ENV_FILE}."
aio_log "Runtime preflight complete."
