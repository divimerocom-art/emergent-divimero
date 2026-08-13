"""Seed demo data for Divimero — deterministic and safe for judges.

Creates admin + two personas (Deniz creator, Ece follower + 2 extras),
transactions for Deniz that produce ~5–7% THYAO allocation, several posts
including a portfolio-linked THYAO thesis, comments, likes, follows, and
a later partial-sale transaction so the "position reduced" flow is visible.
"""
from __future__ import annotations
import os, uuid
import bcrypt
from datetime import datetime, timezone

def _id(): return str(uuid.uuid4())
def _iso(): return datetime.now(timezone.utc).isoformat()
def _hash(pw): return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

DENIZ_AVATAR = "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA2ODl8MHwxfHNlYXJjaHwyfHxwcm9mZXNzaW9uYWwlMjBpbnZlc3RvciUyMHBvcnRyYWl0fGVufDB8fHx8MTc4NjY1MjI1NXww&ixlib=rb-4.1.0&q=85"
ECE_AVATAR = "https://images.unsplash.com/photo-1560250097-0b93528c311a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA2ODl8MHwxfHNlYXJjaHwxfHxwcm9mZXNzaW9uYWwlMjBpbnZlc3RvciUyMHBvcnRyYWl0fGVufDB8fHx8MTc4NjY1MjI1NXww&ixlib=rb-4.1.0&q=85"
MERT_AVATAR = "https://images.pexels.com/photos/7567299/pexels-photo-7567299.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
POST_IMG_1 = "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzB8MHwxfHNlYXJjaHwxfHxzdG9jayUyMG1hcmtldCUyMGNoYXJ0JTIwYWJzdHJhY3R8ZW58MHx8fHwxNzg2NjUyMjU1fDA&ixlib=rb-4.1.0&q=85"

async def _upsert_user(db, email, username, name, bio, password, avatar):
    email = email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        return existing["id"]
    uid = _id()
    await db.users.insert_one({
        "id": uid, "email": email, "username": username, "display_name": name,
        "bio": bio, "avatar_url": avatar, "password_hash": _hash(password),
        "created_at": _iso(), "role": "user",
    })
    return uid

async def _add_tx(db, user_id, ttype, date, ticker=None, qty=0, price=0, fees=0, amount=0, note=""):
    await db.transactions.insert_one({
        "id": _id(), "user_id": user_id, "type": ttype, "ticker": (ticker or None),
        "date": date, "quantity": qty, "price": price, "fees": fees, "amount": amount,
        "note": note, "created_at": _iso(),
    })

async def _add_post(db, author_id, text, tickers=None, image_url=None, disclosure=None, created_at=None):
    pid = _id()
    await db.posts.insert_one({
        "id": pid, "author_id": author_id, "text": text,
        "tickers": [t.upper() for t in (tickers or [])], "image_url": image_url,
        "disclosure": disclosure, "created_at": created_at or _iso(),
    })
    return pid

async def _snapshot_thyao_disclosure(db, author_id, allocation_pct, when):
    return {
        "ticker": "THYAO",
        "underlying_allocation_pct": allocation_pct,
        "underlying_quantity": None,
        "disclosed_allocation_pct": round(allocation_pct, 2),
        "disclosed_range": None,
        "show_allocation": True,
        "allocation_mode": "exact",
        "show_quantity": False,
        "show_value": False,
        "source": "self_reported",
        "snapshot_at": when,
    }

async def seed_all(db):
    # 0. admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@divimero.com")
    admin_pw = os.environ.get("ADMIN_PASSWORD", "admin123")
    if not await db.users.find_one({"email": admin_email.lower()}):
        await db.users.insert_one({
            "id": _id(), "email": admin_email.lower(), "username": "admin",
            "display_name": "Divimero Admin", "bio": "", "avatar_url": None,
            "password_hash": _hash(admin_pw), "created_at": _iso(), "role": "admin",
        })

    demo_pw = os.environ.get("DEMO_PASSWORD", "demo1234")
    # If deniz already exists we assume seeding has been done — skip
    if await db.users.find_one({"email": "deniz@divimero.com"}):
        return

    deniz = await _upsert_user(db, "deniz@divimero.com", "deniz.yatirim", "Deniz Aksoy",
                                "BIST hisseleri üzerine uzun vadeli yatırım tezleri. Şeffaflık her şeydir.",
                                demo_pw, DENIZ_AVATAR)
    ece = await _upsert_user(db, "ece@divimero.com", "ece.market", "Ece Yıldız",
                              "Piyasayı takip eden bireysel yatırımcı. Sözleri değil, aksiyonları takip ederim.",
                              demo_pw, ECE_AVATAR)
    mert = await _upsert_user(db, "mert@divimero.com", "mert.bist", "Mert Kılıç",
                               "Temettü odaklı portföy inşa ediyorum.", demo_pw, MERT_AVATAR)
    zeynep = await _upsert_user(db, "zeynep@divimero.com", "zeynep.finance", "Zeynep Demir",
                                 "Kısa vadeli ticaret. Grafiklere odaklı.", demo_pw, None)

    # 1. Deniz transactions — deposit + buys → ~6% THYAO, plus a later partial sell
    # Deposit 200,000 TL
    await _add_tx(db, deniz, "deposit", "2025-07-01T09:00:00+00:00", amount=200000, note="İlk yatırım")
    # Buys
    await _add_tx(db, deniz, "buy", "2025-07-05T10:00:00+00:00", ticker="THYAO", qty=30, price=280.0, fees=25, note="THYAO alım")
    await _add_tx(db, deniz, "buy", "2025-07-06T10:00:00+00:00", ticker="TUPRS", qty=100, price=155.0, fees=30, note="TUPRS alım")
    await _add_tx(db, deniz, "buy", "2025-07-08T10:00:00+00:00", ticker="ASELS", qty=200, price=85.0, fees=30, note="ASELS alım")
    await _add_tx(db, deniz, "buy", "2025-07-12T10:00:00+00:00", ticker="BIMAS", qty=40, price=490.0, fees=30, note="BIMAS alım")
    await _add_tx(db, deniz, "buy", "2025-07-15T10:00:00+00:00", ticker="GARAN", qty=300, price=118.0, fees=30, note="GARAN alım")
    await _add_tx(db, deniz, "buy", "2025-08-12T10:00:00+00:00", ticker="THYAO", qty=8, price=295.0, fees=15, note="THYAO ekleme")

    # 2. Deniz posts
    await _add_post(db, deniz,
        "BIST portföyümü Divimero üzerinden şeffaf tutmaya başladım. Her tez ile birlikte pozisyon oranımı da paylaşacağım.",
        tickers=[], created_at="2025-08-10T09:00:00+00:00")

    await _add_post(db, deniz,
        "GARAN bilançosu beklentiler doğrultusunda. Net faiz marjı stabil, kredi büyümesi ılımlı. Uzun vadede pozitifim.",
        tickers=["GARAN"], created_at="2025-08-11T10:00:00+00:00")

    # 3. THYAO thesis with disclosure at ~6.2% (matches transactions)
    disc_1 = await _snapshot_thyao_disclosure(db, deniz, allocation_pct=6.18, when="2025-08-13T09:30:00+00:00")
    thyao_post = await _add_post(db, deniz,
        "THYAO tezim: yaz sezonu doluluk oranları güçlü, uzun mesafe uçuşlarındaki fiyat gücü marjları destekliyor. "
        "Portföyümde uzun vadeli tuttuğum bir pozisyon. Pozisyon oranımı açıkça paylaşıyorum, adet ve tutarı gizli tutuyorum.",
        tickers=["THYAO"], image_url=POST_IMG_1, disclosure=disc_1, created_at="2025-08-13T09:30:00+00:00")

    # 4. Later, Deniz sells part of THYAO — position reduced
    await _add_tx(db, deniz, "sell", "2025-08-25T10:00:00+00:00", ticker="THYAO", qty=20, price=310.0, fees=25, note="Kısmi kar realizasyonu")

    # A follow-up post explaining the trim, with an updated disclosure snapshot
    disc_2_alloc = 2.6  # after the sell, allocation approx drops
    disc_2 = await _snapshot_thyao_disclosure(db, deniz, allocation_pct=disc_2_alloc, when="2025-08-26T09:00:00+00:00")
    await _add_post(db, deniz,
        "THYAO'da kısmi realizasyon yaptım. Ana tez geçerli, ancak %6+ ağırlık portföyüm için yüksekti. Şeffaflık için pozisyon oranımı güncelliyorum.",
        tickers=["THYAO"], disclosure=disc_2, created_at="2025-08-26T09:00:00+00:00")

    # 5. Another user's normal post + comment on Deniz's post
    await _add_post(db, mert,
        "Temettü sezonu yaklaşıyor. Bankacılık kağıtlarında beklentim dengeli.",
        tickers=["AKBNK", "GARAN"], created_at="2025-08-14T12:00:00+00:00")

    # Ece follows Deniz + likes & comments the thyao post
    await db.follows.insert_one({"id": _id(), "follower_id": ece, "followee_id": deniz, "created_at": _iso()})
    await db.follows.insert_one({"id": _id(), "follower_id": ece, "followee_id": mert, "created_at": _iso()})
    await db.follows.insert_one({"id": _id(), "follower_id": mert, "followee_id": deniz, "created_at": _iso()})
    await db.follows.insert_one({"id": _id(), "follower_id": zeynep, "followee_id": deniz, "created_at": _iso()})

    await db.likes.insert_one({"post_id": thyao_post, "user_id": ece, "created_at": _iso()})
    await db.likes.insert_one({"post_id": thyao_post, "user_id": mert, "created_at": _iso()})
    await db.comments.insert_one({"id": _id(), "post_id": thyao_post, "user_id": ece,
        "text": "Pozisyon oranı paylaşımı için teşekkürler, çok değerli.", "created_at": _iso()})
    await db.comments.insert_one({"id": _id(), "post_id": thyao_post, "user_id": mert,
        "text": "Uzun mesafe fiyatlaması konusunda hemfikirim.", "created_at": _iso()})
