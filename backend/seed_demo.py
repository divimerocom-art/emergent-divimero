"""Seed demo data for Divimero — deterministic and safe for judges.

Creates admin + four personas: Deniz (creator), Mert (second creator), Ece
(follower) and Zeynep. Between them the seed demonstrates all four disclosure
states, because each one is derived from the ledger rather than declared:

  Mert   AKBNK  02.09  -> increased/reduced  ("Azalttı · pozisyonun ~%40'ı")
  Mert   EREGL  31.08  -> closed             ("Kapattı", full exit)
  Deniz  THYAO  13.08  -> reduced ~%53       (38 -> 18 shares)
  Deniz  ASTOR  15.08  -> reduced ~%50       (140 -> 70 shares)
  Deniz  THYAO  26.08  -> unchanged          (sold BEFORE publishing; no trade since)
  Deniz  ASTOR  29.08  -> unchanged          (sold BEFORE publishing; price drift only)

Deniz's ledger and his four disclosures are load-bearing: they are the W2
regression evidence and his portfolio totals are pinned in HANDOFF.md §5.
Change Mert's data, not his.
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

def _disclosure(ticker, allocation_pct, when):
    """A publication snapshot: the allocation the author consented to publish, frozen at `when`.
    Quantity is never recorded here — the badge is derived from the ledger at read time."""
    return {
        "ticker": ticker,
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


async def _snapshot_thyao_disclosure(db, author_id, allocation_pct, when):
    return _disclosure("THYAO", allocation_pct, when)

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

    # 1. Deniz transactions — deposit + buys → ~6% THYAO, ~8% ASTOR, plus a later partial sell
    await _add_tx(db, deniz, "deposit", "2025-07-01T09:00:00+00:00", amount=200000, note="İlk yatırım")
    await _add_tx(db, deniz, "buy", "2025-07-05T10:00:00+00:00", ticker="THYAO", qty=30, price=280.0, fees=25, note="THYAO alım")
    await _add_tx(db, deniz, "buy", "2025-07-06T10:00:00+00:00", ticker="TUPRS", qty=100, price=155.0, fees=30, note="TUPRS alım")
    await _add_tx(db, deniz, "buy", "2025-07-08T10:00:00+00:00", ticker="ASELS", qty=200, price=85.0, fees=30, note="ASELS alım")
    await _add_tx(db, deniz, "buy", "2025-07-10T10:00:00+00:00", ticker="ASTOR", qty=140, price=118.0, fees=30, note="ASTOR alım")
    await _add_tx(db, deniz, "buy", "2025-07-12T10:00:00+00:00", ticker="BIMAS", qty=40, price=490.0, fees=30, note="BIMAS alım")
    await _add_tx(db, deniz, "buy", "2025-07-15T10:00:00+00:00", ticker="GARAN", qty=300, price=118.0, fees=30, note="GARAN alım")
    await _add_tx(db, deniz, "buy", "2025-08-12T10:00:00+00:00", ticker="THYAO", qty=8, price=295.0, fees=15, note="THYAO ekleme")
    # Dividends (recorded by Deniz)
    await _add_tx(db, deniz, "dividend", "2025-08-05T10:00:00+00:00", ticker="GARAN", amount=1650, note="GARAN nakit temettü")
    await _add_tx(db, deniz, "dividend", "2025-08-20T10:00:00+00:00", ticker="ASTOR", amount=1250, note="ASTOR nakit temettü")

    # 2. Deniz posts
    intro_post = await _add_post(db, deniz,
        "BIST portföyümü Divimero üzerinden şeffaf tutmaya başladım. Her tez ile birlikte pozisyon oranımı da paylaşacağım.",
        tickers=[], created_at="2025-08-10T09:00:00+00:00")

    garan_post = await _add_post(db, deniz,
        "GARAN bilançosu beklentiler doğrultusunda. Net faiz marjı stabil, kredi büyümesi ılımlı. Uzun vadede pozitifim.",
        tickers=["GARAN"], created_at="2025-08-11T10:00:00+00:00")

    # 3. THYAO thesis with disclosure at ~6.2% (matches transactions)
    disc_1 = await _snapshot_thyao_disclosure(db, deniz, allocation_pct=6.18, when="2025-08-13T09:30:00+00:00")
    thyao_post = await _add_post(db, deniz,
        "THYAO tezim: yaz sezonu doluluk oranları güçlü, uzun mesafe uçuşlarındaki fiyat gücü marjları destekliyor. "
        "Portföyümde uzun vadeli tuttuğum bir pozisyon. Pozisyon oranımı açıkça paylaşıyorum, adet ve tutarı gizli tutuyorum.",
        tickers=["THYAO"], disclosure=disc_1, created_at="2025-08-13T09:30:00+00:00")

    # 4. Later, Deniz sells part of THYAO — position reduced
    await _add_tx(db, deniz, "sell", "2025-08-25T10:00:00+00:00", ticker="THYAO", qty=20, price=310.0, fees=25, note="Kısmi kar realizasyonu")

    # A follow-up post explaining the trim, with an updated disclosure snapshot
    disc_2_alloc = 2.6  # after the sell, allocation approx drops
    disc_2 = await _snapshot_thyao_disclosure(db, deniz, allocation_pct=disc_2_alloc, when="2025-08-26T09:00:00+00:00")
    thyao_trim_post = await _add_post(db, deniz,
        "THYAO'da kısmi realizasyon yaptım. Ana tez geçerli, ancak %6+ ağırlık portföyüm için yüksekti. Şeffaflık için pozisyon oranımı güncelliyorum.",
        tickers=["THYAO"], disclosure=disc_2, created_at="2025-08-26T09:00:00+00:00")

    # 4b. ASTOR thesis with portfolio-linked disclosure at ~8%, then later trim to ~4%
    disc_astor_1 = {
        "ticker": "ASTOR",
        "underlying_allocation_pct": 8.4,
        "underlying_quantity": None,
        "disclosed_allocation_pct": 8.4,
        "disclosed_range": None,
        "show_allocation": True, "allocation_mode": "exact",
        "show_quantity": False, "show_value": False,
        "source": "self_reported",
        "snapshot_at": "2025-08-15T09:00:00+00:00",
    }
    astor_post = await _add_post(db, deniz,
        "ASTOR tezim: Türkiye'nin transformer ve OSB elektrifikasyon talebi güçleniyor. Uzun vadeli tuttuğum bir pozisyon. "
        "Portföyümdeki oranı açıkça paylaşıyorum, adet ve tutar gizli.",
        tickers=["ASTOR"], disclosure=disc_astor_1, created_at="2025-08-15T09:00:00+00:00")

    # Later trim of ASTOR
    await _add_tx(db, deniz, "sell", "2025-08-28T10:00:00+00:00", ticker="ASTOR", qty=70, price=126.0, fees=30, note="ASTOR ağırlık düşürme")
    disc_astor_2 = {
        "ticker": "ASTOR",
        "underlying_allocation_pct": 4.2,
        "underlying_quantity": None,
        "disclosed_allocation_pct": 4.2,
        "disclosed_range": None,
        "show_allocation": True, "allocation_mode": "exact",
        "show_quantity": False, "show_value": False,
        "source": "self_reported",
        "snapshot_at": "2025-08-29T09:00:00+00:00",
    }
    astor_trim_post = await _add_post(db, deniz,
        "ASTOR pozisyonumu %8'den %4'lere indirdim. Ana tez değişmedi — portföy ağırlığı için dengeleme yaptım. "
        "Not: sonraki fiyat hareketleri güncel oranı tekrar yukarı çekmiş olabilir; bu sayfa canlı ağırlığı gösteriyor.",
        tickers=["ASTOR"], disclosure=disc_astor_2, created_at="2025-08-29T09:00:00+00:00")

    # 5. Another user's normal post + comment on Deniz's post
    mert_note_post = await _add_post(db, mert,
        "Temettü sezonu yaklaşıyor. Bankacılık kağıtlarında beklentim dengeli.",
        tickers=["AKBNK", "GARAN"], created_at="2025-08-14T12:00:00+00:00")

    # 5b. Mert is the second creator, and the one who demonstrates the two badge states
    # Deniz's ledger cannot reach. Deniz's transactions are deliberately left untouched:
    # his four disclosures are the W2 regression evidence and his portfolio totals are pinned.
    await _add_tx(db, mert, "deposit", "2025-07-02T09:00:00+00:00", amount=150000, note="Başlangıç sermayesi")
    await _add_tx(db, mert, "buy", "2025-07-08T10:00:00+00:00", ticker="AKBNK", qty=900, price=61.50, fees=40, note="AKBNK alım")
    await _add_tx(db, mert, "buy", "2025-07-09T10:00:00+00:00", ticker="GARAN", qty=300, price=118.00, fees=30, note="GARAN alım")
    await _add_tx(db, mert, "buy", "2025-07-15T10:00:00+00:00", ticker="EREGL", qty=700, price=48.20, fees=30, note="EREGL alım")
    await _add_tx(db, mert, "dividend", "2025-08-06T10:00:00+00:00", ticker="AKBNK", amount=1800, note="AKBNK nakit temettü")

    # EREGL thesis, then a full exit -> "Kapattı". The only closed position in the demo.
    disc_eregl = _disclosure("EREGL", 11.4, "2025-08-31T09:00:00+00:00")
    eregl_post = await _add_post(db, mert,
        "EREGL tezim: çelik marjlarında toparlanma bekliyorum, ihracat tarafı destekleyici. "
        "Portföyümdeki oranı paylaşıyorum, adet ve tutar gizli.",
        tickers=["EREGL"], disclosure=disc_eregl, created_at="2025-08-31T09:00:00+00:00")
    await _add_tx(db, mert, "sell", "2025-09-03T10:00:00+00:00", ticker="EREGL", qty=700, price=52.10, fees=35, note="EREGL pozisyon kapatma")

    # AKBNK thesis, then a partial sell -> "Azalttı · pozisyonun ~%40'ı". Newest card in the feed.
    disc_akbnk = _disclosure("AKBNK", 18.6, "2025-09-02T09:00:00+00:00")
    akbnk_post = await _add_post(db, mert,
        "AKBNK tezim: net faiz marjı dipten dönüyor, temettü verimi cazip. Uzun vadeli taşıdığım bir pozisyon. "
        "Tezimi paylaşıyorsam pozisyonumu da paylaşırım — oran açık, adet ve tutar gizli.",
        tickers=["AKBNK"], disclosure=disc_akbnk, created_at="2025-09-02T09:00:00+00:00")
    await _add_tx(db, mert, "sell", "2025-09-05T10:00:00+00:00", ticker="AKBNK", qty=360, price=74.30, fees=35, note="AKBNK kısmi realizasyon")

    # Ece follows Deniz + likes & comments the thyao post
    await db.follows.insert_one({"id": _id(), "follower_id": ece, "followee_id": deniz, "created_at": _iso()})
    await db.follows.insert_one({"id": _id(), "follower_id": ece, "followee_id": mert, "created_at": _iso()})
    await db.follows.insert_one({"id": _id(), "follower_id": mert, "followee_id": deniz, "created_at": _iso()})
    await db.follows.insert_one({"id": _id(), "follower_id": zeynep, "followee_id": deniz, "created_at": _iso()})

    # Engagement, dated between each post and now — seed-time timestamps made a
    # 2025 post show comments as "az önce".
    for pid, uid, when in [
        (thyao_post, ece, "2025-08-13T11:20:00+00:00"),
        (thyao_post, mert, "2025-08-13T14:05:00+00:00"),
        (thyao_post, zeynep, "2025-08-14T08:40:00+00:00"),
        (astor_post, ece, "2025-08-15T12:10:00+00:00"),
        (astor_post, zeynep, "2025-08-16T09:25:00+00:00"),
        (astor_trim_post, ece, "2025-08-29T10:15:00+00:00"),
        (astor_trim_post, mert, "2025-08-29T18:30:00+00:00"),
        (thyao_trim_post, ece, "2025-08-26T10:05:00+00:00"),
        (garan_post, mert, "2025-08-11T15:00:00+00:00"),
        (intro_post, ece, "2025-08-10T10:30:00+00:00"),
        (mert_note_post, deniz, "2025-08-14T13:10:00+00:00"),
        (eregl_post, deniz, "2025-08-31T11:45:00+00:00"),
        (eregl_post, ece, "2025-09-01T08:20:00+00:00"),
        (akbnk_post, deniz, "2025-09-02T10:40:00+00:00"),
        (akbnk_post, ece, "2025-09-02T16:05:00+00:00"),
        (akbnk_post, zeynep, "2025-09-03T09:00:00+00:00"),
    ]:
        await db.likes.insert_one({"post_id": pid, "user_id": uid, "created_at": when})

    for pid, uid, text, when in [
        (thyao_post, ece, "Pozisyon oranı paylaşımı için teşekkürler, çok değerli.", "2025-08-13T11:22:00+00:00"),
        (thyao_post, mert, "Uzun mesafe fiyatlaması konusunda hemfikirim.", "2025-08-13T14:08:00+00:00"),
        (astor_trim_post, ece, "Azalttığını rozetten değil, defterden gördüm — bu yüzden buradayım.", "2025-08-29T10:18:00+00:00"),
        (astor_post, zeynep, "OSB elektrifikasyonu tezine katılıyorum, oranı görmek ayrıca güven veriyor.", "2025-08-16T09:30:00+00:00"),
        (akbnk_post, deniz, "Temettü verimi tarafında haklısın. Oranı paylaşman tezi daha okunur kılıyor.", "2025-09-02T10:45:00+00:00"),
        (eregl_post, ece, "Çelik marjları için takipteyim, pozisyonunu izliyorum.", "2025-09-01T08:25:00+00:00"),
    ]:
        await db.comments.insert_one({"id": _id(), "post_id": pid, "user_id": uid, "text": text, "created_at": when})

    # 6. The "follow position changes" payoff needs an artifact. Ece watches Deniz's THYAO;
    # the alert already fired when he trimmed it, so /alerts is a live row and the bell has
    # an unread badge on the follower demo instead of two empty states.
    await db.alerts.insert_one({
        "id": _id(), "user_id": ece, "followee_id": deniz, "ticker": "THYAO",
        "direction": "decrease", "threshold_pct": 1.0, "created_at": "2025-08-14T09:00:00+00:00",
    })
    await db.notifications.insert_one({
        "id": _id(), "user_id": ece, "kind": "alert", "actor_id": deniz, "post_id": None,
        "ticker": "THYAO", "before_pct": 6.18, "after_pct": 2.6, "delta_pct": -3.58,
        "change_kind": "azalttı", "created_at": "2025-08-26T09:05:00+00:00", "read": False,
    })
    await db.notifications.insert_one({
        "id": _id(), "user_id": ece, "kind": "new_post", "actor_id": deniz,
        "post_id": astor_trim_post, "has_disclosure": True,
        "created_at": "2025-08-29T09:01:00+00:00", "read": False,
    })
