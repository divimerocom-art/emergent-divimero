import os
import requests
import pytest
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = BASE_URL + "/api"

DENIZ = {"email": "deniz@divimero.com", "password": "demo1234"}
ECE = {"email": "ece@divimero.com", "password": "demo1234"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"Login failed for {creds['email']}: {r.status_code} {r.text[:300]}")
    tok = r.json().get("token")
    if not tok:
        pytest.fail("No token in login response")
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="session")
def api_base():
    return API


@pytest.fixture(scope="session")
def deniz():
    return _login(DENIZ)


@pytest.fixture(scope="session")
def ece():
    return _login(ECE)


# --- Global teardown: purge artefacts created by the test suites -------------
# Previous iterations left "TEST ..." posts on the demo user (deniz) and
# throwaway registered users behind, which polluted the golden demo feed.
def pytest_sessionfinish(session, exitstatus):
    """Purge once, in the xdist CONTROLLER only.

    Previously this was a session-scoped autouse fixture, which under
    `-n 2 --dist loadscope` executes inside EVERY worker. The first worker to
    finish deleted the throwaway TEST_ user that a still-running worker was
    authenticated as, producing intermittent 401 "Kullanıcı bulunamadı".
    """
    if hasattr(session.config, "workerinput"):
        return  # xdist worker -> controller does the cleanup
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    from dotenv import dotenv_values as _dv

    env = _dv("/app/backend/.env")

    async def purge():
        c = AsyncIOMotorClient(env["MONGO_URL"])
        db = c[env["DB_NAME"]]
        async for p in db.posts.find({"text": {"$regex": "^TEST"}}, {"id": 1}):
            await db.notifications.delete_many({"post_id": p["id"]})
            await db.likes.delete_many({"post_id": p["id"]})
            await db.comments.delete_many({"post_id": p["id"]})
            await db.posts.delete_one({"id": p["id"]})
        async for u in db.users.find({"$or": [{"username": {"$regex": "^test_"}},
                                              {"email": {"$regex": "^TEST_"}},
                                              {"email": {"$regex": "@example.com$"}}]}, {"id": 1}):
            await db.posts.delete_many({"author_id": u["id"]})
            await db.transactions.delete_many({"user_id": u["id"]})
            await db.notifications.delete_many({"user_id": u["id"]})
            await db.alerts.delete_many({"user_id": u["id"]})
            await db.follows.delete_many({"$or": [{"follower_id": u["id"]}, {"followee_id": u["id"]}]})
            await db.users.delete_one({"id": u["id"]})
        c.close()

    asyncio.run(purge())
