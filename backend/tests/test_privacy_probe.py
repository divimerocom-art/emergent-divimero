"""Privacy leak probe: does GET /users/{u}/disclosures respect show_allocation / allocation_mode?"""
import os
import uuid
import requests
import pytest
from dotenv import dotenv_values

API = (os.environ.get("REACT_APP_BACKEND_URL")
       or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/") + "/api"


@pytest.fixture(scope="module")
def hidden_user():
    uid = uuid.uuid4().hex[:8]
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={
        "email": f"TEST_priv_{uid}@example.com", "password": "demo1234",
        "display_name": "TEST Priv", "username": f"test_priv_{uid}"},
        timeout=40)
    assert r.status_code == 200, r.text[:200]
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    username = r.json()["user"]["username"]
    s.post(f"{API}/portfolio/transactions", json={"type": "deposit", "date": "2025-01-01", "amount": 10000}, timeout=40)
    s.post(f"{API}/portfolio/transactions", json={"type": "buy", "ticker": "ASTOR", "date": "2025-01-02",
                                                 "quantity": 10, "price": 100}, timeout=40)
    yield s, username
    # teardown: remove user + their posts/transactions directly
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


def test_hidden_allocation_is_not_leaked_by_disclosures(hidden_user):
    s, username = hidden_user
    r = s.post(f"{API}/posts", json={
        "text": "TEST hidden allocation post", "tickers": ["ASTOR"],
        "attach_position": True, "disclosure_ticker": "ASTOR",
        "show_allocation": False, "allocation_mode": "hidden",
        "show_quantity": False, "show_value": False}, timeout=60)
    assert r.status_code == 200, r.text[:200]
    post = r.json()
    assert post["disclosure"]["disclosed_allocation_pct"] is None, "hidden mode should not disclose pct"

    pub = requests.get(f"{API}/users/{username}/disclosures", timeout=60)
    assert pub.status_code == 200
    rows = pub.json()
    assert rows, "disclosure row missing"
    row = rows[0]
    # Hidden posts must not add a numeric history entry, and must not expose
    # allocation_at_publication / underlying_* anywhere on the row.
    for h in row.get("history", []):
        assert "allocation_at_publication" not in h, (
            f"PRIVACY LEAK: allocation_at_publication in history: {h}")
        assert "underlying_allocation_pct" not in h, (
            f"PRIVACY LEAK: underlying_allocation_pct in history: {h}")
    assert "underlying_allocation_pct" not in row, f"PRIVACY LEAK on row: {row}"
    assert row.get("last_disclosed") is None, (
        f"hidden-mode post should not set last_disclosed, got {row.get('last_disclosed')}")


def test_quantity_not_leaked_publicly(hidden_user):
    s, username = hidden_user
    rows = requests.get(f"{API}/users/{username}/disclosures", timeout=60).json()
    if not rows:
        pytest.skip("no disclosure rows")
    row = rows[0]
    assert "quantity" not in row.get("current", {}), f"quantity leaked in current: {row}"
    for h in row.get("history", []):
        assert "quantity" not in h, f"quantity leaked in history: {h}"
    assert "underlying_quantity" not in str(row), f"underlying_quantity leaked: {row}"
