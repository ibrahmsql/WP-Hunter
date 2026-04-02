import json
from pathlib import Path

from server.update_manager import UpdateManager


class _TestUpdateManager(UpdateManager):
    def __init__(self, state_dir: Path):
        self._test_state_dir = state_dir
        super().__init__()

    @property
    def state_dir(self) -> Path:
        self._test_state_dir.mkdir(parents=True, exist_ok=True)
        return self._test_state_dir


def _write_runtime_file(manager: UpdateManager):
    runtime_file = manager.runtime_file
    runtime_file.write_text(
        json.dumps(
            {
                "workspace_root": "/workspace",
                "image_name": "temodar-agent:latest",
                "container_name": "temodar-agent-app",
                "port": "8080",
                "app_state_path": "/state",
                "plugins_path": "/workspace/Plugins",
                "semgrep_results_path": "/workspace/semgrep_results",
            }
        ),
        encoding="utf-8",
    )
    return runtime_file


def test_status_works_when_runtime_metadata_exists(monkeypatch, tmp_path):
    manager = _TestUpdateManager(tmp_path / ".temodar-agent")
    _write_runtime_file(manager)
    monkeypatch.setattr(manager, "_is_running_in_docker", lambda: True)
    monkeypatch.setattr(
        manager,
        "_resolve_release_for_status",
        lambda force: {"tag_name": None, "update_available": False},
    )

    status = manager.get_status()

    assert status["current_version"]


def test_start_update_queues_host_request_for_docker_managed_install(monkeypatch, tmp_path):
    manager = _TestUpdateManager(tmp_path / ".temodar-agent")
    _write_runtime_file(manager)
    monkeypatch.setattr(manager, "_is_running_in_docker", lambda: True)
    monkeypatch.setattr(
        manager,
        "get_status",
        lambda force=True: {"update_available": True, "latest_version": "v9.9.9"},
    )

    called = {}

    def _fake_start(latest_tag):
        called["tag"] = latest_tag
        return "started"

    monkeypatch.setattr(manager, "_start_docker_update", _fake_start)

    result = manager.start_update()

    assert result == "started"
    assert called == {"tag": "v9.9.9"}


def test_start_docker_update_persists_host_request(tmp_path):
    manager = _TestUpdateManager(tmp_path / ".temodar-agent")
    _write_runtime_file(manager)

    message = manager._start_docker_update("v2.1.0")
    state = json.loads(manager.state_file.read_text(encoding="utf-8"))

    assert "Host supervisor" in message
    assert state["update_in_progress"] is True
    assert state["last_update_status"] == "requested"
    assert state["latest_requested_tag"] == "v2.1.0"
    assert state["requested_version"] == "v2.1.0"
    assert state["request_id"]
    assert "Host supervisor" in state["last_update_message"]
