"""Iteration 4 — verification of the disclosure privacy fix + regressions."""
import os
import re
import uuid
import json
import requests
import pytest
from dotenv import dotenv_values

API = (os.environ.get("REACT_APP_BACKEND_URL")
       or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/") + "/api"

LEAK_KEYS = ("underlying_allocation_pct", "underlying_quantity", "allocation_at_publication")


@pytest.fixture(scope="module")
def deniz():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "deniz@divimero.com", "password": "demo1234"}, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


# --- root endpoint ---------------------------------------------------------
class TestRoot:
    def test_market_data_source_is_real_provider(self):
        r = requests.get(f"{API}/", timeout=60)
        assert r.status_code == 200
        assert r.json().get("market_data_source") == "yahoo", r.json()


# --- privacy on feed / posts ----------------------------------------------
class TestFeedPrivacy:
    def test_feed_has_no_leak_and_valid_change_status(self):
        r = requests.get(f"{API}/feed?limit=50", timeout=90)
        assert r.status_code == 200
        posts = r.json()
        assert posts, "feed empty"
        raw = json.dumps(posts)
        for k in LEAK_KEYS:
            assert k not in raw, f"LEAK: {k} present in /feed payload"
        seen_disclosure = False
        for p in posts:
            d = p.get("disclosure")
            if not d:
                continue
            seen_disclosure = True
            assert set(d.keys()) <= {
                "ticker", "disclosed_allocation_pct", "disclosed_range", "show_allocation",
                "allocation_mode", "show_quantity", "show_value", "source", "snapshot_at",
                "change_status", "change_magnitude_pct"}, d.keys()
            assert d.get("change_status") in {"increased", "reduced", "closed", "unchanged", None}
            cp = p.get("current_position")
            assert cp is None or set(cp.keys()) == {"allocation_pct"}, cp
        assert seen_disclosure, "no disclosure posts in feed to verify"

    def test_post_detail_has_no_leak(self):
        posts = requests.get(f"{API}/feed?limit=50", timeout=90).json()
        target = next((p for p in posts if p.get("disclosure")), None)
        assert target, "no disclosure post"
        r = requests.get(f"{API}/posts/{target['id']}", timeout=60)
        assert r.status_code == 200
        raw = json.dumps(r.json())
        for k in LEAK_KEYS:
            assert k not in raw, f"LEAK: {k} in /posts/{{id}}"
        assert r.json()["disclosure"]["change_status"] in {"increased", "reduced", "closed", "unchanged", None}


# --- golden demo disclosures ---------------------------------------------
class TestGoldenDisclosures:
    def test_deniz_disclosures_use_last_disclosed(self):
        r = requests.get(f"{API}/users/deniz.yatirim/disclosures", timeout=90)
        assert r.status_code == 200
        rows = {row["ticker"]: row for row in r.json()}
        raw = json.dumps(r.json())
        for k in LEAK_KEYS:
            assert k not in raw, f"LEAK: {k} in /disclosures"
        assert "THYAO" in rows and "ASTOR" in rows, rows.keys()
        assert rows["THYAO"]["last_disclosed"] == pytest.approx(2.6, abs=0.01)
        # The badge compares share counts against the LAST disclosure (26.08.2025),
        # by which date the 25.08 sale had already happened: 18 shares then, 18 now.
        # This asserted "reduced" while the status was derived from allocation %,
        # which drifts with the share price even when the creator makes no trade.
        assert rows["THYAO"]["change_status"] == "unchanged", rows["THYAO"]
        assert rows["ASTOR"]["last_disclosed"] == pytest.approx(4.2, abs=0.01), rows["ASTOR"]
        for row in rows.values():
            assert set(row["current"].keys()) == {"allocation_pct"}, row["current"]
            for h in row["history"]:
                assert "quantity" not in h and "allocation_at_publication" not in h, h


# --- hidden-mode post on a throwaway account ------------------------------
class TestHiddenPost:
    def test_hidden_post_yields_no_numbers(self):
        uid = uuid.uuid4().hex[:8]
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "email": f"TEST_it4_{uid}@example.com", "password": "demo1234",
            "display_name": "TEST It4", "username": f"test_it4_{uid}"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
        username = r.json()["user"]["username"]
        try:
            s.post(f"{API}/portfolio/transactions", json={"type": "deposit", "date": "2025-01-01", "amount": 10000}, timeout=60)
            s.post(f"{API}/portfolio/transactions", json={"type": "buy", "ticker": "ASTOR", "date": "2025-01-02",
                                                         "quantity": 10, "price": 100}, timeout=60)
            pr = s.post(f"{API}/posts", json={
                "text": "TEST it4 hidden", "tickers": ["ASTOR"], "attach_position": True,
                "disclosure_ticker": "ASTOR", "show_allocation": False, "allocation_mode": "hidden",
                "show_quantity": False, "show_value": False}, timeout=90)
            assert pr.status_code == 200, pr.text[:300]
            pd = pr.json()
            assert pd["disclosure"]["disclosed_allocation_pct"] is None
            assert pd.get("current_position") is None, pd.get("current_position")
            raw_post = json.dumps(pd)
            for k in LEAK_KEYS:
                assert k not in raw_post, f"LEAK on POST /posts response: {k}"

            rows = requests.get(f"{API}/users/{username}/disclosures", timeout=60).json()
            assert rows
            row = rows[0]
            assert row["last_disclosed"] is None, row
            assert row["history"] == [], row["history"]
            assert row["change_status"] is None, row
            raw = json.dumps(row)
            for k in LEAK_KEYS:
                assert k not in raw, f"LEAK: {k}"
        finally:
            import asyncio
            from motor.motor_asyncio import AsyncIOMotorClient
            env = dotenv_values("/app/backend/.env")

            async def go():
                c = AsyncIOMotorClient(env["MONGO_URL"])
                db = c[env["DB_NAME"]]
                u = await db.users.find_one({"username": username})
                if u:
                    await db.posts.delete_many({"author_id": u["id"]})
                    await db.transactions.delete_many({"user_id": u["id"]})
                    await db.notifications.delete_many({"user_id": u["id"]})
                    await db.users.delete_one({"id": u["id"]})
                c.close()
            asyncio.run(go())


# --- regressions ----------------------------------------------------------
class TestRegressions:
    def test_notifications_route_registered_once(self, deniz):
        r = deniz.get(f"{API}/notifications", timeout=60)
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, dict) and "items" in body and "unread" in body, body
        # ensure the route is registered exactly once (duplicate decorator regression)
        import importlib
        srv = importlib.import_module("server")
        matches = [r for r in srv.app.routes
                   if getattr(r, "path", None) == "/api/notifications" and "GET" in getattr(r, "methods", set())]
        assert len(matches) == 1, f"/api/notifications registered {len(matches)} times"

    def test_instrument_search_astor(self):
        r = requests.get(f"{API}/market/tickers?q=astor", timeout=60)
        assert r.status_code == 200
        syms = [t["symbol"] for t in r.json()]
        assert "ASTOR" in syms, syms[:10]

    def test_ticker_movers(self):
        r = requests.get(f"{API}/market/movers", timeout=90)
        assert r.status_code == 200, r.text[:200]
        assert isinstance(r.json(), (list, dict))

    def test_portfolio_xirr(self, deniz):
        r = deniz.get(f"{API}/portfolio", timeout=90)
        assert r.status_code == 200
        data = r.json()
        assert "xirr" in json.dumps(data).lower()

    def test_dividend_flow_invariance(self, deniz):
        before = deniz.get(f"{API}/portfolio", timeout=90).json()
        b_div = before["total_dividends"]
        b_cash = before["cash"]
        b_qty = next(h["quantity"] for h in before["holdings"] if h["ticker"] == "ASTOR")
        cr = deniz.post(f"{API}/portfolio/transactions", json={
            "type": "dividend", "ticker": "ASTOR", "date": "2026-02-01", "amount": 500}, timeout=60)
        assert cr.status_code == 200, cr.text[:300]
        tx_id = cr.json().get("id") or cr.json().get("transaction", {}).get("id")
        try:
            after = deniz.get(f"{API}/portfolio", timeout=90).json()
            assert after["total_dividends"] == pytest.approx(b_div + 500, abs=0.01)
            assert after["cash"] == pytest.approx(b_cash + 500, abs=0.01)
            a_qty = next(h["quantity"] for h in after["holdings"] if h["ticker"] == "ASTOR")
            assert a_qty == b_qty
        finally:
            assert deniz.delete(f"{API}/portfolio/transactions/{tx_id}", timeout=60).status_code in (200, 204)
        restored = deniz.get(f"{API}/portfolio", timeout=90).json()
        assert restored["total_dividends"] == pytest.approx(b_div, abs=0.01)

    def test_alerts_crud(self, deniz):
        cr = deniz.post(f"{API}/alerts", json={
            "followee_username": "ece.market", "ticker": "ASTOR",
            "direction": "any", "threshold_pct": 5}, timeout=60)
        assert cr.status_code == 200, cr.text[:300]
        aid = cr.json()["id"]
        got = deniz.get(f"{API}/alerts", timeout=60)
        assert got.status_code == 200 and any(a["id"] == aid for a in got.json())
        up = deniz.patch(f"{API}/alerts/{aid}", json={"active": False}, timeout=60)
        assert up.status_code == 200 and up.json()["active"] is False
        assert deniz.delete(f"{API}/alerts/{aid}", timeout=60).status_code in (200, 204)
        assert not any(a["id"] == aid for a in deniz.get(f"{API}/alerts", timeout=60).json())

    def test_media_range_streaming(self):
        posts = requests.get(f"{API}/feed?limit=50", timeout=90).json()
        url = next((p.get("video_url") or p.get("image_url") for p in posts
                    if p.get("video_url") or p.get("image_url")), None)
        if not url or not url.startswith("/api"):
            pytest.skip("no local media in feed")
        base = API.rsplit("/api", 1)[0]
        r = requests.get(base + url, headers={"Range": "bytes=0-99"}, timeout=60)
        assert r.status_code == 206, r.status_code
        assert "content-range" in {k.lower() for k in r.headers}
