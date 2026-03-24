#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="wp-hunter:latest"
CONTAINER_NAME="wp-hunter-app"
PORT="8080"
PLUGIN_RETENTION_DAYS="${WP_HUNTER_PLUGIN_RETENTION_DAYS:-30}"

RESET="\033[0m"
BOLD="\033[1m"
CYAN="\033[36m"
GREEN="\033[32m"
YELLOW="\033[33m"
MAGENTA="\033[35m"

mkdir -p "Plugins" "semgrep_results" ".wp-hunter"

WP_HUNTER_PLUGIN_RETENTION_DAYS="${PLUGIN_RETENTION_DAYS}" python3 - <<'PY'
from pathlib import Path
import os
import shutil
import time

plugins_dir = Path("Plugins")
retention_days_raw = os.environ.get("WP_HUNTER_PLUGIN_RETENTION_DAYS", "30").strip()
try:
    retention_days = max(0, int(retention_days_raw))
except ValueError:
    retention_days = 30

cutoff_ts = time.time() - (retention_days * 86400)
removed = 0

for entry in plugins_dir.iterdir() if plugins_dir.exists() else []:
    if not entry.is_dir():
        continue
    source_dir = entry / "source"
    target = source_dir if source_dir.exists() else entry
    try:
        mtime = target.stat().st_mtime
    except OSError:
        continue
    if mtime < cutoff_ts:
        shutil.rmtree(entry, ignore_errors=True)
        removed += 1

print(f"[cleanup] Removed {removed} plugin cache folder(s) older than {retention_days} day(s).")
PY

cat <<'EOF'

██╗    ██╗██████╗       ██╗  ██╗██╗   ██╗███╗   ██╗████████╗███████╗██████╗
██║    ██║██╔══██╗      ██║  ██║██║   ██║████╗  ██║╚══██╔══╝██╔════╝██╔══██╗
██║ █╗ ██║██████╔╝█████╗███████║██║   ██║██╔██╗ ██║   ██║   █████╗  ██████╔╝
██║███╗██║██╔═══╝ ╚════╝██╔══██║██║   ██║██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗
╚███╔███╔╝██║           ██║  ██║╚██████╔╝██║ ╚████║   ██║   ███████╗██║  ██║
 ╚══╝╚══╝ ╚═╝           ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝

GitHub : https://github.com/xeloxa/wp-hunter
Mail   : alisunbul@proton.me

EOF

remove_container() {
  if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    docker rm -f "${CONTAINER_NAME}" >/dev/null
  fi
}

build_image() {
  docker build -t "${IMAGE_NAME}" .
}

start_container() {
  docker run -d --name "${CONTAINER_NAME}" \
    -p "${PORT}:8080" \
    --add-host "host.docker.internal:host-gateway" \
    -v "$(pwd)/Plugins:/app/Plugins" \
    -v "$(pwd)/semgrep_results:/app/semgrep_results" \
    -v "$(pwd)/.wp-hunter:/home/appuser/.wp-hunter" \
    "${IMAGE_NAME}" >/dev/null
}

cleanup() {
  remove_container
}

trap cleanup EXIT

restart_everything() {
  printf "\n${BOLD}${YELLOW}Restarting everything...${RESET}\n"
  remove_container
  build_image
  start_container
  printf "${BOLD}${GREEN}Restart completed.${RESET}\n"
}

build_image
remove_container
start_container

printf "\n${BOLD}${YELLOW}WP-Hunter is running in Docker...${RESET}\n"
printf "${BOLD}${GREEN}Open your browser at:${RESET} ${CYAN}http://127.0.0.1:${PORT}${RESET}\n"
printf "${BOLD}${GREEN}Persistent DB path:${RESET} ${CYAN}./.wp-hunter/wp_hunter.db${RESET}\n"
printf "${BOLD}${GREEN}Plugin cache retention:${RESET} ${CYAN}${PLUGIN_RETENTION_DAYS} day(s)${RESET}\n"
printf "${BOLD}${MAGENTA}Press R to rebuild+restart everything, Q to quit, Ctrl+C to stop.${RESET}\n\n"

while true; do
  read -rsn1 key
  case "${key}" in
    [Rr])
      restart_everything
      ;;
    [Qq])
      printf "\n${BOLD}${YELLOW}Stopping WP-Hunter...${RESET}\n"
      break
      ;;
  esac
done
