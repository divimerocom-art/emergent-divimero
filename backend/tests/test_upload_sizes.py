"""Probe: /api/uploads behaviour across file sizes (Emergent Object Storage integration)."""
import io
import pytest
import requests
from conftest import API
from pymongo import MongoClient
from dotenv import dotenv_values

BE = dotenv_values("/app/backend/.env")

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def _png_bytes(size):
    body = PNG_HEADER + b"0" * max(0, size - len(PNG_HEADER))
    return body


@pytest.mark.parametrize("kb", [8, 200, 900, 1500])
def test_upload_image_sizes(deniz, kb):
    files = {"file": (f"TEST_it5_{kb}kb.png", io.BytesIO(_png_bytes(kb * 1024)), "image/png")}
    r = deniz.post(f"{API}/uploads", files=files, timeout=120)
    assert r.status_code == 200, f"{kb}KB upload -> {r.status_code} {r.text[:200]}"
    fid = r.json()["id"]
    try:
        g = requests.get(f"{API}/media/{fid}", timeout=120)
        assert g.status_code == 200
        assert len(g.content) == kb * 1024
    finally:
        MongoClient(BE["MONGO_URL"])[BE["DB_NAME"]].files.delete_one({"id": fid})


@pytest.mark.parametrize("kb", [200, 1100])
def test_upload_video_sizes(deniz, kb):
    body = b"\x00\x00\x00\x20ftypmp42" + b"0" * (kb * 1024)
    files = {"file": (f"TEST_it5_{kb}kb.mp4", io.BytesIO(body), "video/mp4")}
    r = deniz.post(f"{API}/uploads", files=files, timeout=120)
    assert r.status_code == 200, f"{kb}KB video upload -> {r.status_code} {r.text[:300]}"
    fid = r.json()["id"]
    MongoClient(BE["MONGO_URL"])[BE["DB_NAME"]].files.delete_one({"id": fid})
