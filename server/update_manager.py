"""
Automatic updater for the Temodar Agent dashboard.

Supports Docker-managed source updates for installations started via ./run.sh.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from app_meta import __version__

logger = logging.getLogger("temodar_agent.update")


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(UTC)


def utc_timestamp() -> str:
    """Return an ISO8601 UTC timestamp with a trailing Z suffix."""
    return utc_now().isoformat().replace("+00:00", "Z")


class UpdateStateStore:
    """Persist updater state under the user home directory."""

    def __init__(self, state_file: Path):
        self.state_file = state_file

    def load(self) -> Dict[str, Any]:
        try:
            if not self.state_file.exists():
                return {}
            with self.state_file.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            if not isinstance(raw, dict):
                return {}
            return dict(raw)
        except Exception:
            logger.warning("Failed to load updater state file.", exc_info=True)
            return {}

    def save(self, state: Dict[str, Any]) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with self.state_file.open("w", encoding="utf-8") as handle:
                json.dump(state, handle)
        except Exception:
            logger.warning("Failed to persist updater state file.", exc_info=True)

    def merge(self, **fields: Any) -> Dict[str, Any]:
        state = self.load()
        for key, value in fields.items():
            if value is None:
                state.pop(key, None)
            else:
                state[key] = value
        self.save(state)
        return state

    def mark_update_started(self, *, progress_message: str, latest_tag: str = "") -> None:
        self.merge(
            update_in_progress=True,
            progress_message=progress_message,
            last_error=None,
            last_update_message=None,
            latest_requested_tag=latest_tag or None,
            update_started_at=utc_timestamp(),
            update_completed_at=None,
        )

    def mark_update_failed(self, error_message: str) -> None:
        self.merge(
            update_in_progress=False,
            progress_message="",
            last_error=error_message,
            last_update_message=None,
            update_completed_at=utc_timestamp(),
        )



class ReleaseMetadataService:
    """Release metadata fetching, normalization, and validation."""

    def __init__(
        self,
        *,
        release_api_url: str,
        allowed_release_hosts: set[str],
        current_version: str,
    ) -> None:
        self.release_api_url = release_api_url
        self.allowed_release_hosts = allowed_release_hosts
        self.current_version = current_version

    def normalized_version(self, version: Optional[str]) -> Tuple[int, ...]:
        if not version:
            return ()
        cleaned = version.strip().lstrip("vV")
        parts = cleaned.replace("-", ".").replace("_", ".").split(".")
        nums: List[int] = []
        for part in parts:
            digits = "".join(ch for ch in part if ch.isdigit())
            nums.append(int(digits) if digits else 0)
        return tuple(nums)

    def is_newer_release(self, latest_version: Optional[str]) -> bool:
        current_tuple = self.normalized_version(self.current_version)
        latest_tuple = self.normalized_version(latest_version)
        if not latest_tuple:
            return False
        length = max(len(current_tuple), len(latest_tuple))
        current_tuple += (0,) * (length - len(current_tuple))
        latest_tuple += (0,) * (length - len(latest_tuple))
        return latest_tuple > current_tuple

    def release_headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Temodar Agent Update Agent",
        }

    def choose_asset(self, assets: list, fallback_url: Optional[str]) -> Dict[str, Any]:
        if assets:
            preferred = next(
                (a for a in assets if str(a.get("name", "")).lower().endswith(".zip")),
                None,
            )
            chosen = preferred or assets[0]
            return {
                "name": chosen.get("name"),
                "size": chosen.get("size"),
                "browser_download_url": chosen.get("browser_download_url"),
                "url": chosen.get("url"),
            }
        return {
            "name": (fallback_url and Path(urlparse(fallback_url).path).name)
            or "source-archive",
            "size": None,
            "browser_download_url": fallback_url,
            "url": fallback_url,
        }

    def build_release_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        assets = data.get("assets") or []
        asset = self.choose_asset(assets, data.get("zipball_url"))
        download_url = (
            data.get("zipball_url")
            or asset.get("browser_download_url")
            or asset.get("url")
        )
        return {
            "tag_name": data.get("tag_name"),
            "name": data.get("name") or data.get("tag_name"),
            "body": data.get("body") or "",
            "published_at": data.get("published_at"),
            "html_url": data.get("html_url"),
            "zipball_url": data.get("zipball_url"),
            "asset_name": asset.get("name"),
            "asset_size": asset.get("size"),
            "asset_url": asset.get("browser_download_url") or asset.get("url"),
            "download_url": download_url,
            "update_available": self.is_newer_release(data.get("tag_name")),
        }

    def empty_release_payload(self) -> Dict[str, Any]:
        return {
            "tag_name": None,
            "name": None,
            "body": "",
            "published_at": None,
            "html_url": None,
            "zipball_url": None,
            "asset_name": None,
            "asset_size": None,
            "asset_url": None,
            "download_url": None,
            "update_available": False,
        }

    def fetch_release(self) -> Dict[str, Any]:
        response = requests.get(
            self.release_api_url,
            headers=self.release_headers(),
            timeout=15,
        )
        response.raise_for_status()
        return self.build_release_payload(response.json())


class UpdateManager:
    RELEASE_API_URL = "https://api.github.com/repos/xeloxa/temodar-agent/releases/latest"
    CHECK_INTERVAL = timedelta(minutes=30)
    ALLOWED_RELEASE_HOSTS = {
        "api.github.com",
        "github.com",
        "codeload.github.com",
        "objects.githubusercontent.com",
        "github-releases.githubusercontent.com",
        "release-assets.githubusercontent.com",
    }
    STATE_FILE_NAME = "update_state.json"
    RUNTIME_FILE_NAME = "update-runtime.json"
    DOCKER_RUNTIME_REQUIRED_FIELDS = (
        "workspace_root",
        "app_state_path",
        "plugins_path",
        "semgrep_results_path",
        "image_name",
        "container_name",
        "port",
    )
    ERROR_NON_DOCKER_INSTALL = (
        "This installation does not expose Docker runtime metadata. "
        "Start Temodar Agent via ./run.sh to use in-app updates."
    )
    ERROR_NO_NEW_RELEASE = "No newer release is available right now."
    MESSAGE_QUEUE_DOCKER_REBUILD = "Queueing Docker rebuild request…"
    MESSAGE_DOCKER_UPDATE_PROGRESS = (
        "Update request accepted. Waiting for host to rebuild and restart "
        "the Docker container…"
    )
    MESSAGE_DOCKER_UPDATE_STATE = (
        "Docker update requested. Host supervisor will pull source, rebuild "
        "the image, and restart the container."
    )
    MESSAGE_DOCKER_UPDATE_ACCEPTED = (
        "Docker update request accepted. Host supervisor will rebuild and "
        "restart the container shortly."
    )

    def __init__(self) -> None:
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_time: Optional[datetime] = None
        self._lock = threading.Lock()
        self._in_progress = False
        self._progress_message: str = ""
        self._last_error: Optional[str] = None
        self._last_update_message: Optional[str] = None
        self._startup_auto_check_done = False
        self._state_store = UpdateStateStore(self.state_file)
        self._release_metadata = ReleaseMetadataService(
            release_api_url=self.RELEASE_API_URL,
            allowed_release_hosts=self.ALLOWED_RELEASE_HOSTS,
            current_version=__version__,
        )

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    @property
    def state_dir(self) -> Path:
        state_dir = Path.home() / ".temodar-agent"
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir

    @property
    def state_file(self) -> Path:
        return self.state_dir / self.STATE_FILE_NAME

    @property
    def runtime_file(self) -> Path:
        return self.state_dir / self.RUNTIME_FILE_NAME

    def _is_running_in_docker(self) -> bool:
        return Path("/.dockerenv").exists()

    def _load_runtime_metadata(self) -> Dict[str, Any]:
        try:
            if not self.runtime_file.exists():
                return {}
            with self.runtime_file.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            return raw if isinstance(raw, dict) else {}
        except Exception:
            logger.warning("Failed to load update runtime metadata.", exc_info=True)
            return {}

    def _validate_docker_runtime_metadata(self, runtime: Dict[str, Any]) -> List[str]:
        return [
            field
            for field in self.DOCKER_RUNTIME_REQUIRED_FIELDS
            if not runtime.get(field)
        ]

    def _is_docker_managed_install(self) -> bool:
        runtime = self._load_runtime_metadata()
        missing = self._validate_docker_runtime_metadata(runtime)
        return self._is_running_in_docker() and not missing

    def _read_persistent_runtime_state(self) -> Dict[str, Any]:
        state = self._state_store.load()
        return {
            "in_progress": bool(state.get("update_in_progress")),
            "progress_message": str(state.get("progress_message") or ""),
            "last_error": state.get("last_error"),
            "last_update_message": state.get("last_update_message"),
        }

    def _fetch_release(self, force: bool = False) -> Dict[str, Any]:
        with self._lock:
            now = utc_now()
            if (
                not force
                and self._cache
                and self._cache_time
                and (now - self._cache_time) < self.CHECK_INTERVAL
            ):
                return self._cache

        release_info = self._release_metadata.fetch_release()
        with self._lock:
            self._cache = release_info
            self._cache_time = now
        return release_info

    def _empty_release_payload(self) -> Dict[str, Any]:
        return self._release_metadata.empty_release_payload()

    def _snapshot_runtime_state(self) -> Dict[str, Any]:
        with self._lock:
            memory_state = {
                "in_progress": self._in_progress,
                "progress_message": self._progress_message,
                "last_error": self._last_error,
                "last_update_message": self._last_update_message,
                "cache": self._cache,
            }
        persisted = self._read_persistent_runtime_state()
        return {
            "in_progress": memory_state["in_progress"] or persisted["in_progress"],
            "progress_message": persisted["progress_message"] or memory_state["progress_message"],
            "last_error": persisted["last_error"] or memory_state["last_error"],
            "last_update_message": persisted["last_update_message"] or memory_state["last_update_message"],
            "cache": memory_state["cache"],
        }

    def _resolve_release_for_status(self, force: bool) -> Dict[str, Any]:
        release: Optional[Dict[str, Any]] = None
        should_fetch = force
        if not force:
            with self._lock:
                if not self._startup_auto_check_done:
                    self._startup_auto_check_done = True
                    should_fetch = True

        if should_fetch:
            try:
                release = self._fetch_release(force)
                self._last_error = None
            except Exception as exc:
                self._last_error = f"{type(exc).__name__}: {exc}"
                logger.warning("Unable to refresh release info: %s", exc)
                cached_release = self._snapshot_runtime_state()["cache"]
                if cached_release:
                    release = cached_release
                elif force:
                    raise
                else:
                    release = self._empty_release_payload()
        else:
            release = self._snapshot_runtime_state()["cache"] or self._empty_release_payload()
        return release

    def _build_status_payload(self, release: Dict[str, Any]) -> Dict[str, Any]:
        runtime_state = self._snapshot_runtime_state()
        state = self._state_store.load()
        installed_tag = state.get("installed_release_tag")
        latest_tag = release.get("tag_name")
        already_installed = bool(
            installed_tag
            and latest_tag
            and self._release_metadata.normalized_version(str(installed_tag))
            == self._release_metadata.normalized_version(str(latest_tag))
        )
        update_available = bool(release.get("update_available")) and not already_installed
        checked_at = self._cache_time.isoformat().replace("+00:00", "Z") if self._cache_time else None
        return {
            "current_version": __version__,
            "latest_version": release.get("tag_name"),
            "release_name": release.get("name"),
            "release_notes": release.get("body"),
            "release_url": release.get("html_url"),
            "release_published_at": release.get("published_at"),
            "asset_name": release.get("asset_name"),
            "asset_size": release.get("asset_size"),
            "asset_url": release.get("asset_url"),
            "download_url": release.get("download_url"),
            "zipball_url": release.get("zipball_url"),
            "update_available": update_available,
            "already_installed_release": already_installed,
            "installed_release_tag": installed_tag,
            "checked_at": checked_at,
            "in_progress": runtime_state["in_progress"],
            "progress_message": runtime_state["progress_message"],
            "last_error": runtime_state["last_error"],
            "last_update_message": runtime_state["last_update_message"],
        }

    def get_status(self, force: bool = False) -> Dict[str, Any]:
        release = self._resolve_release_for_status(force)
        return self._build_status_payload(release)

    def _reset_in_progress_state(self) -> None:
        with self._lock:
            self._in_progress = False
            self._progress_message = ""

    def _mark_update_started(self, progress_message: str, latest_tag: str = "") -> None:
        with self._lock:
            if self._in_progress:
                raise RuntimeError("An update is already running")
            self._in_progress = True
            self._progress_message = progress_message
            self._last_error = None
            self._last_update_message = None
        self._state_store.mark_update_started(
            progress_message=progress_message,
            latest_tag=latest_tag,
        )

    def _start_docker_update(self, latest_tag: str) -> str:
        runtime = self._load_runtime_metadata()
        missing = self._validate_docker_runtime_metadata(runtime)
        if missing:
            raise RuntimeError(
                "Docker update runtime metadata is incomplete: " + ", ".join(missing)
            )

        request_id = utc_now().strftime("%Y%m%d%H%M%S")
        self._state_store.merge(
            update_in_progress=True,
            progress_message=self.MESSAGE_DOCKER_UPDATE_PROGRESS,
            last_error=None,
            last_update_message=self.MESSAGE_DOCKER_UPDATE_STATE,
            latest_requested_tag=latest_tag or None,
            requested_version=latest_tag or None,
            requested_at=utc_timestamp(),
            request_id=request_id,
            last_update_status="requested",
            update_completed_at=None,
        )
        return self.MESSAGE_DOCKER_UPDATE_ACCEPTED

    def _resolve_latest_tag_for_update(self) -> str:
        if not self._is_docker_managed_install():
            raise RuntimeError(self.ERROR_NON_DOCKER_INSTALL)

        release_status = self.get_status(force=True)
        if not release_status.get("update_available"):
            raise RuntimeError(self.ERROR_NO_NEW_RELEASE)
        return str(release_status.get("latest_version") or "")

    def start_update(self) -> str:
        latest_tag = self._resolve_latest_tag_for_update()
        self._mark_update_started(self.MESSAGE_QUEUE_DOCKER_REBUILD, latest_tag)
        try:
            return self._start_docker_update(latest_tag)
        except Exception as exc:
            self._state_store.mark_update_failed(f"{type(exc).__name__}: {exc}")
            self._reset_in_progress_state()
            raise


manager = UpdateManager()
