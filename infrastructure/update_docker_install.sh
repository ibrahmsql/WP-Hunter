#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${TEMODAR_AGENT_APP_STATE_PATH:-/runtime-state}"
STATE_FILE="${STATE_DIR}/update_state.json"
LOCK_DIR="${STATE_DIR}/update.lock"
WORKSPACE_ROOT="${TEMODAR_AGENT_WORKSPACE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
IMAGE_NAME="${TEMODAR_AGENT_IMAGE_NAME:-temodar-agent:latest}"
CONTAINER_NAME="${TEMODAR_AGENT_CONTAINER_NAME:-temodar-agent-app}"
PORT="${TEMODAR_AGENT_PORT:-8080}"
PLUGINS_PATH="${TEMODAR_AGENT_PLUGINS_PATH:-${WORKSPACE_ROOT}/Plugins}"
SEMGREP_RESULTS_PATH="${TEMODAR_AGENT_SEMGREP_RESULTS_PATH:-${WORKSPACE_ROOT}/semgrep_results}"
APP_STATE_PATH="${TEMODAR_AGENT_APP_STATE_PATH:-${WORKSPACE_ROOT}/.temodar-agent}"
LATEST_TAG="${TEMODAR_AGENT_LATEST_TAG:-}"
HOST_GATEWAY="host.docker.internal:host-gateway"
UPDATE_FINISHED="false"

mkdir -p "${STATE_DIR}"

python_update_state() {
  local in_progress="$1"
  local progress_message="$2"
  local last_error="$3"
  local last_update_message="$4"
  local installed_tag="$5"
  local status="${6:-}"
  python3 - "$STATE_FILE" "$in_progress" "$progress_message" "$last_error" "$last_update_message" "$installed_tag" "$LATEST_TAG" "$status" "$TEMODAR_AGENT_HANDLED_REQUEST_ID" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


state_path = Path(sys.argv[1])
in_progress = sys.argv[2] == "true"
progress_message = sys.argv[3]
last_error = sys.argv[4] or None
last_update_message = sys.argv[5] or None
installed_tag = sys.argv[6] or None
latest_tag = sys.argv[7] or None
status = sys.argv[8] or None
handled_request_id = sys.argv[9] or None

try:
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    if not isinstance(state, dict):
        state = {}
except Exception:
    state = {}

state["update_in_progress"] = in_progress
state["progress_message"] = progress_message
state["last_error"] = last_error
state["last_update_message"] = last_update_message
state["update_completed_at"] = utc_timestamp()
if latest_tag:
    state["latest_requested_tag"] = latest_tag
if status:
    state["last_update_status"] = status
if handled_request_id:
    state["handled_request_id"] = handled_request_id
if installed_tag:
    state["installed_release_tag"] = installed_tag
    state["installed_at"] = utc_timestamp()

state_path.write_text(json.dumps(state), encoding="utf-8")
PY
}

progress() {
  python_update_state true "$1" "" "" "" "running"
}

fail_update() {
  local message="$1"
  UPDATE_FINISHED="true"
  python_update_state false "" "$message" "" "" "failed"
  rm -rf "${LOCK_DIR}" >/dev/null 2>&1 || true
  exit 1
}

succeed_update() {
  local message="$1"
  UPDATE_FINISHED="true"
  python_update_state false "" "" "$message" "$LATEST_TAG" "succeeded"
  rm -rf "${LOCK_DIR}" >/dev/null 2>&1 || true
}

cleanup_on_exit() {
  local code=$?
  if [[ $code -ne 0 && "${UPDATE_FINISHED}" != "true" ]]; then
    python_update_state false "" "Update helper exited unexpectedly (code ${code})." "" "" "failed"
  fi
  rm -rf "${LOCK_DIR}" >/dev/null 2>&1 || true
}
trap cleanup_on_exit EXIT

if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  fail_update "Another Docker update is already running."
fi

command -v git >/dev/null 2>&1 || fail_update "git is not available in the helper environment."
command -v docker >/dev/null 2>&1 || fail_update "docker is not available in the helper environment."

progress "Fetching latest source code…"
cd "${WORKSPACE_ROOT}"

if [[ ! -d .git ]]; then
  fail_update "Workspace is not a git checkout; Docker update requires a git repository."
fi

current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
if [[ -z "${current_branch}" || "${current_branch}" == "HEAD" ]]; then
  current_branch="main"
fi

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  fail_update "Update blocked: local code changes are present in the Temodar Agent checkout. Commit/stash them first, then retry the Docker update."
fi

git fetch --tags origin || fail_update "git fetch failed."

behind_ahead="$(git rev-list --left-right --count "origin/${current_branch}...HEAD" 2>/dev/null || echo '')"
if [[ -n "${behind_ahead}" ]]; then
  behind_count="${behind_ahead%%$'\t'*}"
  ahead_count="${behind_ahead##*$'\t'}"
  if [[ "${behind_count}" != "0" && "${ahead_count}" != "0" ]]; then
    fail_update "Update blocked: local branch has diverged from origin/${current_branch}. Reconcile local commits before running the in-app Docker update."
  fi
fi

git pull --ff-only origin "${current_branch}" || fail_update "git pull failed. Local branch could not be fast-forwarded."

progress "Building fresh Docker image…"
docker build -t "${IMAGE_NAME}" "${WORKSPACE_ROOT}" || fail_update "docker build failed."

progress "Stopping current container…"
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

progress "Starting updated container…"
docker run -d --name "${CONTAINER_NAME}" \
  -p "${PORT}:8080" \
  --add-host "${HOST_GATEWAY}" \
  -v "${PLUGINS_PATH}:/app/Plugins" \
  -v "${SEMGREP_RESULTS_PATH}:/app/semgrep_results" \
  -v "${APP_STATE_PATH}:/home/appuser/.temodar-agent" \
  "${IMAGE_NAME}" >/dev/null || fail_update "Failed to start updated container."

progress "Waiting for health check…"
python3 - "$PORT" <<'PY' || fail_update "Health check failed after container restart."
import sys
import time
import urllib.request

port = sys.argv[1]
url = f"http://127.0.0.1:{port}/api/system/update"
last_error = None
for _ in range(45):
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            if 200 <= resp.status < 500:
                raise SystemExit(0)
    except Exception as exc:
        last_error = exc
        time.sleep(2)
raise SystemExit(str(last_error or "unknown health check error"))
PY

succeed_update "Update complete. Docker image rebuilt and container restarted successfully."
