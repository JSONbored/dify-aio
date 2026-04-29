#!/command/with-contenv bash
# shellcheck shell=bash
# shellcheck disable=SC2312
set -euo pipefail

# shellcheck source=/dev/null
. /opt/dify-aio/lib/env.sh
load_generated_env
configure_dify_env

if ! is_true "${DIFY_USE_INTERNAL_POSTGRES:-true}"; then
	aio_log "External PostgreSQL mode enabled; skipping bundled PostgreSQL initialization."
	exit 0
fi

PG_VERSION="$(find /usr/lib/postgresql -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort -V | tail -n1)"
PG_BIN="/usr/lib/postgresql/${PG_VERSION}/bin"
PGDATA="/appdata/postgres"
PGUSER="${DB_USERNAME}"
PGPASS="${DB_PASSWORD}"
PGDB="${DB_DATABASE}"
PLUGIN_DB="${DB_PLUGIN_DATABASE}"
PGPASS_SQL="${PGPASS//\'/\'\'}"

mkdir -p "${PGDATA}" /run/postgresql
chown -R postgres:postgres "${PGDATA}" /run/postgresql
chmod 700 "${PGDATA}"

if [[ -z "$(find "${PGDATA}" -mindepth 1 -maxdepth 1 2>/dev/null | head -n1)" ]]; then
	aio_log "Initializing bundled PostgreSQL database."
	su postgres -s /bin/sh -c "\"${PG_BIN}/initdb\" -D \"${PGDATA}\" --auth-local=peer --auth-host=scram-sha-256 >/dev/null"
fi

if ! su postgres -s /bin/sh -c "\"${PG_BIN}/pg_ctl\" -D \"${PGDATA}\" status" >/dev/null 2>&1; then
	su postgres -s /bin/sh -c "\"${PG_BIN}/pg_ctl\" -D \"${PGDATA}\" -w start >/dev/null"
fi

su postgres -s /bin/sh -c "psql -v ON_ERROR_STOP=1 -c \"DO \\\$\\\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='${PGUSER}') THEN CREATE ROLE ${PGUSER} LOGIN PASSWORD '${PGPASS_SQL}'; ELSE ALTER ROLE ${PGUSER} WITH LOGIN PASSWORD '${PGPASS_SQL}'; END IF; END \\\$\\\$;\" >/dev/null"

for database in "${PGDB}" "${PLUGIN_DB}"; do
	su postgres -s /bin/sh -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='${database}'\" | grep -q 1" ||
		su postgres -s /bin/sh -c "createdb -O \"${PGUSER}\" \"${database}\""
done

su postgres -s /bin/sh -c "psql -d \"${PGDB}\" -c \"CREATE EXTENSION IF NOT EXISTS vector;\" >/dev/null"

su postgres -s /bin/sh -c "\"${PG_BIN}/pg_ctl\" -D \"${PGDATA}\" -m fast -w stop >/dev/null"
aio_log "Bundled PostgreSQL is initialized."
