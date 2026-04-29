#!/command/with-contenv bash
# shellcheck shell=bash
set -euo pipefail

mkdir -p /config/aio

ENV_FILE="/config/aio/generated.env"
touch "${ENV_FILE}"
chown root:appuser /config/aio "${ENV_FILE}"
chmod 750 /config/aio
chmod 640 "${ENV_FILE}"

persist_if_missing() {
	local key="$1"
	local value="$2"
	if grep -q "^${key}=" "${ENV_FILE}"; then
		return
	fi
	printf '%s="%s"\n' "${key}" "${value}" >>"${ENV_FILE}"
}

# Replace these with any first-run secrets your app needs.
if [[ -z ${APP_SECRET_KEY-} ]]; then
	generated_secret="$(openssl rand -hex 64)"
	persist_if_missing "APP_SECRET_KEY" "${generated_secret}"
fi

echo "[aio-template] Generated first-run values are stored at ${ENV_FILE}."
