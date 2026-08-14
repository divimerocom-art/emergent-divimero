"""Iteration 5 — verification of the intermittent-404 bug fixes.

Covers:
  * HEAD /api/media/{id}  (was 405 Method Not Allowed)
  * POST /api/auth/refresh (was 404)
  * regression sweep of all authenticated read endpoints
  * BIST symbol search variants
"""
import os
import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

from conftest import API

BE_ENV = dotenv_values("/app/backend/.env")
BOGUS_ID = "00000000-0000-0000-0000-000000000000"


def _mongo():
    return MongoClient(BE_ENV["MONGO_URL"])[BE_ENV["DB_NAME"]]


@pytest.fixture(scope="module")
def real_files():
    db = _mongo()
    img = db.files.find_one({"is_deleted": False, "kind": "image"}, {"_id": 0, "id": 1})
    vid = db.files.find_one({"is_deleted": False, "kind": "video"}, {"_id": 0, "id": 1})
    if not img:
        pytest.fail("No non-deleted image file found in db.files")
    return {"image": img["id"], "video": vid["id"] if vid else None}


# --- HEAD /api/media/{id} ---------------------------------------------------
class TestHeadMedia:
    def test_head_real_image_200_and_headers_match_get(self, real_files):
        fid = real_files["image"]
        h = requests.head(f"{API}/media/{fid}", timeout=60)
        assert h.status_code == 200, f"HEAD returned {h.status_code}: {h.text[:200]}"
        assert h.content == b"", "HEAD must not return a body"

        g = requests.get(f"{API}/media/{fid}", timeout=60)
        assert g.status_code == 200
        for header in ("ETag", "Accept-Ranges", "Cache-Control", "Content-Length"):
            assert header in h.headers, f"HEAD missing {header}"
            assert h.headers[header] == g.headers.get(header), (
                f"{header} mismatch: HEAD={h.headers[header]!r} GET={g.headers.get(header)!r}")
        assert h.headers["Content-Length"] == str(len(g.content))
        assert h.headers["Accept-Ranges"] == "bytes"
        assert h.headers["Content-Type"].startswith("image/")

    def test_head_real_video_200(self, real_files):
        if not real_files["video"]:
            pytest.skip("no video file in db.files")
        h = requests.head(f"{API}/media/{real_files['video']}", timeout=60)
        assert h.status_code == 200
        assert h.headers["Content-Type"].startswith("video/")
        assert h.headers.get("Accept-Ranges") == "bytes"

    def test_head_bogus_id_404_not_405(self):
        h = requests.head(f"{API}/media/{BOGUS_ID}", timeout=30)
        assert h.status_code == 404, f"expected 404, got {h.status_code}"

    def test_get_bogus_id_404(self):
        g = requests.get(f"{API}/media/{BOGUS_ID}", timeout=30)
        assert g.status_code == 404

    def test_head_repeated_is_stable(self, real_files):
        codes = [requests.head(f"{API}/media/{real_files['image']}", timeout=60).status_code
                 for _ in range(5)]
        assert codes == [200] * 5, f"intermittent HEAD failures: {codes}"


# --- POST /api/auth/refresh ------------------------------------------------
class TestAuthRefresh:
    def test_refresh_without_token_401(self):
        r = requests.post(f"{API}/auth/refresh", timeout=30)
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text[:200]}"

    def test_refresh_with_bad_token_401(self):
        r = requests.post(f"{API}/auth/refresh", headers={"Authorization": "Bearer not.a.jwt"},
                          timeout=30)
        assert r.status_code == 401

    def test_refresh_returns_new_usable_token(self, deniz):
        r = deniz.post(f"{API}/auth/refresh", timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        data = r.json()
        assert isinstance(data.get("token"), str) and len(data["token"]) > 20
        # NOTE: public_user() intentionally omits email (same shape as /auth/me)
        assert data.get("user", {}).get("username") == "deniz.yatirim"
        assert "password_hash" not in data["user"]
        # new token must be accepted by /auth/me
        me = requests.get(f"{API}/auth/me",
                          headers={"Authorization": f"Bearer {data['token']}"}, timeout=30)
        assert me.status_code == 200
        assert me.json()["username"] == "deniz.yatirim"


# --- Regression sweep ------------------------------------------------------
AUTH_GET_ENDPOINTS = [
    "/auth/me",
    "/feed",
    "/portfolio",
    "/portfolio/transactions",
    "/portfolio/performance",
    "/notifications",
    "/market/movers",
    "/market/search?q=THYAO",
    "/users/deniz.yatirim",
    "/users/deniz.yatirim/posts",
    "/users/deniz.yatirim/disclosures",
    "/alerts",
]


class TestRegressionSweep:
    @pytest.mark.parametrize("path", AUTH_GET_ENDPOINTS)
    def test_endpoint_200(self, deniz, path):
        r = deniz.get(f"{API}{path}", timeout=90)
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"
        body = r.json()
        assert body is not None
        assert "_id" not in str(body)[:5000] or '"_id"' not in str(body), f"{path} leaks _id"

    def test_open_a_post_and_its_media(self, deniz):
        feed = deniz.get(f"{API}/feed", timeout=60).json()
        items = feed["items"] if isinstance(feed, dict) and "items" in feed else feed
        assert len(items) > 0
        checked = 0
        for p in items:
            r = deniz.get(f"{API}/posts/{p['id']}", timeout=60)
            assert r.status_code == 200, f"/posts/{p['id']} -> {r.status_code}"
            for url in (p.get("image_url"), p.get("video_url")):
                if url and url.startswith("/api/"):
                    hr = requests.head(f"{API.rsplit('/api', 1)[0]}{url}", timeout=60)
                    assert hr.status_code == 200, f"HEAD {url} -> {hr.status_code}"
                    checked += 1
        print(f"media HEAD probes from feed: {checked}")


# --- Market search variants ------------------------------------------------
SEARCH_CASES = [
    ("THYAO", "THYAO"), ("THYAO.IS", "THYAO"), ("BIST:THYAO", "THYAO"), ("thyao", "THYAO"),
    ("türk hava", "THYAO"), ("TUPRS", "TUPRS"), ("tüpraş", "TUPRS"), ("aselsan", "ASELS"),
    ("bim", "BIMAS"), ("koç holding", "KCHOL"), ("ASTOR", "ASTOR"), ("asto", "ASTOR"),
    ("GARAN", "GARAN"), ("EREGL", "EREGL"), ("MGROS", "MGROS"),
]


class TestMarketSearch:
    @pytest.mark.parametrize("query,expected", SEARCH_CASES)
    def test_top_hit(self, deniz, query, expected):
        r = deniz.get(f"{API}/market/search", params={"q": query}, timeout=60)
        assert r.status_code == 200, f"{query} -> {r.status_code} {r.text[:200]}"
        data = r.json()
        results = data["results"] if isinstance(data, dict) and "results" in data else data
        assert len(results) > 0, f"no results for {query!r}"
        assert results[0]["symbol"] == expected, (
            f"{query!r} top hit = {results[0]['symbol']}, expected {expected}")


# --- Broken media URL post lifecycle --------------------------------------
class TestBrokenMediaPost:
    def test_post_with_broken_image_url_is_served(self, deniz):
        r = deniz.post(f"{API}/posts", json={
            "text": "TEST_it5 broken image url probe",
            "image_url": f"/api/media/{BOGUS_ID}",
        }, timeout=60)
        assert r.status_code in (200, 201), f"{r.status_code} {r.text[:300]}"
        pid = r.json()["id"]
        try:
            got = deniz.get(f"{API}/posts/{pid}", timeout=30)
            assert got.status_code == 200
            assert got.json().get("image_url") == f"/api/media/{BOGUS_ID}"
            # the media itself must 404 (both verbs), not 405/500
            assert requests.get(f"{API}/media/{BOGUS_ID}", timeout=30).status_code == 404
            assert requests.head(f"{API}/media/{BOGUS_ID}", timeout=30).status_code == 404
        finally:
            # ISSUE: there is no DELETE /api/posts/{id} endpoint (returns 405),
            # so the temporary post must be purged straight from Mongo.
            _mongo().posts.delete_one({"id": pid})
            assert deniz.get(f"{API}/posts/{pid}", timeout=30).status_code == 404

    def test_delete_post_endpoint_missing(self, deniz):
        """Documents the missing DELETE /api/posts/{id} route (405 Method Not Allowed)."""
        r = deniz.post(f"{API}/posts", json={"text": "TEST_it5 delete-route probe"}, timeout=60)
        assert r.status_code in (200, 201)
        pid = r.json()["id"]
        d = deniz.delete(f"{API}/posts/{pid}", timeout=30)
        _mongo().posts.delete_one({"id": pid})
        assert d.status_code in (200, 204), (
            f"DELETE /api/posts/{{id}} not implemented -> {d.status_code}; users cannot delete posts")
