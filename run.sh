#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="temodar-agent:latest"
CONTAINER_NAME="temodar-agent-app"
PORT="8080"
PLUGIN_RETENTION_DAYS="${TEMODAR_AGENT_PLUGIN_RETENTION_DAYS:-30}"
APP_STATE_DIR="${WORKSPACE_ROOT}/.temodar-agent"
PLUGINS_DIR="${WORKSPACE_ROOT}/Plugins"
SEMGREP_RESULTS_DIR="${WORKSPACE_ROOT}/semgrep_results"
RUNTIME_FILE="${APP_STATE_DIR}/update-runtime.json"
WATCHER_PID_FILE="${APP_STATE_DIR}/host-update-watcher.pid"
WATCHER_STOP_FILE="${APP_STATE_DIR}/host-update-watcher.stop"
WATCHER_SCRIPT="${WORKSPACE_ROOT}/infrastructure/host_update_watcher.sh"

RESET="\033[0m"
BOLD="\033[1m"
CYAN="\033[36m"
GREEN="\033[32m"
YELLOW="\033[33m"
MAGENTA="\033[35m"

mkdir -p "${PLUGINS_DIR}" "${SEMGREP_RESULTS_DIR}" "${APP_STATE_DIR}"

python3 - "$RUNTIME_FILE" "$WORKSPACE_ROOT" "$IMAGE_NAME" "$CONTAINER_NAME" "$PORT" "$APP_STATE_DIR" "$PLUGINS_DIR" "$SEMGREP_RESULTS_DIR" <<'PY'
import json
import sys
from pathlib import Path

runtime_path = Path(sys.argv[1])
runtime_path.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "workspace_root": sys.argv[2],
    "image_name": sys.argv[3],
    "container_name": sys.argv[4],
    "port": sys.argv[5],
    "app_state_path": sys.argv[6],
    "plugins_path": sys.argv[7],
    "semgrep_results_path": sys.argv[8],
}
runtime_path.write_text(json.dumps(payload), encoding="utf-8")
PY

TEMODAR_AGENT_PLUGIN_RETENTION_DAYS="${PLUGIN_RETENTION_DAYS}" python3 - <<'PY'
from pathlib import Path
import os
import shutil
import time

plugins_dir = Path("Plugins")
retention_days_raw = os.environ.get("TEMODAR_AGENT_PLUGIN_RETENTION_DAYS", "30").strip()
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

████████╗███████╗███╗   ███╗ ██████╗ ██████╗  █████╗ ██████╗      █████╗  ██████╗ ███████╗███╗   ██╗████████╗
╚══██╔══╝██╔════╝████╗ ████║██╔═══██╗██╔══██╗██╔══██╗██╔══██╗    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
   ██║   █████╗  ██╔████╔██║██║   ██║██║  ██║███████║██████╔╝    ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
   ██║   ██╔══╝  ██║╚██╔╝██║██║   ██║██║  ██║██╔══██║██╔══██╗    ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
   ██║   ███████╗██║ ╚═╝ ██║╚██████╔╝██████╔╝██║  ██║██║  ██║    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
   ╚═╝   ╚══════╝╚═╝     ╚═╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   

GitHub : https://github.com/xeloxa/temodar-agent
Mail   : alisunbul@proton.me

EOF

remove_container() {
  if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    docker rm -f "${CONTAINER_NAME}" >/dev/null
  fi
}

stop_watcher() {
  touch "${WATCHER_STOP_FILE}"
  if [[ -f "${WATCHER_PID_FILE}" ]]; then
    local watcher_pid
    watcher_pid="$(cat "${WATCHER_PID_FILE}" 2>/dev/null || true)"
    if [[ -n "${watcher_pid}" ]] && kill -0 "${watcher_pid}" 2>/dev/null; then
      wait "${watcher_pid}" 2>/dev/null || true
    fi
    rm -f "${WATCHER_PID_FILE}"
  fi
  rm -f "${WATCHER_STOP_FILE}"
}

start_watcher() {
  rm -f "${WATCHER_STOP_FILE}"
  if [[ -f "${WATCHER_PID_FILE}" ]]; then
    local watcher_pid
    watcher_pid="$(cat "${WATCHER_PID_FILE}" 2>/dev/null || true)"
    if [[ -n "${watcher_pid}" ]] && kill -0 "${watcher_pid}" 2>/dev/null; then
      return
    fi
    rm -f "${WATCHER_PID_FILE}"
  fi
  bash "${WATCHER_SCRIPT}" "${WORKSPACE_ROOT}" >/dev/null 2>&1 &
  echo $! > "${WATCHER_PID_FILE}"
}

build_image() {
  local old_image_id=""
  local new_image_id=""

  old_image_id="$(docker image inspect --format '{{.Id}}' "${IMAGE_NAME}" 2>/dev/null || true)"
  docker build -t "${IMAGE_NAME}" "${WORKSPACE_ROOT}"
  new_image_id="$(docker image inspect --format '{{.Id}}' "${IMAGE_NAME}" 2>/dev/null || true)"

  if [[ -n "${old_image_id}" && -n "${new_image_id}" && "${old_image_id}" != "${new_image_id}" ]]; then
    docker rmi "${old_image_id}" >/dev/null 2>&1 || true
  fi
}

ensure_image_exists() {
  if docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
    printf "${BOLD}${GREEN}Docker image already exists, skipping build.${RESET}\n"
  else
    printf "${BOLD}${YELLOW}Docker image not found, building...${RESET}\n"
    build_image
  fi
}

start_container() {
  docker run -d --name "${CONTAINER_NAME}" \
    -p "${PORT}:8080" \
    --add-host "host.docker.internal:host-gateway" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "${PLUGINS_DIR}:/app/Plugins" \
    -v "${SEMGREP_RESULTS_DIR}:/app/semgrep_results" \
    -v "${APP_STATE_DIR}:/home/appuser/.temodar-agent" \
    "${IMAGE_NAME}" >/dev/null
}

cleanup() {
  stop_watcher
  remove_container
}

trap cleanup EXIT

restart_everything() {
  printf "\n${BOLD}${YELLOW}Restarting everything...${RESET}\n"
  stop_watcher
  remove_container
  build_image
  start_container
  start_watcher
  printf "${BOLD}${GREEN}Restart completed.${RESET}\n"
}

ensure_image_exists
remove_container
start_container
start_watcher

printf "\n${BOLD}${YELLOW}Temodar Agent is running in Docker...${RESET}\n"
printf "${BOLD}${GREEN}Open your browser at:${RESET} ${CYAN}http://127.0.0.1:${PORT}${RESET}\n"
printf "${BOLD}${GREEN}Persistent DB path:${RESET} ${CYAN}./.temodar-agent/temodar_agent.db${RESET}\n"
printf "${BOLD}${GREEN}Plugin cache retention:${RESET} ${CYAN}${PLUGIN_RETENTION_DAYS} day(s)${RESET}\n"
printf "${BOLD}${MAGENTA}Press R to rebuild+restart everything, Q to quit, Ctrl+C to stop.${RESET}\n\n"

while true; do
  read -rsn1 key
  case "${key}" in
    [Rr])
      restart_everything
      ;;
    [Qq])
      printf "\n${BOLD}${YELLOW}Stopping Temodar Agent...${RESET}\n"
      break
      ;;
  esac
done
