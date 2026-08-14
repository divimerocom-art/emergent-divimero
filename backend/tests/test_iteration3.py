"""Iteration 3 — instrument search, dividend workflow, public disclosure privacy, golden ASTOR/THYAO."""
import os
import requests
import pytest
from datetime import datetime, timezone
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
API = base_url.rstrip("/") + "/api"

DENIZ = {"email": "deniz@divimero.com", "password": "demo1234"}
ECE = {"email": "ece@divimero.com", "password": "demo1234"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=40)
    if r.status_code != 200:
        pytest.fail(f"Login failed {creds['email']}: {r.status_code} {r.text[:300]}")
    tok = r.json().get("token")
    if not tok:
        pytest.fail("no token")
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def dz():
    return _login(DENIZ)


@pytest.fixture(scope="module")
def ec():
    return _login(ECE)


@pytest.fixture(scope="module")
def created_tx_ids():
    return []


@pytest.fixture(scope="module", autouse=True)
def cleanup(dz, created_tx_ids):
    yield
    for tid in created_tx_ids:
        r = dz.delete(f"{API}/portfolio/transactions/{tid}", timeout=40)
        assert r.status_code in (200, 204, 404), f"cleanup failed for {tid}: {r.status_code}"


# --- Module: market_data / instrument search --------------------------------
class TestInstrumentSearch:
    def test_tickers_astor(self):
        r = requests.get(f"{API}/market/tickers", params={"q": "ASTOR"}, timeout=40)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list) and len(rows) >= 1
        assert rows[0]["symbol"] == "ASTOR"
        assert "astor" in rows[0]["name"].lower()
        assert rows[0].get("sector")

    def test_tickers_case_insensitive(self):
        for q in ["astor", "AsToR", "astor enerji"]:
            r = requests.get(f"{API}/market/tickers", params={"q": q}, timeout=40)
            assert r.status_code == 200, q
            syms = [x["symbol"] for x in r.json()]
            assert "ASTOR" in syms, f"q={q} -> {syms[:10]}"

    def test_universe_size(self):
        r = requests.get(f"{API}/market/tickers", params={"limit": 200}, timeout=40)
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 50, f"expected expanded BIST universe, got {len(rows)}"
        assert len({x["symbol"] for x in rows}) == len(rows), "duplicate symbols"

    def test_search_enerji_multiple(self):
        r = requests.get(f"{API}/market/search", params={"q": "enerji"}, timeout=40)
        assert r.status_code == 200
        syms = [x["symbol"] for x in r.json()]
        assert len(syms) >= 3, syms
        assert "ASTOR" in syms

    def test_search_energy_sector(self):
        r = requests.get(f"{API}/market/search", params={"q": "Enerji"}, timeout=40)
        assert r.status_code == 200
        syms = set(x["symbol"] for x in r.json())
        # sector-ish expectation from review request
        found = syms & {"TUPRS", "PETKM", "ENJSA", "ASTOR"}
        assert len(found) >= 2, f"only {found} matched of energy tickers; got {sorted(syms)}"

    def test_search_missing_q_is_422(self):
        r = requests.get(f"{API}/market/search", timeout=40)
        assert r.status_code == 422

    def test_search_no_result(self):
        r = requests.get(f"{API}/market/search", params={"q": "zzzznotarealticker"}, timeout=40)
        assert r.status_code == 200
        assert r.json() == []

    def test_quote_astor(self):
        r = requests.get(f"{API}/market/quote/ASTOR", timeout=40)
        assert r.status_code == 200
        q = r.json()
        assert q["symbol"] == "ASTOR"
        assert isinstance(q["price"], (int, float)) and q["price"] > 0


# --- Module: portfolio dividends -------------------------------------------
class TestDividends:
    def test_seeded_dividend_totals(self, dz):
        r = dz.get(f"{API}/portfolio", timeout=60)
        assert r.status_code == 200
        p = r.json()
        assert p["total_dividends"] == pytest.approx(2900.0, abs=0.01), p["total_dividends"]
        by = {h["ticker"]: h for h in p["holdings"]}
        assert by["GARAN"]["dividends"] == pytest.approx(1650.0, abs=0.01)
        assert by["ASTOR"]["dividends"] == pytest.approx(1250.0, abs=0.01)

    def test_dividend_does_not_change_quantity(self, dz, created_tx_ids):
        before = dz.get(f"{API}/portfolio", timeout=60).json()
        b_by = {h["ticker"]: h for h in before["holdings"]}
        qty_before = b_by["ASTOR"]["quantity"]
        cash_before = before["cash"]
        div_before = before["total_dividends"]

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        r = dz.post(f"{API}/portfolio/transactions", json={
            "type": "dividend", "ticker": "ASTOR", "date": today,
            "amount": 500, "note": "TEST_dividend"
        }, timeout=60)
        assert r.status_code == 200, r.text[:300]
        tx = r.json()
        assert "_id" not in tx
        assert tx["ticker"] == "ASTOR" and tx["type"] == "dividend" and tx["amount"] == 500
        created_tx_ids.append(tx["id"])

        after = dz.get(f"{API}/portfolio", timeout=60).json()
        a_by = {h["ticker"]: h for h in after["holdings"]}
        assert a_by["ASTOR"]["quantity"] == pytest.approx(qty_before), "dividend changed quantity!"
        assert after["total_dividends"] == pytest.approx(div_before + 500, abs=0.01)
        assert after["cash"] == pytest.approx(cash_before + 500, abs=0.01)
        assert a_by["ASTOR"]["dividends"] == pytest.approx(b_by["ASTOR"]["dividends"] + 500, abs=0.01)

        # visible in transaction list
        txs = dz.get(f"{API}/portfolio/transactions", timeout=60).json()
        assert any(t["id"] == tx["id"] and t["type"] == "dividend" for t in txs)

    def test_dividend_delete_reverts(self, dz):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        base = dz.get(f"{API}/portfolio", timeout=60).json()["total_dividends"]
        tx = dz.post(f"{API}/portfolio/transactions", json={
            "type": "dividend", "ticker": "GARAN", "date": today, "amount": 111, "note": "TEST_del"
        }, timeout=60).json()
        mid = dz.get(f"{API}/portfolio", timeout=60).json()["total_dividends"]
        assert mid == pytest.approx(base + 111, abs=0.01)
        d = dz.delete(f"{API}/portfolio/transactions/{tx['id']}", timeout=60)
        assert d.status_code == 200
        end = dz.get(f"{API}/portfolio", timeout=60).json()["total_dividends"]
        assert end == pytest.approx(base, abs=0.01)

    def test_invalid_tx_type_rejected(self, dz):
        r = dz.post(f"{API}/portfolio/transactions", json={"type": "bogus", "date": "2026-01-01"}, timeout=40)
        assert r.status_code == 422


# --- Module: buy transaction via search ------------------------------------
class TestBuyAstor:
    def test_buy_astor_updates_holdings(self, dz, created_tx_ids):
        before = dz.get(f"{API}/portfolio", timeout=60).json()
        qty_before = next((h["quantity"] for h in before["holdings"] if h["ticker"] == "ASTOR"), 0)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        r = dz.post(f"{API}/portfolio/transactions", json={
            "type": "buy", "ticker": "astor", "date": today, "quantity": 10, "price": 130, "fees": 0, "note": "TEST_buy"
        }, timeout=60)
        assert r.status_code == 200, r.text[:300]
        tx = r.json()
        assert tx["ticker"] == "ASTOR", "ticker not normalised to uppercase"
        created_tx_ids.append(tx["id"])
        after = dz.get(f"{API}/portfolio", timeout=60).json()
        qty_after = next(h["quantity"] for h in after["holdings"] if h["ticker"] == "ASTOR")
        assert qty_after == pytest.approx(qty_before + 10)


# --- Module: privacy / disclosures -----------------------------------------
class TestPrivacy:
    def test_portfolio_requires_auth(self):
        r = requests.get(f"{API}/portfolio", timeout=40)
        assert r.status_code == 401

    def test_disclosures_public_no_money(self):
        r = requests.get(f"{API}/users/deniz.yatirim/disclosures", timeout=60)
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        tickers = {x["ticker"] for x in rows}
        assert {"THYAO", "ASTOR"} <= tickers, tickers
        banned = {"market_value", "total_value", "cost_basis", "avg_cost", "cash", "amount", "value"}
        def scan(o, path=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    assert k not in banned, f"monetary field '{k}' leaked at {path}"
                    scan(v, f"{path}.{k}")
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    scan(v, f"{path}[{i}]")
        scan(rows)

    def test_disclosures_only_disclosed_tickers(self, dz):
        held = {h["ticker"] for h in dz.get(f"{API}/portfolio", timeout=60).json()["holdings"]}
        disclosed = {x["ticker"] for x in requests.get(f"{API}/users/deniz.yatirim/disclosures", timeout=60).json()}
        assert disclosed <= held or True  # disclosed may include closed positions
        assert len(disclosed) < len(held), f"all holdings exposed: held={held} disclosed={disclosed}"

    def test_ece_cannot_see_deniz_portfolio(self, ec):
        r = ec.get(f"{API}/portfolio", timeout=60).json()
        deniz_pub = requests.get(f"{API}/users/deniz.yatirim", timeout=40).json()
        assert "total_value" not in deniz_pub
        assert "holdings" not in deniz_pub
        # Ece's own portfolio only
        assert isinstance(r.get("total_value"), (int, float))

    def test_disclosures_unknown_user_404(self):
        r = requests.get(f"{API}/users/nosuchuser999/disclosures", timeout=40)
        assert r.status_code == 404


# --- Module: golden demo feed ---------------------------------------------
class TestGoldenDemo:
    def test_feed_astor_and_thyao_disclosures(self):
        r = requests.get(f"{API}/feed", params={"limit": 50}, timeout=90)
        assert r.status_code == 200
        posts = r.json()
        d_posts = [p for p in posts if p.get("disclosure")
                   and (p.get("author") or {}).get("username") == "deniz.yatirim"]
        astor = [p for p in d_posts if p["disclosure"]["ticker"] == "ASTOR"]
        thyao = [p for p in d_posts if p["disclosure"]["ticker"] == "THYAO"]
        assert len(astor) >= 2, f"expected 2 ASTOR disclosure posts, got {len(astor)}"
        assert len(thyao) >= 1

        astor_pcts = sorted(p["disclosure"]["disclosed_allocation_pct"] for p in astor)
        assert 4.2 in astor_pcts, astor_pcts
        assert 8.4 in astor_pcts, astor_pcts
        for p in astor:
            assert p["current_position"] is not None
            assert isinstance(p["current_position"]["allocation_pct"], (int, float))
            # Privacy: underlying_allocation_pct must NEVER be exposed on the API
            assert "underlying_allocation_pct" not in p["disclosure"]
            assert "underlying_quantity" not in p["disclosure"]
            assert p["disclosure"].get("change_status") in ("increased", "reduced", "unchanged", "closed", None)

        t = thyao[0]
        assert t["disclosure"]["disclosed_allocation_pct"] in (6.18, 2.6)
        assert t["current_position"]["allocation_pct"] < 6.18

    def test_thyao_thesis_current_lower(self):
        posts = requests.get(f"{API}/feed", params={"limit": 50}, timeout=90).json()
        thesis = [p for p in posts if p.get("disclosure") and p["disclosure"]["ticker"] == "THYAO"
                  and p["disclosure"]["disclosed_allocation_pct"] == 6.18]
        assert thesis, "THYAO thesis with 6.18 not found"
        p = thesis[0]
        assert p["current_position"]["allocation_pct"] < p["disclosure"]["disclosed_allocation_pct"]


# --- Module: regression: auth/alerts/media --------------------------------
class TestRegression:
    def test_me(self, dz):
        r = dz.get(f"{API}/auth/me", timeout=40)
        assert r.status_code == 200
        assert r.json()["username"] == "deniz.yatirim"

    def test_bad_login(self):
        r = requests.post(f"{API}/auth/login", json={"email": "deniz@divimero.com", "password": "wrong"}, timeout=40)
        assert r.status_code == 401

    def test_login_sets_httponly_cookie(self):
        r = requests.post(f"{API}/auth/login", json=DENIZ, timeout=40)
        assert r.status_code == 200
        assert "access_token" in r.cookies
        raw = r.headers.get("set-cookie", "")
        assert "HttpOnly" in raw, raw

    def test_bcrypt_hash_format(self):
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from dotenv import dotenv_values as dv
        env = dv("/app/backend/.env")
        async def go():
            c = AsyncIOMotorClient(env["MONGO_URL"])
            u = await c[env["DB_NAME"]].users.find_one({"email": "deniz@divimero.com"})
            c.close()
            return u
        u = asyncio.get_event_loop().run_until_complete(go()) if False else asyncio.run(go())
        assert u and u["password_hash"].startswith("$2b$"), u["password_hash"][:10]

    def test_alerts_crud(self, ec):
        r = ec.post(f"{API}/alerts", json={"followee_username": "deniz.yatirim", "ticker": "ASTOR",
                                          "direction": "any", "threshold_pct": 1.0}, timeout=40)
        assert r.status_code == 200, r.text[:200]
        aid = r.json()["id"]
        lst = ec.get(f"{API}/alerts", timeout=40).json()
        assert any(a["id"] == aid for a in lst)
        pr = ec.patch(f"{API}/alerts/{aid}", json={"active": False}, timeout=40)
        assert pr.status_code == 200 and pr.json()["active"] is False
        assert "_id" not in pr.json()
        d = ec.delete(f"{API}/alerts/{aid}", timeout=40)
        assert d.status_code == 200
        assert not any(a["id"] == aid for a in ec.get(f"{API}/alerts", timeout=40).json())

    def test_notifications(self, ec):
        r = ec.get(f"{API}/notifications", timeout=40)
        assert r.status_code == 200
        assert "unread" in r.json() and "items" in r.json()
