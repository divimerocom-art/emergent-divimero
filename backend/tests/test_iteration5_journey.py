"""Iteration 5 — realistic user journey probe: every /api/* call must avoid 404/405/500."""
import pytest
import requests
from conftest import API


class TestUserJourney:
    def test_full_journey_no_unexpected_errors(self, deniz):
        calls = []

        def rec(method, path, **kw):
            r = getattr(deniz, method)(f"{API}{path}", timeout=90, **kw)
            calls.append((method.upper(), path, r.status_code))
            return r

        me = rec("get", "/auth/me")
        assert me.status_code == 200

        feed = rec("get", "/feed")
        assert feed.status_code == 200
        items = feed.json().get("items", feed.json()) if isinstance(feed.json(), dict) else feed.json()
        pid = items[0]["id"]

        assert rec("get", f"/posts/{pid}").status_code == 200
        assert rec("get", f"/posts/{pid}/comments").status_code == 200
        like = rec("post", f"/posts/{pid}/like")
        assert like.status_code == 200
        rec("post", f"/posts/{pid}/like")  # unlike back

        assert rec("get", "/users/deniz.yatirim").status_code == 200
        assert rec("get", "/users/deniz.yatirim/posts").status_code == 200
        assert rec("get", "/users/deniz.yatirim/disclosures").status_code == 200

        assert rec("get", "/portfolio").status_code == 200
        assert rec("get", "/portfolio/transactions").status_code == 200
        assert rec("get", "/portfolio/performance").status_code == 200

        # add + remove a transaction
        tx = rec("post", "/portfolio/transactions", json={
            "ticker": "THYAO", "type": "buy", "quantity": 1, "price": 100.0,
            "date": "2026-01-02", "fees": 0,
        })
        assert tx.status_code in (200, 201), tx.text[:300]
        tx_id = tx.json().get("id")
        assert tx_id
        d = rec("delete", f"/portfolio/transactions/{tx_id}")
        assert d.status_code in (200, 204)

        assert rec("get", "/notifications").status_code == 200
        assert rec("get", "/alerts").status_code == 200
        assert rec("get", "/market/movers").status_code == 200
        assert rec("get", "/market/search?q=THYAO").status_code == 200

        bad = [c for c in calls if c[2] >= 400]
        assert not bad, f"journey produced error responses: {bad}"
        print("journey calls:", calls)

    def test_frontend_probe_paths_do_not_404(self):
        """The SPA shell must be served for deep links (no hard 404 from ingress)."""
        base = API.rsplit("/api", 1)[0]
        for path in ["/feed", "/portfolio", "/alerts", "/notifications", "/u/deniz.yatirim", "/login"]:
            r = requests.get(f"{base}{path}", timeout=60)
            assert r.status_code == 200, f"{path} -> {r.status_code}"
