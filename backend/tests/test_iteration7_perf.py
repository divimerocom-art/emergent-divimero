"""Iteration 7: verify perf budgets + feed/post-detail parity after the
YahooBistProvider parallelisation + /api/feed cash-tx fix."""
import os
import time
import threading

import pytest
import requests
from dotenv import dotenv_values

_env = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _env.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE}/api"
CRED = {"email": "deniz@divimero.com", "password": "demo1234"}


def _timed(url, **kw):
    t0 = time.time()
    r = requests.get(url, timeout=60, **kw)
    return r, time.time() - t0


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json=CRED, timeout=30)
    assert r.status_code == 200, r.text[:300]
    tok = r.json().get("token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


# --- PERF: market search cold/warm ------------------------------------------
def test_market_search_cold_and_warm():
    url = f"{API}/market/search?q=K&with_price=true&limit=30"
    times = []
    for _ in range(3):
        r, dt = _timed(url)
        assert r.status_code == 200, r.text[:300]
        assert isinstance(r.json(), list) and len(r.json()) > 0
        times.append(dt)
    print(f"search q=K timings: {[round(t,3) for t in times]}")
    assert times[0] < 5.0, f"cold search {times[0]:.2f}s exceeds 5s"
    assert times[1] < 0.2, f"warm search {times[1]:.3f}s exceeds 200ms"
    assert times[2] < 0.2, f"warm search {times[2]:.3f}s exceeds 200ms"


# --- PERF: feed -------------------------------------------------------------
def test_feed_warm_under_300ms():
    requests.get(f"{API}/feed", timeout=60)
    times = []
    for _ in range(3):
        r, dt = _timed(f"{API}/feed")
        assert r.status_code == 200
        times.append(dt)
    print(f"feed timings: {[round(t,3) for t in times]}")
    assert max(times) < 0.3, f"feed warm times {times}"


# --- PERF: portfolio --------------------------------------------------------
def test_portfolio_warm_under_500ms(auth):
    requests.get(f"{API}/portfolio", headers=auth, timeout=60)
    times = []
    for _ in range(3):
        r, dt = _timed(f"{API}/portfolio", headers=auth)
        assert r.status_code == 200
        times.append(dt)
    print(f"portfolio timings: {[round(t,3) for t in times]}")
    assert max(times) < 0.5, f"portfolio warm times {times}"


# --- CORRECTNESS: feed vs post-detail parity --------------------------------
def test_feed_post_divergence_gone():
    feed = requests.get(f"{API}/feed", timeout=60)
    assert feed.status_code == 200
    posts = [p for p in feed.json() if p.get("disclosure")]
    assert posts, "no disclosure posts in feed"
    mismatches = []
    checked = 0
    for p in posts:
        d = requests.get(f"{API}/posts/{p['id']}", timeout=60)
        assert d.status_code == 200, d.text[:200]
        det = d.json()
        fa = (p.get("current_position") or {}).get("allocation_pct")
        da = (det.get("current_position") or {}).get("allocation_pct")
        fs = (p.get("disclosure") or {}).get("change_status")
        ds = (det.get("disclosure") or {}).get("change_status")
        checked += 1
        if fa is not None and da is not None:
            if abs(float(fa) - float(da)) > 0.01:
                mismatches.append(f"{p['id']} {p['disclosure'].get('ticker')} alloc feed={fa} detail={da}")
        elif fa != da:
            mismatches.append(f"{p['id']} alloc feed={fa} detail={da}")
        if fs != ds:
            mismatches.append(f"{p['id']} {p['disclosure'].get('ticker')} status feed={fs} detail={ds}")
    print(f"checked {checked} disclosure posts")
    assert not mismatches, "DIVERGENCE: " + "; ".join(mismatches)


def test_thyao_reduced_and_astor_status():
    feed = requests.get(f"{API}/feed", timeout=60).json()
    seen = {}
    for p in feed:
        d = p.get("disclosure")
        if not d:
            continue
        seen.setdefault(d.get("ticker"), []).append(
            (d.get("change_status"), (p.get("current_position") or {}).get("allocation_pct"))
        )
    print("disclosure statuses:", seen)
    assert "THYAO" in seen, "no THYAO disclosure post seeded"
    for status, alloc in seen["THYAO"]:
        assert status == "reduced", f"THYAO expected 'reduced', got {status} (alloc={alloc})"
    if "ASTOR" in seen:
        for status, alloc in seen["ASTOR"]:
            assert status in ("unchanged", "increased", "reduced"), status
            assert alloc is not None and alloc < 15, f"ASTOR alloc looks inflated: {alloc}"


# --- CONCURRENCY: event loop must not stall ---------------------------------
def test_feed_not_blocked_by_cold_market_call():
    holder = {}

    def cold():
        try:
            r, dt = _timed(f"{API}/market/tickers?q=K&limit=120&with_price=true&nocache={time.time()}")
            holder["cold"] = (r.status_code, dt)
        except Exception as e:  # pragma: no cover
            holder["cold"] = ("err", str(e))

    t = threading.Thread(target=cold)
    t.start()
    time.sleep(0.4)
    r, dt = _timed(f"{API}/feed")
    t.join(timeout=90)
    print(f"cold market call: {holder.get('cold')}; concurrent feed: {dt:.3f}s")
    assert r.status_code == 200
    assert dt < 0.5, f"feed stalled to {dt:.3f}s during cold market call (event loop blocked)"


# --- REGRESSION smoke -------------------------------------------------------
@pytest.mark.parametrize("path", [
    "/auth/me", "/notifications", "/alerts",
    "/users/deniz.yatirim", "/users/deniz.yatirim/posts", "/users/deniz.yatirim/disclosures",
])
def test_smoke_endpoints(auth, path):
    r, dt = _timed(f"{API}{path}", headers=auth)
    print(f"{path} -> {r.status_code} in {dt:.3f}s")
    assert r.status_code == 200, r.text[:200]
