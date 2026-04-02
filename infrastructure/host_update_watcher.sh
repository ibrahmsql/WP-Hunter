#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STATE_DIR="${WORKSPACE_ROOT}/.temodar-agent"
STATE_FILE="${STATE_DIR}/update_state.json"
RUNTIME_FILE="${STATE_DIR}/update-runtime.json"
STOP_FILE="${STATE_DIR}/host-update-watcher.stop"
LOCK_DIR="${STATE_DIR}/host-update-watcher.lock"
LOG_FILE="${STATE_DIR}/host-update-watcher.log"
UPDATE_SCRIPT="${WORKSPACE_ROOT}/infrastructure/update_docker_install.sh"
POLL_INTERVAL="${TEMODAR_AGENT_UPDATE_WATCHER_INTERVAL:-2}"

mkdir -p "${STATE_DIR}"

log() {
  printf '[host-update-watcher] %s\n' "$1" >>"${LOG_FILE}"
}

state_field() {
  local field="$1"
  python3 - "$STATE_FILE" "$field" <<'PY'
import json
import sys
from pathlib import Path

state_path = Path(sys.argv[1])
field = sys.argv[2]
if not state_path.exists():
    print("")
    raise SystemExit(0)
try:
    raw = json.loads(state_path.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
value = raw.get(field, "") if isinstance(raw, dict) else ""
if value is None:
    value = ""
print(value)
PY
}

runtime_exports() {
  python3 - "$RUNTIME_FILE" <<'PY'
import json
import shlex
import sys
from pathlib import Path

runtime_path = Path(sys.argv[1])
if not runtime_path.exists():
    raise SystemExit(1)
raw = json.loads(runtime_path.read_text(encoding="utf-8"))
for env_name, key in [
    ("TEMODAR_AGENT_IMAGE_NAME", "image_name"),
    ("TEMODAR_AGENT_CONTAINER_NAME", "container_name"),
    ("TEMODAR_AGENT_PORT", "port"),
    ("TEMODAR_AGENT_PLUGINS_PATH", "plugins_path"),
    ("TEMODAR_AGENT_SEMGREP_RESULTS_PATH", "semgrep_results_path"),
    ("TEMODAR_AGENT_APP_STATE_PATH", "app_state_path"),
]:
    value = raw.get(key, "")
    print(f'export {env_name}={shlex.quote(str(value))}')
PY
}

cleanup() {
  rm -rf "${LOCK_DIR}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

log "Watcher started for ${WORKSPACE_ROOT}"

while true; do
  if [[ -f "${STOP_FILE}" ]]; then
    log "Stop file detected; exiting watcher."
    break
  fi

  if [[ ! -f "${STATE_FILE}" || ! -f "${RUNTIME_FILE}" ]]; then
    sleep "${POLL_INTERVAL}"
    continue
  fi

  status="$(state_field last_update_status)"
  in_progress="$(state_field update_in_progress)"
  request_id="$(state_field request_id)"
  handled_request_id="$(state_field handled_request_id)"
  latest_tag="$(state_field latest_requested_tag)"

  if [[ "${status}" == "requested" && "${in_progress}" == "True" || "${in_progress}" == "true" ]]; then
    if [[ -n "${request_id}" && "${request_id}" != "${handled_request_id}" ]]; then
      if mkdir "${LOCK_DIR}" 2>/dev/null; then
        log "Handling request ${request_id} for tag ${latest_tag:-<none>}"
        {
          eval "$(runtime_exports)"
          export TEMODAR_AGENT_WORKSPACE_ROOT="${WORKSPACE_ROOT}"
          export TEMODAR_AGENT_LATEST_TAG="${latest_tag}"
          export TEMODAR_AGENT_HANDLED_REQUEST_ID="${request_id}"
          bash "${UPDATE_SCRIPT}"
        } >>"${LOG_FILE}" 2>&1 || log "Update script failed for request ${request_id}"
        rm -rf "${LOCK_DIR}" >/dev/null 2>&1 || true
      fi
    fi
  fi

  sleep "${POLL_INTERVAL}"
done
