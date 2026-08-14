"""Iteration 6 — performance (market search / feed / portfolio) + feed batching correctness."""
import os
import time

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

DENIZ = {"email": "deniz@divimero.com", "password": "demo1234"}

TIMINGS = {}


def _timed(session, method, url, **kw):
    t0 = time.perf_counter()
    r = session.request(method, url, timeout=90, **kw)
    return r, time.perf_counter() - t0


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def auth(sess):
    r = sess.post(f"{BASE_URL}/api/auth/login", json=DENIZ)
    if r.status_code != 200:
        pytest.fail(f"Deniz login failed {r.status_code}: {r.text[:300]}")
    tok = r.json().get("access_token") or r.json().get("token")
    if not tok:
        pytest.fail(f"No token in login response: {list(r.json().keys())}")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    return s


# --- PERF: /api/market/search ------------------------------------------------
class TestMarketSearchPerf:
    def test_search_with_price_3_sequential_calls(self, sess):
        url = f"{BASE_URL}/api/market/search?q=T&with_price=true&limit=25"
        durations = []
        for i in range(3):
            r, d = _timed(sess, "GET", url)
            assert r.status_code == 200, f"call {i+1} -> {r.status_code}: {r.text[:200]}"
            rows = r.json()
            assert isinstance(rows, list) and len(rows) > 0
            assert len(rows) <= 25
            durations.append(d)
            print(f"[search q=T limit=25] call {i+1}: {d:.3f}s (rows={len(rows)})")
        TIMINGS["search"] = durations
        # price enrichment sanity on the last response
        rows = r.json()
        assert any(x.get("price") for x in rows), "no row has a price"
        for x in rows:
            assert "price_available" in x and "price_source" in x
        cold, warm = durations[0], min(durations[1:])
        print(f"[search] cold={cold:.3f}s warm_min={warm:.3f}s all={[round(x,3) for x in durations]}")
        assert cold < 5.0, f"COLD search took {cold:.3f}s (budget 5s)"
        assert warm < 0.3, f"WARM search took {warm:.3f}s (budget 300ms)"

    def test_search_limit_50_uncached_symbols(self, sess):
        """Wider net -> more symbols outside the 35-symbol prewarm set."""
        r, d = _timed(sess, "GET", f"{BASE_URL}/api/market/search?q=A&with_price=true&limit=50")
        print(f"[search q=A limit=50] cold: {d:.3f}s status={r.status_code}")
        TIMINGS["search_a50_cold"] = d
        assert r.status_code == 200
        r2, d2 = _timed(sess, "GET", f"{BASE_URL}/api/market/search?q=A&with_price=true&limit=50")
        print(f"[search q=A limit=50] warm: {d2:.3f}s")
        TIMINGS["search_a50_warm"] = d2
        assert d2 < 0.5, f"warm 50-symbol search {d2:.3f}s"
        assert d < 8.0, f"cold 50-symbol search {d:.3f}s — sequential fetch suspected"


# --- PERF + CORRECTNESS: /api/feed ------------------------------------------
class TestFeed:
    def test_feed_perf_and_shape(self, sess):
        url = f"{BASE_URL}/api/feed"
        durations = []
        for i in range(3):
            r, d = _timed(sess, "GET", url)
            assert r.status_code == 200, f"{r.status_code}: {r.text[:200]}"
            durations.append(d)
            print(f"[feed] call {i+1}: {d:.3f}s")
        posts = r.json()
        TIMINGS["feed"] = durations
        assert isinstance(posts, list) and len(posts) > 0
        warm = min(durations[1:])
        assert warm < 0.5, f"WARM feed {warm:.3f}s (budget 500ms)"

    def test_feed_disclosure_posts_have_current_position(self, sess):
        posts = sess.get(f"{BASE_URL}/api/feed", timeout=60).json()
        disc_posts = [p for p in posts if p.get("disclosure")]
        assert disc_posts, "no disclosure posts in feed"
        print(f"[feed] {len(disc_posts)}/{len(posts)} posts have a disclosure")
        valid = {"increased", "reduced", "unchanged", "closed"}
        problems = []
        for p in disc_posts:
            d = p["disclosure"]
            # private fields must never leak
            assert "underlying_allocation_pct" not in d, f"LEAK on post {p['id']}"
            if d.get("show_allocation", True):
                cp = p.get("current_position")
                if cp is None:
                    problems.append(f"{d['ticker']}: current_position is None")
                    continue
                if not isinstance(cp.get("allocation_pct"), (int, float)) or cp["allocation_pct"] <= 0:
                    problems.append(f"{d['ticker']}: allocation_pct={cp.get('allocation_pct')} not positive")
                if d.get("change_status") not in valid:
                    problems.append(f"{d['ticker']}: change_status={d.get('change_status')!r}")
                assert "quantity" not in cp, "quantity leaked in current_position"
                print(f"  {d['ticker']}: alloc={cp.get('allocation_pct')} status={d.get('change_status')}")
        assert not problems, f"feed disclosure problems: {problems}"

    def test_feed_astor_thyao_disclosures(self, sess):
        posts = sess.get(f"{BASE_URL}/api/feed", timeout=60).json()
        valid = {"increased", "reduced", "unchanged", "closed"}
        found = {}
        for p in posts:
            d = p.get("disclosure")
            if d and d.get("ticker") in ("ASTOR", "THYAO") and d.get("show_allocation", True):
                found[d["ticker"]] = (p.get("current_position"), d.get("change_status"))
        print(f"[feed] ASTOR/THYAO: {found}")
        for tk in ("ASTOR", "THYAO"):
            assert tk in found, f"{tk} disclosure post missing from feed"
            cp, status = found[tk]
            assert cp is not None, f"{tk} current_position None"
            assert cp["allocation_pct"] > 0, f"{tk} allocation_pct {cp['allocation_pct']}"
            assert status in valid, f"{tk} change_status {status!r}"

    def test_feed_matches_single_post_endpoint(self, sess):
        """Batched /feed must agree with the per-post _hydrate_post path."""
        posts = sess.get(f"{BASE_URL}/api/feed", timeout=60).json()
        mismatches = []
        for p in [x for x in posts if x.get("disclosure")][:6]:
            single = sess.get(f"{BASE_URL}/api/posts/{p['id']}", timeout=60)
            assert single.status_code == 200
            s = single.json()
            if p.get("current_position") != s.get("current_position"):
                mismatches.append(f"{p['id']} current_position feed={p.get('current_position')} single={s.get('current_position')}")
            if p["disclosure"].get("change_status") != (s.get("disclosure") or {}).get("change_status"):
                mismatches.append(f"{p['id']} change_status feed={p['disclosure'].get('change_status')} single={(s.get('disclosure') or {}).get('change_status')}")
            if p.get("likes_count") != s.get("likes_count") or p.get("comments_count") != s.get("comments_count"):
                mismatches.append(f"{p['id']} counts feed={p.get('likes_count')}/{p.get('comments_count')} single={s.get('likes_count')}/{s.get('comments_count')}")
        assert not mismatches, f"batched feed diverges from per-post hydration: {mismatches}"

    def test_feed_liked_flag_when_authenticated(self, auth):
        r, d = _timed(auth, "GET", f"{BASE_URL}/api/feed")
        print(f"[feed authed] {d:.3f}s")
        assert r.status_code == 200
        posts = r.json()
        assert all(isinstance(p.get("liked"), bool) for p in posts)


# --- PERF: /api/portfolio ---------------------------------------------------
class TestPortfolioPerf:
    def test_portfolio_perf(self, auth):
        durations = []
        for i in range(3):
            r, d = _timed(auth, "GET", f"{BASE_URL}/api/portfolio")
            assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
            durations.append(d)
            print(f"[portfolio] call {i+1}: {d:.3f}s")
        body = r.json()
        TIMINGS["portfolio"] = durations
        holdings = body.get("holdings") or []
        print(f"[portfolio] holdings={len(holdings)} total_value={body.get('total_value')}")
        assert len(holdings) > 0, "Deniz has no holdings"
        warm = min(durations[1:])
        assert warm < 0.8, f"WARM portfolio {warm:.3f}s (budget 800ms)"


# --- REGRESSION smoke -------------------------------------------------------
class TestSmoke:
    @pytest.mark.parametrize("path", [
        "/api/auth/me",
        "/api/notifications",
        "/api/alerts",
        "/api/users/deniz.yatirim",
        "/api/users/deniz.yatirim/posts",
        "/api/users/deniz.yatirim/disclosures",
    ])
    def test_authed_endpoints_200(self, auth, path):
        r, d = _timed(auth, "GET", f"{BASE_URL}{path}")
        print(f"[smoke] {path} -> {r.status_code} in {d:.3f}s")
        assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:250]}"


# --- PREWARM ----------------------------------------------------------------
class TestPrewarm:
    def test_prewarm_log_present(self):
        import re
        hits = []
        for f in ("/var/log/supervisor/backend.err.log", "/var/log/supervisor/backend.out.log"):
            try:
                with open(f, encoding="utf-8", errors="ignore") as fh:
                    hits += re.findall(r"Market cache pre-warmed: (\d+) symbols", fh.read())
            except FileNotFoundError:
                pass
        assert hits, "no 'Market cache pre-warmed' line in backend logs"
        n = int(hits[-1])
        print(f"[prewarm] last log entry: {n} symbols")
        assert n >= 30, f"prewarmed only {n} symbols"


def test_zz_print_timing_summary():
    print("\n=== TIMING SUMMARY ===")
    for k, v in TIMINGS.items():
        print(f"{k}: {v if not isinstance(v, list) else [round(x, 3) for x in v]}")
