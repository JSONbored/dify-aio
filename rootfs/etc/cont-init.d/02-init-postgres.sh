#!/command/with-contenv bash
# shellcheck shell=bash
set -euo pipefail

# Optional example hook for repos that embed PostgreSQL inside the AIO image.
# Remove this file if the derived app does not need an internal database.
echo "[aio-template] Customize or remove 02-init-postgres.sh for the derived app."
