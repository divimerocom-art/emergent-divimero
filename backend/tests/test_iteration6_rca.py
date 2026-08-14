"""RCA probes originally added in iteration 6 for (a) feed allocation 3x inflation and
(b) event-loop blocking. Iteration 7: both defects were fixed, so the probes are now
written as POSITIVE regression assertions instead of documenting markers.
"""
import asyncio
import os
import time

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env["REACT_APP_BACKEND_URL"]).rstrip("/")


# RCA (a) FIXED: /api/feed must compute allocation from the FULL ledger (incl. cash txs)
def test_rca_feed_uses_full_ledger_including_cash():
    import sys
    sys.path.insert(0, "/app/backend")
    from motor.motor_asyncio import AsyncIOMotorClient
    from portfolio_calc import allocation_for_symbol

    env = dotenv_values("/app/backend/.env")

    async def probe():
        c = AsyncIOMotorClient(env["MONGO_URL"])
        db = c[env["DB_NAME"]]
        u = await db.users.find_one({"username": "deniz.yatirim"})
        all_txs = await db.transactions.find({"user_id": u["id"]}, {"_id": 0}).sort("date", 1).to_list(5000)
        ticker_only = await db.transactions.find(
            {"user_id": u["id"], "ticker": {"$ne": None}}, {"_id": 0}).sort("date", 1).to_list(5000)
        c.close()
        return all_txs, ticker_only

    all_txs, ticker_only = asyncio.run(probe())
    dropped = len(all_txs) - len(ticker_only)
    print(f"[RCA-a] total txs={len(all_txs)} ticker-only txs={len(ticker_only)} cash rows={dropped}")
    if dropped == 0:
        pytest.skip("no cash-only tx in dataset; probe inconclusive")

    # Build the quote map from the author's ACTUAL holdings, otherwise missing symbols
    # are valued at 0 and the reference allocation itself becomes wrong.
    syms = sorted({(t.get("ticker") or "").upper() for t in all_txs if t.get("ticker")})
    qmap = {}
    for s in syms:
        r = requests.get(f"{BASE_URL}/api/market/quote/{s}", timeout=60)
        if r.status_code == 200 and r.json().get("price"):
            qmap[s] = r.json()["price"]
    assert len(qmap) == len(syms), f"missing quotes for {set(syms) - set(qmap)}"
    correct, _ = allocation_for_symbol(all_txs, qmap, "ASTOR")
    inflated, _ = allocation_for_symbol(ticker_only, qmap, "ASTOR")
    print(f"[RCA-a] ASTOR full-ledger={correct:.4f}% ticker-only(buggy)={inflated:.4f}%")

    feed = requests.get(f"{BASE_URL}/api/feed", timeout=60).json()
    astor = [p for p in feed if (p.get("disclosure") or {}).get("ticker") == "ASTOR"
             and p.get("current_position")]
    assert astor, "no ASTOR disclosure post in feed"
    api_alloc = float(astor[0]["current_position"]["allocation_pct"])
    print(f"[RCA-a] /api/feed ASTOR allocation_pct={api_alloc}")
    assert abs(api_alloc - correct) < 0.05, (
        f"/api/feed allocation {api_alloc} does not match full-ledger {correct:.4f}")
    assert abs(api_alloc - inflated) > 0.5, "feed still looks like the cash-less computation"


# RCA (b) FIXED: cold /market/tickers must not stall the event loop
def test_rca_cold_market_call_does_not_block_event_loop():
    import threading
    results = {}

    def cold_heavy():
        t0 = time.perf_counter()
        r = requests.get(f"{BASE_URL}/api/market/tickers?with_price=true&limit=120&q=K", timeout=120)
        results["heavy"] = (r.status_code, time.perf_counter() - t0)

    th = threading.Thread(target=cold_heavy)
    th.start()
    time.sleep(0.4)
    t0 = time.perf_counter()
    r2 = requests.get(f"{BASE_URL}/api/feed", timeout=120)
    light = time.perf_counter() - t0
    th.join()
    print(f"[RCA-b] heavy cold market call: {results.get('heavy')}")
    print(f"[RCA-b] concurrent /api/feed latency: {light:.3f}s")
    assert r2.status_code == 200
    assert light < 0.5, (
        f"DEFECT: /api/feed took {light:.3f}s while a cold /market/tickers?with_price "
        f"was running -> get_quotes still blocks the event loop")
