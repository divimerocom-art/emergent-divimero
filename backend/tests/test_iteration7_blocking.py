"""Iteration 7 probes: remaining provider.get_quotes call sites that are NOT wrapped in
run_in_threadpool (server.py ~248, 316, 352, 377, 410, 465, 819). Measures whether they
still stall the event loop for other requests.
"""
import os
import threading
import time

import requests
from dotenv import dotenv_values

_env = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _env["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE}/api"
CRED = {"email": "deniz@divimero.com", "password": "demo1234"}


def _login():
    r = requests.post(f"{API}/auth/login", json=CRED, timeout=30)
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _concurrency(heavy_call, label):
    res = {}

    def run():
        t0 = time.perf_counter()
        try:
            r = heavy_call()
            res["heavy"] = (r.status_code, round(time.perf_counter() - t0, 3))
        except Exception as e:
            res["heavy"] = ("err", str(e)[:80])

    th = threading.Thread(target=run)
    th.start()
    time.sleep(0.3)
    t0 = time.perf_counter()
    light = requests.get(f"{API}/feed", timeout=120)
    dt = time.perf_counter() - t0
    th.join(timeout=180)
    print(f"[{label}] heavy={res.get('heavy')} concurrent_feed={dt:.3f}s")
    assert light.status_code == 200
    return dt


# Uncached single-symbol quote -> server.py:352 prov.get_quote (sync, not threadpooled)
def test_single_quote_does_not_block_event_loop():
    # pick a symbol unlikely to be prewarmed/cached
    rows = requests.get(f"{API}/market/tickers?limit=400", timeout=60).json()
    sym = None
    for r in rows[::-1]:
        if r["symbol"] not in ("THYAO", "ASTOR", "GARAN", "AKBNK"):
            sym = r["symbol"]
            break
    print(f"[quote] probing symbol {sym}")
    dt = _concurrency(lambda: requests.get(f"{API}/market/quote/{sym}", timeout=120), "market/quote")
    assert dt < 0.5, f"/api/feed stalled {dt:.3f}s during /api/market/quote/{sym}"


# server.py:316 get_quotes inside a per-transaction loop, no threadpool
def test_portfolio_performance_does_not_block_event_loop():
    auth = _login()
    dt = _concurrency(
        lambda: requests.get(f"{API}/portfolio/performance", headers=auth, timeout=120),
        "portfolio/performance")
    assert dt < 0.5, f"/api/feed stalled {dt:.3f}s during /api/portfolio/performance"


# server.py:377 movers -> get_quotes sync on event loop
def test_movers_does_not_block_event_loop():
    dt = _concurrency(lambda: requests.get(f"{API}/market/movers", timeout=120), "market/movers")
    assert dt < 0.5, f"/api/feed stalled {dt:.3f}s during /api/market/movers"
