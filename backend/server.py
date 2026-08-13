"""Divimero backend — FastAPI + MongoDB.

Turkish-first BIST portfolio tracker + financial social network.
"""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import uuid
import logging
import asyncio
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, status, UploadFile, File, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response as FastResponse
from starlette.concurrency import run_in_threadpool
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from market_data import get_market_data_provider
from portfolio_calc import compute_state, valuation, allocation_for_symbol
from xirr import xirr, build_cashflows
from storage import init_storage, put_object, get_object, make_upload_path, APP_NAME as STORAGE_APP

# --- Config / DB ---
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = "HS256"
ACCESS_TTL_MIN = 60 * 24 * 7   # 7 days for a smooth judge demo
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="Divimero API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("divimero")

# --- Helpers ----------------------------------------------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def new_id() -> str:
    return str(uuid.uuid4())

def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_pw(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False

def make_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TTL_MIN), "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

async def get_current_user(request: Request) -> dict:
    token = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Kimlik doğrulama gerekli")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Oturum süresi doldu")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Geçersiz oturum")
    user = await db.users.find_one({"id": payload["sub"]}, {"password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı")
    user.pop("_id", None)
    return user

def public_user(u: dict) -> dict:
    return {
        "id": u["id"],
        "username": u.get("username"),
        "display_name": u.get("display_name"),
        "bio": u.get("bio", ""),
        "avatar_url": u.get("avatar_url"),
        "created_at": u.get("created_at"),
    }

# --- Models -----------------------------------------------------------------
class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: EmailStr
    password: str = Field(min_length=6)
    display_name: str = Field(min_length=1, max_length=60)
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_.]+$")

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

class TransactionIn(BaseModel):
    type: Literal["buy", "sell", "deposit", "withdraw", "dividend"]
    ticker: Optional[str] = None
    date: str            # ISO
    quantity: Optional[float] = 0
    price: Optional[float] = 0
    fees: Optional[float] = 0
    amount: Optional[float] = 0
    note: Optional[str] = ""

class PostIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    tickers: List[str] = []
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    # Portfolio disclosure controls
    attach_position: bool = False
    disclosure_ticker: Optional[str] = None
    show_allocation: bool = True
    allocation_mode: Literal["exact", "range", "hidden"] = "exact"
    show_quantity: bool = False
    show_value: bool = False

class CommentIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)

class AlertIn(BaseModel):
    followee_username: str
    ticker: str
    direction: Literal["any", "increase", "decrease"] = "any"
    threshold_pct: float = Field(gt=0, le=100)

# --- Auth endpoints ---------------------------------------------------------
@api.post("/auth/register")
async def register(payload: RegisterIn, response: Response):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Bu e-posta zaten kayıtlı")
    if await db.users.find_one({"username": payload.username.lower()}):
        raise HTTPException(status_code=400, detail="Bu kullanıcı adı alınmış")
    user = {
        "id": new_id(),
        "email": email,
        "username": payload.username.lower(),
        "display_name": payload.display_name,
        "bio": "",
        "avatar_url": None,
        "password_hash": hash_pw(payload.password),
        "created_at": now_iso(),
        "role": "user",
    }
    await db.users.insert_one(user)
    token = make_token(user["id"])
    response.set_cookie("access_token", token, max_age=ACCESS_TTL_MIN * 60, httponly=True, samesite="none", secure=True, path="/")
    return {"token": token, "user": public_user(user)}

@api.post("/auth/login")
async def login(payload: LoginIn, response: Response):
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_pw(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")
    token = make_token(user["id"])
    response.set_cookie("access_token", token, max_age=ACCESS_TTL_MIN * 60, httponly=True, samesite="none", secure=True, path="/")
    return {"token": token, "user": public_user(user)}

@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}

@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return public_user(user)

@api.patch("/auth/me")
async def update_me(update: ProfileUpdate, user=Depends(get_current_user)):
    doc = {k: v for k, v in update.model_dump(exclude_unset=True).items() if v is not None}
    if doc:
        await db.users.update_one({"id": user["id"]}, {"$set": doc})
    fresh = await db.users.find_one({"id": user["id"]}, {"password_hash": 0, "_id": 0})
    return public_user(fresh)

# --- Users / Follow ---------------------------------------------------------
@api.get("/users/{username}")
async def get_user(username: str, request: Request):
    u = await db.users.find_one({"username": username.lower()}, {"password_hash": 0, "_id": 0})
    if not u:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    followers = await db.follows.count_documents({"followee_id": u["id"]})
    following = await db.follows.count_documents({"follower_id": u["id"]})
    is_following = False
    try:
        me_user = await get_current_user(request)
        is_following = bool(await db.follows.find_one({"follower_id": me_user["id"], "followee_id": u["id"]}))
    except HTTPException:
        pass
    return {**public_user(u), "followers_count": followers, "following_count": following, "is_following": is_following}

@api.post("/users/{username}/follow")
async def follow(username: str, user=Depends(get_current_user)):
    target = await db.users.find_one({"username": username.lower()})
    if not target:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    if target["id"] == user["id"]:
        raise HTTPException(400, "Kendinizi takip edemezsiniz")
    exists = await db.follows.find_one({"follower_id": user["id"], "followee_id": target["id"]})
    if exists:
        await db.follows.delete_one({"_id": exists["_id"]})
        return {"following": False}
    await db.follows.insert_one({"id": new_id(), "follower_id": user["id"], "followee_id": target["id"], "created_at": now_iso()})
    return {"following": True}

# --- Portfolio --------------------------------------------------------------
async def _user_txs(user_id: str) -> list:
    return await db.transactions.find({"user_id": user_id}, {"_id": 0}).sort("date", 1).to_list(5000)

async def _portfolio_valuation(user_id: str) -> dict:
    txs = await _user_txs(user_id)
    state = compute_state(txs)
    provider = get_market_data_provider()
    symbols = list(state.holdings.keys())
    quotes = {s: q.price for s, q in provider.get_quotes(symbols).items()}
    return valuation(state, quotes)

@api.get("/portfolio")
async def my_portfolio(user=Depends(get_current_user)):
    val = await _portfolio_valuation(user["id"])
    val["source"] = get_market_data_provider().name
    # Money-weighted annualised return (XIRR)
    txs = await _user_txs(user["id"])
    try:
        cfs = build_cashflows(txs, now_iso(), val["total_value"])
        r = xirr(cfs)
        val["xirr"] = r
    except Exception:
        val["xirr"] = None
    return val

@api.get("/portfolio/transactions")
async def list_transactions(user=Depends(get_current_user)):
    return await _user_txs(user["id"])

@api.post("/portfolio/transactions")
async def create_transaction(tx: TransactionIn, user=Depends(get_current_user)):
    doc = tx.model_dump()
    doc["id"] = new_id()
    doc["user_id"] = user["id"]
    doc["ticker"] = (doc.get("ticker") or "").upper() or None
    doc["created_at"] = now_iso()
    # Capture pre-tx allocations for tickers we care about (this tx + all active alerts on the user)
    watched = set()
    if doc["ticker"]:
        watched.add(doc["ticker"])
    async for a in db.alerts.find({"followee_id": user["id"], "active": True}):
        watched.add(a["ticker"])
    pre_allocs: dict = {}
    if watched:
        for sym in watched:
            a, _ = await _allocation_for(user["id"], sym)
            pre_allocs[sym] = a
    await db.transactions.insert_one(doc)
    doc.pop("_id", None)
    # Fire alerts for followers watching this creator on any changed ticker
    if watched:
        await _check_and_fire_alerts(user["id"], pre_allocs)
    return doc

@api.delete("/portfolio/transactions/{tx_id}")
async def delete_transaction(tx_id: str, user=Depends(get_current_user)):
    r = await db.transactions.delete_one({"id": tx_id, "user_id": user["id"]})
    if r.deleted_count == 0:
        raise HTTPException(404, "İşlem bulunamadı")
    return {"ok": True}

@api.get("/portfolio/performance")
async def performance(user=Depends(get_current_user)):
    """Build a simple time series of portfolio value using deposits + FIFO cost basis.
    Real market history would need external data; we approximate day-end value using
    current quote applied at each cumulative holdings step (safe demo behaviour)."""
    txs = await _user_txs(user["id"])
    if not txs:
        return {"series": []}
    provider = get_market_data_provider()
    series = []
    running = []
    for tx in sorted(txs, key=lambda t: t.get("date", "")):
        running.append(tx)
        st = compute_state(running)
        symbols = list(st.holdings.keys())
        quotes = {s: q.price for s, q in provider.get_quotes(symbols).items()}
        v = valuation(st, quotes)
        series.append({"date": tx["date"][:10], "value": round(v["total_value"], 2)})
    return {"series": series}

# --- Market data ------------------------------------------------------------
@api.get("/market/tickers")
async def list_tickers():
    prov = get_market_data_provider()
    return [t.__dict__ for t in prov.list_tickers()]

@api.get("/market/quote/{symbol}")
async def get_quote(symbol: str):
    prov = get_market_data_provider()
    q = prov.get_quote(symbol)
    if not q:
        raise HTTPException(404, "Sembol bulunamadı")
    return q.__dict__

# --- Social: Posts / Feed ---------------------------------------------------
def _bucket_range(pct: float) -> str:
    if pct <= 0: return "0%"
    if pct < 1: return "<%1"
    if pct < 3: return "%1-3"
    if pct < 5: return "%3-5"
    if pct < 10: return "%5-10"
    if pct < 20: return "%10-20"
    return ">%20"

async def _snapshot_disclosure(user_id: str, payload: PostIn) -> Optional[dict]:
    if not payload.attach_position or not payload.disclosure_ticker:
        return None
    sym = payload.disclosure_ticker.upper()
    txs = await _user_txs(user_id)
    provider = get_market_data_provider()
    all_syms = list({(t.get("ticker") or "").upper() for t in txs if t.get("ticker")})
    quotes = {s: q.price for s, q in provider.get_quotes(all_syms).items()}
    alloc, qty = allocation_for_symbol(txs, quotes, sym)

    disclosed_alloc: Optional[float] = None
    disclosed_range: Optional[str] = None
    if payload.show_allocation:
        if payload.allocation_mode == "exact":
            disclosed_alloc = round(alloc, 2)
        elif payload.allocation_mode == "range":
            disclosed_range = _bucket_range(alloc)
    return {
        "ticker": sym,
        "underlying_allocation_pct": round(alloc, 4),
        "underlying_quantity": qty,
        "disclosed_allocation_pct": disclosed_alloc,
        "disclosed_range": disclosed_range,
        "show_allocation": payload.show_allocation,
        "allocation_mode": payload.allocation_mode,
        "show_quantity": payload.show_quantity,
        "show_value": payload.show_value,
        "source": "self_reported",
        "snapshot_at": now_iso(),
    }

@api.post("/posts")
async def create_post(payload: PostIn, user=Depends(get_current_user)):
    disclosure = await _snapshot_disclosure(user["id"], payload)
    post = {
        "id": new_id(),
        "author_id": user["id"],
        "text": payload.text,
        "tickers": [t.upper() for t in payload.tickers[:5]],
        "image_url": payload.image_url,
        "video_url": payload.video_url,
        "disclosure": disclosure,
        "created_at": now_iso(),
    }
    await db.posts.insert_one(post)
    post.pop("_id", None)
    # Fan-out notifications to followers
    follower_ids = [f["follower_id"] async for f in db.follows.find({"followee_id": user["id"]})]
    if follower_ids:
        notif_docs = [{
            "id": new_id(), "user_id": fid, "kind": "new_post",
            "actor_id": user["id"], "post_id": post["id"],
            "has_disclosure": bool(disclosure),
            "created_at": now_iso(), "read": False,
        } for fid in follower_ids]
        await db.notifications.insert_many(notif_docs)
    return await _hydrate_post(post, viewer_id=user["id"])

async def _current_allocation(author_id: str, ticker: str) -> dict:
    txs = await _user_txs(author_id)
    provider = get_market_data_provider()
    all_syms = list({(t.get("ticker") or "").upper() for t in txs if t.get("ticker")})
    quotes = {s: q.price for s, q in provider.get_quotes(all_syms).items()}
    alloc, qty = allocation_for_symbol(txs, quotes, ticker)
    return {"allocation_pct": round(alloc, 4), "quantity": qty}

async def _hydrate_post(post: dict, viewer_id: Optional[str]) -> dict:
    author = await db.users.find_one({"id": post["author_id"]}, {"password_hash": 0, "_id": 0})
    likes_count = await db.likes.count_documents({"post_id": post["id"]})
    comments_count = await db.comments.count_documents({"post_id": post["id"]})
    liked = False
    if viewer_id:
        liked = bool(await db.likes.find_one({"post_id": post["id"], "user_id": viewer_id}))
    current = None
    if post.get("disclosure"):
        current = await _current_allocation(post["author_id"], post["disclosure"]["ticker"])
    return {
        **post,
        "author": public_user(author) if author else None,
        "likes_count": likes_count,
        "comments_count": comments_count,
        "liked": liked,
        "current_position": current,
    }

@api.get("/feed")
async def feed(request: Request, limit: int = 30):
    viewer = None
    try:
        viewer = (await get_current_user(request))["id"]
    except HTTPException:
        pass
    posts = await db.posts.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return [await _hydrate_post(p, viewer) for p in posts]

@api.get("/posts/{post_id}")
async def get_post(post_id: str, request: Request):
    viewer = None
    try: viewer = (await get_current_user(request))["id"]
    except HTTPException: pass
    p = await db.posts.find_one({"id": post_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Gönderi bulunamadı")
    return await _hydrate_post(p, viewer)

@api.post("/posts/{post_id}/like")
async def like_post(post_id: str, user=Depends(get_current_user)):
    p = await db.posts.find_one({"id": post_id})
    if not p:
        raise HTTPException(404, "Gönderi bulunamadı")
    existing = await db.likes.find_one({"post_id": post_id, "user_id": user["id"]})
    if existing:
        await db.likes.delete_one({"_id": existing["_id"]})
        return {"liked": False}
    await db.likes.insert_one({"post_id": post_id, "user_id": user["id"], "created_at": now_iso()})
    return {"liked": True}

@api.get("/posts/{post_id}/comments")
async def list_comments(post_id: str):
    rows = await db.comments.find({"post_id": post_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
    out = []
    for c in rows:
        u = await db.users.find_one({"id": c["user_id"]}, {"password_hash": 0, "_id": 0})
        out.append({**c, "author": public_user(u) if u else None})
    return out

@api.post("/posts/{post_id}/comments")
async def add_comment(post_id: str, body: CommentIn, user=Depends(get_current_user)):
    p = await db.posts.find_one({"id": post_id})
    if not p:
        raise HTTPException(404, "Gönderi bulunamadı")
    c = {"id": new_id(), "post_id": post_id, "user_id": user["id"], "text": body.text, "created_at": now_iso()}
    await db.comments.insert_one(c)
    c.pop("_id", None)
    return {**c, "author": public_user(user)}

@api.get("/users/{username}/posts")
async def user_posts(username: str, request: Request):
    u = await db.users.find_one({"username": username.lower()})
    if not u:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    viewer = None
    try: viewer = (await get_current_user(request))["id"]
    except HTTPException: pass
    posts = await db.posts.find({"author_id": u["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [await _hydrate_post(p, viewer) for p in posts]

@api.get("/users/{username}/disclosures")
async def user_disclosures(username: str):
    """Return only the tickers the user has voluntarily disclosed via posts."""
    u = await db.users.find_one({"username": username.lower()})
    if not u:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    posts = await db.posts.find({"author_id": u["id"], "disclosure": {"$ne": None}}, {"_id": 0}).sort("created_at", 1).to_list(500)
    by_ticker: dict = {}
    for p in posts:
        d = p.get("disclosure")
        if not d: continue
        t = d["ticker"]
        entry = by_ticker.setdefault(t, {"ticker": t, "history": []})
        entry["history"].append({
            "post_id": p["id"], "date": p["created_at"],
            "allocation_at_publication": d["underlying_allocation_pct"],
        })
    # attach current allocation
    for t, entry in by_ticker.items():
        cur = await _current_allocation(u["id"], t)
        entry["current"] = cur
        entry["opened_at"] = entry["history"][0]["date"]
        entry["last_disclosed"] = entry["history"][-1]["allocation_at_publication"]
    return list(by_ticker.values())

# --- Uploads (Emergent Object Storage) -------------------------------------
ALLOWED_IMAGE = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEO = {"video/mp4", "video/quicktime", "video/webm"}
MAX_IMAGE_MB = 8
MAX_VIDEO_MB = 60

@api.post("/uploads")
async def upload_media(file: UploadFile = File(...), user=Depends(get_current_user)):
    ctype = (file.content_type or "").lower()
    is_image = ctype in ALLOWED_IMAGE
    is_video = ctype in ALLOWED_VIDEO
    if not (is_image or is_video):
        raise HTTPException(400, "Desteklenmeyen dosya türü")
    data = await file.read()
    size_mb = len(data) / (1024 * 1024)
    if is_image and size_mb > MAX_IMAGE_MB:
        raise HTTPException(413, f"Görsel {MAX_IMAGE_MB} MB sınırını aşıyor")
    if is_video and size_mb > MAX_VIDEO_MB:
        raise HTTPException(413, f"Video {MAX_VIDEO_MB} MB sınırını aşıyor")
    path = make_upload_path(user["id"], file.filename or ("upload.bin"))
    try:
        result = await run_in_threadpool(put_object, path, data, ctype)
    except Exception as e:
        log.exception("Upload failed")
        raise HTTPException(502, f"Yükleme başarısız: {e}")
    record = {
        "id": new_id(),
        "storage_path": result["path"],
        "user_id": user["id"],
        "content_type": ctype,
        "size": result.get("size", len(data)),
        "original_filename": file.filename,
        "kind": "image" if is_image else "video",
        "is_deleted": False,
        "created_at": now_iso(),
    }
    await db.files.insert_one(record)
    return {"id": record["id"], "url": f"/api/media/{record['id']}", "content_type": ctype, "kind": record["kind"]}

@api.get("/media/{file_id}")
async def get_media(file_id: str, request: Request):
    rec = await db.files.find_one({"id": file_id, "is_deleted": False})
    if not rec:
        raise HTTPException(404, "Dosya bulunamadı")
    try:
        data, ct = await run_in_threadpool(get_object, rec["storage_path"])
    except Exception:
        raise HTTPException(502, "Depolama erişimi başarısız")
    media_type = rec.get("content_type") or ct or "application/octet-stream"
    total = len(data)
    etag = f'W/"{file_id}-{total}"'

    # 304 Not Modified
    if request.headers.get("if-none-match") == etag:
        return FastResponse(status_code=304, headers={"ETag": etag, "Cache-Control": "public, max-age=86400"})

    range_header = request.headers.get("range")
    base_headers = {
        "ETag": etag,
        "Cache-Control": "public, max-age=86400",
        "Accept-Ranges": "bytes",
    }
    if range_header and range_header.startswith("bytes="):
        try:
            rng = range_header[6:].split(",")[0].strip()
            start_s, end_s = rng.split("-")
            start = int(start_s) if start_s else 0
            end = int(end_s) if end_s else total - 1
            if start >= total or end >= total or start > end:
                return FastResponse(status_code=416, headers={**base_headers, "Content-Range": f"bytes */{total}"})
            chunk = data[start:end + 1]
            return FastResponse(
                content=chunk,
                status_code=206,
                media_type=media_type,
                headers={
                    **base_headers,
                    "Content-Range": f"bytes {start}-{end}/{total}",
                    "Content-Length": str(len(chunk)),
                },
            )
        except ValueError:
            pass  # fall through to full 200

    return FastResponse(content=data, media_type=media_type,
                        headers={**base_headers, "Content-Length": str(total)})

# --- Notifications ---------------------------------------------------------
async def _allocation_for(user_id: str, symbol: str) -> tuple[float, float]:
    txs = await _user_txs(user_id)
    provider = get_market_data_provider()
    all_syms = list({(t.get("ticker") or "").upper() for t in txs if t.get("ticker")})
    quotes = {s: q.price for s, q in provider.get_quotes(all_syms).items()}
    return allocation_for_symbol(txs, quotes, symbol)


async def _check_and_fire_alerts(followee_id: str, pre_allocs: dict):
    """After a transaction is inserted for `followee_id`, check any active alerts
    on their tickers and fire notifications for followers whose thresholds are met."""
    async for alert in db.alerts.find({"followee_id": followee_id, "active": True}):
        sym = alert["ticker"]
        pre = pre_allocs.get(sym)
        if pre is None:
            continue
        post_alloc, _ = await _allocation_for(followee_id, sym)
        diff = post_alloc - pre
        direction = alert["direction"]
        if direction == "increase" and diff <= 0:
            continue
        if direction == "decrease" and diff >= 0:
            continue
        if abs(diff) < float(alert["threshold_pct"]):
            continue
        change_kind = "artırdı" if diff > 0 else ("kapattı" if post_alloc < 0.05 else "azalttı")
        notif = {
            "id": new_id(),
            "user_id": alert["user_id"],
            "kind": "alert",
            "actor_id": followee_id,
            "post_id": None,
            "ticker": sym,
            "before_pct": round(pre, 4),
            "after_pct": round(post_alloc, 4),
            "delta_pct": round(diff, 4),
            "change_kind": change_kind,
            "created_at": now_iso(),
            "read": False,
        }
        await db.notifications.insert_one(notif)


@api.get("/alerts")
async def list_alerts(user=Depends(get_current_user)):
    rows = await db.alerts.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    out = []
    for a in rows:
        f = await db.users.find_one({"id": a["followee_id"]}, {"password_hash": 0, "_id": 0})
        out.append({**a, "followee": public_user(f) if f else None})
    return out


@api.post("/alerts")
async def create_alert(payload: AlertIn, user=Depends(get_current_user)):
    followee = await db.users.find_one({"username": payload.followee_username.lower()})
    if not followee:
        raise HTTPException(404, "Yaratıcı bulunamadı")
    if followee["id"] == user["id"]:
        raise HTTPException(400, "Kendinize uyarı kuramazsınız")
    sym = payload.ticker.upper()
    # replace any existing alert on the same (creator, ticker) pair
    await db.alerts.delete_many({"user_id": user["id"], "followee_id": followee["id"], "ticker": sym})
    doc = {
        "id": new_id(),
        "user_id": user["id"],
        "followee_id": followee["id"],
        "ticker": sym,
        "direction": payload.direction,
        "threshold_pct": payload.threshold_pct,
        "active": True,
        "created_at": now_iso(),
    }
    await db.alerts.insert_one(doc)
    doc.pop("_id", None)
    return {**doc, "followee": public_user(followee)}


@api.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str, user=Depends(get_current_user)):
    r = await db.alerts.delete_one({"id": alert_id, "user_id": user["id"]})
    if r.deleted_count == 0:
        raise HTTPException(404, "Uyarı bulunamadı")
    return {"ok": True}


@api.get("/notifications")
@api.get("/notifications")
async def list_notifications(user=Depends(get_current_user), limit: int = 30):
    rows = await db.notifications.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    unread = await db.notifications.count_documents({"user_id": user["id"], "read": False})
    out = []
    for n in rows:
        actor = await db.users.find_one({"id": n["actor_id"]}, {"password_hash": 0, "_id": 0})
        post = await db.posts.find_one({"id": n["post_id"]}, {"_id": 0}) if n.get("post_id") else None
        out.append({
            **n,
            "actor": public_user(actor) if actor else None,
            "post_preview": (post.get("text","")[:120] if post else None),
            "post_ticker": (post.get("disclosure",{}) or {}).get("ticker") if post else None,
        })
    return {"unread": unread, "items": out}

@api.post("/notifications/read")
async def mark_all_read(user=Depends(get_current_user)):
    r = await db.notifications.update_many({"user_id": user["id"], "read": False}, {"$set": {"read": True}})
    return {"ok": True, "modified": r.modified_count}

# --- Debug/system ---
@api.get("/")
async def root():
    return {"app": "Divimero", "status": "ok", "market_data_source": "demo"}

# --- Startup ---
app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    await db.transactions.create_index([("user_id", 1), ("date", 1)])
    await db.posts.create_index([("author_id", 1), ("created_at", -1)])
    await db.follows.create_index([("follower_id", 1), ("followee_id", 1)], unique=True)
    await db.follows.create_index("followee_id")
    await db.likes.create_index([("post_id", 1), ("user_id", 1)], unique=True)
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    await db.alerts.create_index([("user_id", 1), ("followee_id", 1), ("ticker", 1)], unique=True)
    await db.files.create_index("id", unique=True)
    # Best-effort init of Emergent object storage
    try:
        init_storage()
        log.info("Object storage initialized")
    except Exception as e:
        log.warning("Object storage init deferred: %s", e)
    # seed admin + demo
    from seed_demo import seed_all
    try:
        await seed_all(db)
        log.info("Demo seeding complete.")
    except Exception as e:
        log.exception("Seeding failed: %s", e)

@app.on_event("shutdown")
async def shutdown():
    client.close()
