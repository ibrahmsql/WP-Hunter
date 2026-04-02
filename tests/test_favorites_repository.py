from database.repository import ScanRepository


def test_add_favorite_persists_record(tmp_path):
    db_path = tmp_path / "favorites.db"
    repo = ScanRepository(db_path)

    payload = {
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
    }

    assert repo.add_favorite(payload) is True

    favorites = repo.get_favorites()
    assert len(favorites) == 1
    assert favorites[0]["slug"] == "akismet"
    assert favorites[0]["feature_flags"] == ["settings-page"]
    assert favorites[0]["code_analysis"]["summary"] == "ok"
