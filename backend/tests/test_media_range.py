"""Media upload + HTTP Range (206) streaming regression."""
import io
import os
import requests
import pytest
from dotenv import dotenv_values

API = (os.environ.get("REACT_APP_BACKEND_URL")
       or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/") + "/api"
BASE = API.rsplit("/api", 1)[0]

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000100000001008060000001ff3ff"
    "610000001c4944415428cf63f8ffff3f0305fe3f00e22b8d0b0c0c0c0c0c0c0c"
    "0c0c0c0c00" "3e0d0affffffff" "0000000049454e44ae426082")


def test_upload_and_range_206():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "deniz@divimero.com", "password": "demo1234"}, timeout=60)
    assert r.status_code == 200
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})

    up = s.post(f"{API}/uploads",
                files={"file": ("TEST_probe.png", io.BytesIO(PNG), "image/png")}, timeout=90)
    assert up.status_code == 200, up.text[:300]
    url = up.json()["url"]
    assert url.startswith("/api/media/")
    file_id = url.rsplit("/", 1)[-1]
    try:
        full = requests.get(BASE + url, timeout=60)
        assert full.status_code == 200
        assert full.headers.get("Accept-Ranges") == "bytes"
        total = len(full.content)

        part = requests.get(BASE + url, headers={"Range": "bytes=0-9"}, timeout=60)
        assert part.status_code == 206, part.status_code
        assert part.headers["Content-Range"] == f"bytes 0-9/{total}"
        assert len(part.content) == 10

        bad = requests.get(BASE + url, headers={"Range": f"bytes={total + 100}-"}, timeout=60)
        assert bad.status_code == 416, bad.status_code
    finally:
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        env = dotenv_values("/app/backend/.env")

        async def go():
            c = AsyncIOMotorClient(env["MONGO_URL"])
            await c[env["DB_NAME"]].files.delete_many({"id": file_id})
            c.close()
        asyncio.run(go())
