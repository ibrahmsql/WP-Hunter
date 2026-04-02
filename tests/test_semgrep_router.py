from pathlib import Path

from fastapi.testclient import TestClient

from server.app import create_app


class _DummyRepo:
    def __init__(self):
        self.semgrep_scan_calls = []

    def create_semgrep_scan(self, slug, version=None):
        self.semgrep_scan_calls.append((slug, version))
        return 77

    def get_catalog_latest_version(self, slug, is_theme=False):
        if slug == "akismet" and not is_theme:
            return "5.3.1"
        return None

    def get_semgrep_scan(self, slug):
        if slug == "akismet":
            return {"id": 77, "slug": slug, "status": "completed"}
        return None

    def get_session_results(self, session_id, *args, **kwargs):
        del args, kwargs
        if session_id == 10:
            return [
                {
                    "slug": "akismet",
                    "version": "5.3.1",
                    "download_link": "https://downloads.wordpress.org/plugin/akismet.5.3.1.zip",
                },
                {
                    "slug": "hello-dolly",
                    "version": "1.7.2",
                    "download_link": "https://downloads.wordpress.org/plugin/hello-dolly.1.7.2.zip",
                },
            ]
        return []

    def get_semgrep_stats_for_slugs(self, slugs):
        if not slugs:
            return {
                "scanned_count": 0,
                "total_findings": 0,
                "breakdown": {},
                "running_count": 0,
                "pending_count": 0,
                "failed_count": 0,
                "completed_count": 0,
            }
        return {
            "scanned_count": 1,
            "total_findings": 3,
            "breakdown": {"HIGH": 1, "MEDIUM": 2},
            "running_count": 0,
            "pending_count": 1,
            "failed_count": 0,
            "completed_count": 1,
        }



def _create_client(monkeypatch):
    monkeypatch.setattr(
        "server.app.update_manager.manager.get_status",
        lambda force=False: {"status": "ok", "force": force},
    )
    return TestClient(create_app(), base_url="http://localhost")


def _patch_semgrep_state(monkeypatch, tmp_path: Path):
    from server.routers import semgrep_helpers

    custom_rules_path = tmp_path / "custom_rules.yaml"
    disabled_config_path = tmp_path / "disabled_config.json"
    monkeypatch.setattr(semgrep_helpers, "CUSTOM_RULES_PATH", custom_rules_path)
    monkeypatch.setattr(semgrep_helpers, "DISABLED_CONFIG_PATH", disabled_config_path)


def _patch_semgrep_background_tasks(monkeypatch):
    async def _noop_single(*args, **kwargs):
        del args, kwargs

    async def _noop_bulk(*args, **kwargs):
        del args, kwargs

    monkeypatch.setattr("server.routers.semgrep_service.run_plugin_semgrep_scan", _noop_single)
    monkeypatch.setattr("server.routers.semgrep_service.run_bulk_semgrep_task", _noop_bulk)


def test_semgrep_scan_endpoints_work(monkeypatch):
    from server.routers import semgrep

    repo = _DummyRepo()
    monkeypatch.setattr(semgrep, "repo", repo)
    _patch_semgrep_background_tasks(monkeypatch)

    client = _create_client(monkeypatch)

    start_response = client.post(
        "/api/semgrep/scan",
        json={
            "slug": "akismet",
            "download_url": "https://downloads.wordpress.org/plugin/akismet.5.3.1.zip",
        },
    )
    assert start_response.status_code == 200
    assert start_response.json()["success"] is True

    get_response = client.get("/api/semgrep/scan/akismet")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "completed"


def test_semgrep_rules_and_rulesets_endpoints(monkeypatch, tmp_path):
    _patch_semgrep_state(monkeypatch, tmp_path)
    client = _create_client(monkeypatch)

    rules_response = client.get("/api/semgrep/rules")
    assert rules_response.status_code == 200
    assert "rulesets" in rules_response.json()

    create_rule_response = client.post(
        "/api/semgrep/rules",
        json={
            "id": "custom_eval_rule",
            "pattern": "eval($X)",
            "message": "Avoid eval",
            "severity": "WARNING",
            "languages": ["php"],
        },
    )
    assert create_rule_response.status_code == 200
    assert create_rule_response.json()["success"] is True

    toggle_rule_response = client.post("/api/semgrep/rules/custom_eval_rule/toggle")
    assert toggle_rule_response.status_code == 200
    assert toggle_rule_response.json()["rule_id"] == "custom_eval_rule"

    toggle_all_new = client.post("/api/semgrep/rules/actions/toggle-all", json={"enabled": True})
    assert toggle_all_new.status_code == 200
    assert toggle_all_new.json()["success"] is True

    toggle_all_legacy = client.post("/api/semgrep/rules/toggle-all", json={"enabled": False})
    assert toggle_all_legacy.status_code == 405

    create_ruleset_response = client.post("/api/semgrep/rulesets", json={"ruleset": "r/custom-demo"})
    assert create_ruleset_response.status_code == 200
    assert create_ruleset_response.json()["ruleset_id"] == "r/custom-demo"

    toggle_ruleset_response = client.post("/api/semgrep/rulesets/r/custom-demo/toggle")
    assert toggle_ruleset_response.status_code == 200
    assert toggle_ruleset_response.json()["ruleset_id"] == "r/custom-demo"

    delete_ruleset_response = client.delete("/api/semgrep/rulesets/r/custom-demo")
    assert delete_ruleset_response.status_code == 200
    assert delete_ruleset_response.json()["deleted"] == "r/custom-demo"

    delete_rule_response = client.delete("/api/semgrep/rules/custom_eval_rule")
    assert delete_rule_response.status_code == 200
    assert delete_rule_response.json()["deleted"] == "custom_eval_rule"


def test_semgrep_bulk_endpoints(monkeypatch):
    from server.routers import semgrep
    from server.routers import semgrep_tasks

    repo = _DummyRepo()
    monkeypatch.setattr(semgrep, "repo", repo)
    _patch_semgrep_background_tasks(monkeypatch)
    semgrep_tasks.active_bulk_scans.clear()

    client = _create_client(monkeypatch)

    start_bulk_response = client.post("/api/semgrep/bulk/10")
    assert start_bulk_response.status_code == 200
    assert start_bulk_response.json()["status"] == "started"
    assert start_bulk_response.json()["count"] == 2

    stats_response = client.get("/api/semgrep/bulk/10/stats")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["session_id"] == 10
    assert stats["total_plugins"] == 2
    assert stats["scanned_count"] == 1

    stop_bulk_response = client.post("/api/semgrep/bulk/10/stop")
    assert stop_bulk_response.status_code == 200
    assert stop_bulk_response.json()["status"] == "stopping"


def test_semgrep_scan_rejects_invalid_slug(monkeypatch):
    from server.routers import semgrep

    repo = _DummyRepo()
    monkeypatch.setattr(semgrep, "repo", repo)

    client = _create_client(monkeypatch)
    response = client.post(
        "/api/semgrep/scan",
        json={
            "slug": "..bad-slug",
            "download_url": "https://downloads.wordpress.org/plugin/akismet.5.3.1.zip",
        },
    )

    assert response.status_code == 422
