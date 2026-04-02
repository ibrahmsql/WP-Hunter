from fastapi.testclient import TestClient

from server.app import create_app


class _DummyRepo:
    def __init__(self):
        self.calls = []

    def get_catalog_plugins(self, **kwargs):
        self.calls.append(("get_catalog_plugins", kwargs))
        return {"items": [{"slug": "akismet"}], "total": 1}

    def get_catalog_plugin_sessions(self, **kwargs):
        self.calls.append(("get_catalog_plugin_sessions", kwargs))
        return [{"session_id": 7, "score": 90}]

    def get_favorites(self):
        self.calls.append(("get_favorites", {}))
        return [{"slug": "akismet"}]

    def add_favorite(self, payload):
        self.calls.append(("add_favorite", payload))
        return True

    def remove_favorite(self, slug):
        self.calls.append(("remove_favorite", {"slug": slug}))
        return True


class _DummyUpdateManager:
    def __init__(self):
        self.status_calls = []
        self.update_calls = 0
        self.raise_status = None
        self.raise_update = None

    def get_status(self, force=False):
        self.status_calls.append(force)
        if self.raise_status:
            raise self.raise_status
        return {"status": "ok", "force": force}

    def start_update(self):
        self.update_calls += 1
        if self.raise_update:
            raise self.raise_update
        return "Update started"


def _create_test_client(monkeypatch):
    manager = _DummyUpdateManager()
    monkeypatch.setattr("server.app.update_manager.manager", manager)
    monkeypatch.setattr("server.routers.system.update_manager.manager", manager)
    return TestClient(create_app(), base_url="http://localhost"), manager


def test_catalog_plugins_endpoint_forwards_query_params(monkeypatch):
    from server.routers import catalog

    repo = _DummyRepo()
    monkeypatch.setattr(catalog, "repo", repo)
    client, _ = _create_test_client(monkeypatch)

    response = client.get(
        "/api/catalog/plugins",
        params={"q": "seo", "sort_by": "score", "order": "asc", "limit": 25, "offset": 10},
    )

    assert response.status_code == 200
    assert response.json() == {"items": [{"slug": "akismet"}], "total": 1}
    assert repo.calls == [
        (
            "get_catalog_plugins",
            {"q": "seo", "sort_by": "score", "order": "asc", "limit": 25, "offset": 10},
        )
    ]



def test_catalog_plugin_sessions_endpoint_wraps_repo_response(monkeypatch):
    from server.routers import catalog

    repo = _DummyRepo()
    monkeypatch.setattr(catalog, "repo", repo)
    client, _ = _create_test_client(monkeypatch)

    response = client.get(
        "/api/catalog/plugins/akismet/sessions",
        params={"is_theme": "false", "limit": 5},
    )

    assert response.status_code == 200
    assert response.json() == {
        "slug": "akismet",
        "sessions": [{"session_id": 7, "score": 90}],
    }
    assert repo.calls == [
        (
            "get_catalog_plugin_sessions",
            {"slug": "akismet", "is_theme": False, "limit": 5},
        )
    ]



def test_favorites_endpoints_delegate_to_repository(monkeypatch):
    from server.routers import favorites

    repo = _DummyRepo()
    monkeypatch.setattr(favorites, "repo", repo)
    client, _ = _create_test_client(monkeypatch)

    list_response = client.get("/api/favorites")
    add_response = client.post(
        "/api/favorites",
        json={
            "slug": "akismet",
            "name": "Akismet",
            "version": "1.0.0",
            "score": 80,
            "installations": 1000,
            "days_since_update": 5,
            "tested_wp_version": "6.8",
            "is_theme": False,
            "download_link": "https://downloads.wordpress.org/plugin/akismet.zip",
            "wp_org_link": "https://wordpress.org/plugins/akismet/",
            "cve_search_link": "https://cve.mitre.org/cgi-bin/cvekey.cgi?keyword=akismet",
            "wpscan_link": "https://wpscan.com/plugin/akismet",
            "trac_link": "https://plugins.trac.wordpress.org/browser/akismet/",
            "author_trusted": False,
            "is_risky_category": False,
            "is_user_facing": True,
            "risk_tags": ["public-input"],
            "security_flags": ["custom-ajax"],
            "feature_flags": ["settings-page"],
            "code_analysis": {"summary": "ok"},
        },
    )
    delete_response = client.delete("/api/favorites/akismet")

    assert list_response.status_code == 200
    assert list_response.json() == {"favorites": [{"slug": "akismet"}]}
    assert add_response.status_code == 200
    assert add_response.json() == {"success": True}
    assert delete_response.status_code == 200
    assert delete_response.json() == {"success": True}

    assert repo.calls[0] == ("get_favorites", {})
    assert repo.calls[1][0] == "add_favorite"
    assert repo.calls[1][1]["slug"] == "akismet"
    assert repo.calls[1][1]["code_analysis"] == {"summary": "ok"}
    assert repo.calls[2] == ("remove_favorite", {"slug": "akismet"})



def test_system_update_status_endpoint_returns_manager_payload(monkeypatch):
    client, manager = _create_test_client(monkeypatch)

    response = client.get("/api/system/update", params={"force": "true"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "force": True}
    assert manager.status_calls[-1] is True



def test_system_update_status_endpoint_returns_503_on_failure(monkeypatch):
    client, manager = _create_test_client(monkeypatch)
    manager.raise_status = RuntimeError("boom")

    response = client.get("/api/system/update")

    assert response.status_code == 503
    assert response.json()["detail"] == "Unable to check for releases right now."



def test_system_trigger_update_maps_runtime_error_to_409(monkeypatch):
    client, manager = _create_test_client(monkeypatch)
    manager.raise_update = RuntimeError("already running")

    response = client.post("/api/system/update")

    assert response.status_code == 409
    assert response.json()["detail"] == "already running"



def test_system_trigger_update_returns_started_payload(monkeypatch):
    client, manager = _create_test_client(monkeypatch)

    response = client.post("/api/system/update")

    assert response.status_code == 200
    assert response.json() == {"status": "started", "message": "Update started"}
    assert manager.update_calls == 1
