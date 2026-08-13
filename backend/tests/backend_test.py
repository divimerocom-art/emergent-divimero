"""Divimero backend regression + new-feature tests (iteration 2).

Covers: health, auth/register+onboarding PATCH, uploads (image/video/invalid),
media serving, notifications fan-out + read, XIRR in /api/portfolio, golden demo feed.
"""
import io
import os
import time
import uuid
import zlib
import struct
import requests
import pytest

from conftest import API, _login

TIMEOUT = 60


# ---------- helpers: build tiny valid media in-memory ----------
def tiny_png() -> bytes:
    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * 2 for _ in range(2))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def small_mp4(size_bytes: int = 300 * 1024) -> bytes:
    header = (b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
              b"\x00\x00\x00\x08free")
    pad = b"\x00" * max(0, size_bytes - len(header))
    return header + pad


# ---------- module: health ----------
class TestHealth:
    def test_root(self):
        r = requests.get(f"{API}/", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "ok"
        assert data["app"] == "Divimero"


# ---------- feature: onboarding (register -> PATCH /auth/me) ----------
class TestOnboarding:
    created = {}

    def test_register_new_user(self):
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "email": f"test_{suffix}@example.com",
            "password": "demo1234",
            "display_name": "TEST User",
            "username": f"test_{suffix}",
        }
        r = requests.post(f"{API}/auth/register", json=payload, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("token"), str) and len(d["token"]) > 10
        assert d["user"]["username"] == payload["username"]
        assert d["user"]["display_name"] == "TEST User"
        assert d["user"]["bio"] == ""
        TestOnboarding.created = {"payload": payload, "token": d["token"], "id": d["user"]["id"]}

    def test_register_duplicate_email_rejected(self):
        p = TestOnboarding.created["payload"]
        r = requests.post(f"{API}/auth/register", json={**p, "username": p["username"] + "x"}, timeout=TIMEOUT)
        assert r.status_code == 400
        assert "e-posta" in r.json()["detail"].lower()

    def test_patch_me_updates_profile_and_persists(self):
        tok = TestOnboarding.created["token"]
        h = {"Authorization": f"Bearer {tok}"}
        r = requests.patch(f"{API}/auth/me", json={"display_name": "TEST Onboarded", "bio": "BIST temettü"}, headers=h, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["display_name"] == "TEST Onboarded"
        assert d["bio"] == "BIST temettü"
        # GET verify persistence
        g = requests.get(f"{API}/auth/me", headers=h, timeout=TIMEOUT)
        assert g.status_code == 200
        assert g.json()["display_name"] == "TEST Onboarded"
        assert g.json()["bio"] == "BIST temettü"

    def test_new_user_xirr_is_null(self):
        tok = TestOnboarding.created["token"]
        r = requests.get(f"{API}/portfolio", headers={"Authorization": f"Bearer {tok}"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "xirr" in d
        assert d["xirr"] is None, f"expected null xirr for zero-cashflow user, got {d['xirr']}"

    def test_me_requires_auth(self):
        r = requests.get(f"{API}/auth/me", timeout=TIMEOUT)
        assert r.status_code == 401


# ---------- feature: uploads + media ----------
class TestUploads:
    image = {}
    video = {}

    def test_upload_requires_auth(self):
        r = requests.post(f"{API}/uploads", files={"file": ("a.png", tiny_png(), "image/png")}, timeout=TIMEOUT)
        assert r.status_code == 401

    def test_upload_image(self, deniz):
        blob = tiny_png()
        r = deniz.post(f"{API}/uploads", files={"file": ("TEST_tiny.png", blob, "image/png")}, timeout=TIMEOUT)
        assert r.status_code == 200, f"{r.status_code} {r.text[:500]}"
        d = r.json()
        assert d["kind"] == "image"
        assert d["content_type"] == "image/png"
        assert d["url"] == f"/api/media/{d['id']}"
        TestUploads.image = {"meta": d, "bytes": blob}

    def test_get_media_image_bytes_match(self):
        d = TestUploads.image["meta"]
        r = requests.get(f"{API}/media/{d['id']}", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        assert r.headers["content-type"].startswith("image/png")
        assert r.content == TestUploads.image["bytes"], "served bytes differ from uploaded bytes"

    def test_get_media_404(self):
        r = requests.get(f"{API}/media/{uuid.uuid4()}", timeout=TIMEOUT)
        assert r.status_code == 404

    def test_upload_video(self, deniz):
        blob = small_mp4()
        r = deniz.post(f"{API}/uploads", files={"file": ("TEST_clip.mp4", blob, "video/mp4")}, timeout=180)
        assert r.status_code == 200, f"{r.status_code} {r.text[:500]}"
        d = r.json()
        assert d["kind"] == "video"
        assert d["content_type"] == "video/mp4"
        TestUploads.video = {"meta": d, "bytes": blob}

    def test_get_media_video(self):
        d = TestUploads.video["meta"]
        r = requests.get(f"{API}/media/{d['id']}", timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("video/mp4")
        assert len(r.content) == len(TestUploads.video["bytes"])

    def test_upload_invalid_type_400(self, deniz):
        r = deniz.post(f"{API}/uploads", files={"file": ("TEST_doc.pdf", b"%PDF-1.4 junk", "application/pdf")}, timeout=TIMEOUT)
        assert r.status_code == 400, r.text[:300]
        assert "Desteklenmeyen" in r.json()["detail"]

    def test_post_with_video_url(self, deniz):
        url = TestUploads.video["meta"]["url"]
        r = deniz.post(f"{API}/posts", json={"text": "TEST video gönderisi", "tickers": ["THYAO"], "video_url": url}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["video_url"] == url
        assert d["author"]["username"] == "deniz.yatirim"
        # verify persisted in feed
        f = requests.get(f"{API}/posts/{d['id']}", timeout=TIMEOUT)
        assert f.status_code == 200
        assert f.json()["video_url"] == url


# ---------- feature: notifications fan-out ----------
class TestNotifications:
    post_id = None

    def test_requires_auth(self):
        r = requests.get(f"{API}/notifications", timeout=TIMEOUT)
        assert r.status_code == 401

    def test_ece_marks_read_baseline(self, ece):
        r = ece.post(f"{API}/notifications/read", timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.json()["ok"] is True
        g = ece.get(f"{API}/notifications", timeout=TIMEOUT)
        assert g.status_code == 200
        assert g.json()["unread"] == 0

    def test_deniz_post_fans_out_to_ece(self, deniz, ece):
        r = deniz.post(f"{API}/posts", json={"text": "TEST bildirim fan-out gönderisi", "tickers": ["ASELS"]}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        TestNotifications.post_id = r.json()["id"]
        time.sleep(1)
        g = ece.get(f"{API}/notifications", timeout=TIMEOUT)
        assert g.status_code == 200
        data = g.json()
        assert data["unread"] >= 1, f"expected unread>=1, got {data}"
        match = [n for n in data["items"] if n.get("post_id") == TestNotifications.post_id]
        assert match, "no notification for the new post"
        n = match[0]
        assert n["kind"] == "new_post"
        assert n["actor"]["username"] == "deniz.yatirim"
        assert n["read"] is False
        assert "TEST bildirim" in (n["post_preview"] or "")
        assert "_id" not in n

    def test_mark_read_sets_unread_zero(self, ece):
        r = ece.post(f"{API}/notifications/read", timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.json()["modified"] >= 1
        g = ece.get(f"{API}/notifications", timeout=TIMEOUT)
        assert g.json()["unread"] == 0
        n = [x for x in g.json()["items"] if x["post_id"] == TestNotifications.post_id][0]
        assert n["read"] is True

    def test_author_gets_no_self_notification(self, deniz):
        g = deniz.get(f"{API}/notifications", timeout=TIMEOUT)
        assert g.status_code == 200
        own = [n for n in g.json()["items"] if n.get("post_id") == TestNotifications.post_id and n.get("actor", {}).get("username") == "deniz.yatirim"]
        assert not own, "author should not notify himself"


# ---------- feature: XIRR ----------
class TestXirr:
    def test_deniz_portfolio_has_xirr(self, deniz):
        r = deniz.get(f"{API}/portfolio", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "xirr" in d, "xirr field missing"
        assert d["xirr"] is not None, "xirr should be numeric for seeded Deniz"
        assert isinstance(d["xirr"], (int, float))
        assert 0.0 < d["xirr"] < 1.0, f"xirr out of sane range: {d['xirr']}"
        assert d["total_value"] > 0

    def test_unit_xirr_module(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from xirr import xirr as _x, build_cashflows
        r = _x([("2023-01-01", -1000.0), ("2024-01-01", 1100.0)])
        assert r is not None and abs(r - 0.1) < 0.01
        assert _x([("2023-01-01", -1000.0)]) is None
        assert _x([("2023-01-01", -1000.0), ("2024-01-01", -100.0)]) is None
        cfs = build_cashflows([{"type": "deposit", "date": "2023-01-01", "amount": 1000}], "2024-01-01T00:00:00+00:00", 1100)
        assert cfs[0][1] == -1000
        assert cfs[-1][1] == 1100


# ---------- regression: golden demo ----------
class TestGoldenDemo:
    def test_feed_thyao_disclosure(self):
        r = requests.get(f"{API}/feed?limit=50", timeout=TIMEOUT)
        assert r.status_code == 200
        posts = r.json()
        thyao = [p for p in posts if (p.get("disclosure") or {}).get("ticker") == "THYAO"
                 and p.get("author", {}).get("username") == "deniz.yatirim"]
        assert thyao, "golden THYAO thesis post missing"
        thyao.sort(key=lambda x: x["created_at"])
        thesis = thyao[0]   # original thesis snapshot (seed: 6.18)
        assert thesis["disclosure"]["disclosed_allocation_pct"] == 6.18
        assert thesis["disclosure"]["show_allocation"] is True
        assert thesis["disclosure"]["allocation_mode"] == "exact"
        cur = thesis["current_position"]["allocation_pct"]
        assert cur > 0
        # published snapshot (6.18) must stay immutable and above the current weight -> "Azalttı"
        assert cur < thesis["disclosure"]["disclosed_allocation_pct"], "expected reduced (Azaltti) state"
        for p in thyao:
            assert "_id" not in p
