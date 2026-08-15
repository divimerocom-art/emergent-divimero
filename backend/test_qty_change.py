"""Deterministic unit tests for the trade-based disclosure classifier.

`_qty_change` is the single source of truth behind the Artırdı / Azalttı / Kapattı /
Değişmedi badge on the feed, the post detail page and the profile. It is pure — no
Mongo, no market data, no network — so the four seeded acceptance cases can be proven
offline and independently of live BIST prices. That independence is the point of the
fix: the previous allocation-based classifier moved with the share price.
"""
import sys, os

sys.path.insert(0, os.path.dirname(__file__))

# server.py reads these at import time. Motor connects lazily, so importing the module
# needs no running database.
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "divimero_test")
os.environ.setdefault("JWT_SECRET", "test-secret")

from server import _qty_at, _qty_change, _ts  # noqa: E402


# --- the demo creator's real ledger, as seeded in seed_demo.py ---------------
def _deniz_ledger():
    return [
        {"type": "deposit", "amount": 200000, "date": "2025-07-01T09:00:00+00:00"},
        {"type": "buy", "ticker": "THYAO", "quantity": 30, "price": 280.0, "date": "2025-07-05T10:00:00+00:00"},
        {"type": "buy", "ticker": "TUPRS", "quantity": 100, "price": 155.0, "date": "2025-07-06T10:00:00+00:00"},
        {"type": "buy", "ticker": "ASELS", "quantity": 200, "price": 85.0, "date": "2025-07-08T10:00:00+00:00"},
        {"type": "buy", "ticker": "ASTOR", "quantity": 140, "price": 118.0, "date": "2025-07-10T10:00:00+00:00"},
        {"type": "buy", "ticker": "BIMAS", "quantity": 40, "price": 490.0, "date": "2025-07-12T10:00:00+00:00"},
        {"type": "buy", "ticker": "GARAN", "quantity": 300, "price": 118.0, "date": "2025-07-15T10:00:00+00:00"},
        {"type": "dividend", "ticker": "GARAN", "amount": 1650, "date": "2025-08-05T10:00:00+00:00"},
        {"type": "buy", "ticker": "THYAO", "quantity": 8, "price": 295.0, "date": "2025-08-12T10:00:00+00:00"},
        {"type": "dividend", "ticker": "ASTOR", "amount": 1250, "date": "2025-08-20T10:00:00+00:00"},
        {"type": "sell", "ticker": "THYAO", "quantity": 20, "price": 310.0, "date": "2025-08-25T10:00:00+00:00"},
        {"type": "sell", "ticker": "ASTOR", "quantity": 70, "price": 126.0, "date": "2025-08-28T10:00:00+00:00"},
    ]


# --- the four seeded disclosures -------------------------------------------
def test_thyao_first_thesis_is_reduced_by_half():
    """13.08.2025: held 38 (30 + 8), holds 18 now → reduced by 20/38 ≈ 53%."""
    status, magnitude = _qty_change(_deniz_ledger(), "THYAO", "2025-08-13T09:30:00+00:00")
    assert status == "reduced", status
    assert magnitude == 53, magnitude


def test_astor_first_thesis_is_reduced_by_half():
    """15.08.2025: held 140, holds 70 now → reduced by exactly half."""
    status, magnitude = _qty_change(_deniz_ledger(), "ASTOR", "2025-08-15T09:00:00+00:00")
    assert status == "reduced", status
    assert magnitude == 50, magnitude


def test_thyao_post_sale_disclosure_is_unchanged():
    """26.08.2025: the sale already happened on 25.08 — 18 shares then, 18 now.
    The old allocation-based classifier called this 'reduced' purely on price drift."""
    status, magnitude = _qty_change(_deniz_ledger(), "THYAO", "2025-08-26T09:00:00+00:00")
    assert status == "unchanged", status
    assert magnitude is None, magnitude


def test_astor_post_trim_disclosure_is_unchanged():
    """29.08.2025: the trim already happened on 28.08 — 70 shares then, 70 now.
    The old classifier called this 'increased' because ASTOR rallied afterwards,
    directly contradicting the post's own text."""
    status, magnitude = _qty_change(_deniz_ledger(), "ASTOR", "2025-08-29T09:00:00+00:00")
    assert status == "unchanged", status
    assert magnitude is None, magnitude


# --- states the seed cannot reach ------------------------------------------
def test_full_exit_is_closed():
    txs = [
        {"type": "buy", "ticker": "KCHOL", "quantity": 10, "date": "2025-01-01T00:00:00+00:00"},
        {"type": "sell", "ticker": "KCHOL", "quantity": 10, "date": "2025-03-01T00:00:00+00:00"},
    ]
    assert _qty_change(txs, "KCHOL", "2025-02-01T00:00:00+00:00") == ("closed", None)


def test_added_shares_is_increased():
    txs = [
        {"type": "buy", "ticker": "KCHOL", "quantity": 10, "date": "2025-01-01T00:00:00+00:00"},
        {"type": "buy", "ticker": "KCHOL", "quantity": 10, "date": "2025-03-01T00:00:00+00:00"},
    ]
    assert _qty_change(txs, "KCHOL", "2025-02-01T00:00:00+00:00") == ("increased", 100)


def test_no_position_at_publication_has_no_baseline():
    """Nothing held when the post went out → no honest comparison to make."""
    txs = [{"type": "buy", "ticker": "KCHOL", "quantity": 10, "date": "2025-03-01T00:00:00+00:00"}]
    assert _qty_change(txs, "KCHOL", "2025-02-01T00:00:00+00:00") == (None, None)


def test_non_share_transactions_never_move_the_count():
    """Dividends and cash movements must not read as trades."""
    txs = [
        {"type": "buy", "ticker": "GARAN", "quantity": 300, "date": "2025-01-01T00:00:00+00:00"},
        {"type": "dividend", "ticker": "GARAN", "amount": 1650, "date": "2025-03-01T00:00:00+00:00"},
        {"type": "deposit", "amount": 5000, "date": "2025-03-02T00:00:00+00:00"},
        {"type": "withdraw", "amount": 1000, "date": "2025-03-03T00:00:00+00:00"},
    ]
    assert _qty_change(txs, "GARAN", "2025-02-01T00:00:00+00:00") == ("unchanged", None)


# --- ordering and timestamp-format robustness ------------------------------
def test_result_is_independent_of_ledger_order():
    """The batched /api/feed loads transactions from an unsorted cursor. An
    order-sensitive walk would silently drop rows and mis-report the position."""
    ordered = _deniz_ledger()
    shuffled = list(reversed(ordered))
    assert _qty_change(shuffled, "ASTOR", "2025-08-15T09:00:00+00:00") == \
           _qty_change(ordered, "ASTOR", "2025-08-15T09:00:00+00:00")
    assert _qty_change(shuffled, "THYAO", "2025-08-13T09:30:00+00:00") == \
           _qty_change(ordered, "THYAO", "2025-08-13T09:30:00+00:00")


def test_browser_and_seed_timestamp_formats_compare_by_instant():
    """The browser sends '…​.000Z', the seed and now_iso() send '…+00:00'. Comparing
    those as raw strings orders 'Z' and '+' by byte value, not by time."""
    txs = [
        {"type": "buy", "ticker": "KCHOL", "quantity": 10, "date": "2025-01-01T00:00:00.000Z"},
        {"type": "sell", "ticker": "KCHOL", "quantity": 4, "date": "2025-06-01T12:00:00.000Z"},
    ]
    # Snapshot sits between the two trades: 10 held then, 6 now → 40% reduction.
    assert _qty_change(txs, "KCHOL", "2025-03-01T00:00:00+00:00") == ("reduced", 40)


def test_trade_at_the_exact_snapshot_instant_counts_as_published():
    """A buy timestamped identically to the disclosure is part of the disclosed
    position, not a later change."""
    txs = [{"type": "buy", "ticker": "KCHOL", "quantity": 10, "date": "2025-03-01T00:00:00.000Z"}]
    assert _qty_at(txs, "KCHOL", "2025-03-01T00:00:00+00:00") == 10


def test_bare_date_transactions_are_still_understood():
    txs = [{"type": "buy", "ticker": "KCHOL", "quantity": 10, "date": "2025-01-01"}]
    assert _qty_at(txs, "KCHOL", "2025-03-01T00:00:00+00:00") == 10


def test_ts_parses_the_three_shapes_and_rejects_junk():
    assert _ts("2025-03-01T00:00:00+00:00") == _ts("2025-03-01T00:00:00.000Z")
    assert _ts("2025-03-01") is not None
    assert _ts(None) is None
    assert _ts("not-a-date") is None


# --- privacy ---------------------------------------------------------------
def test_magnitude_is_rounded_so_it_cannot_be_reversed_into_share_counts():
    """The exact quotient 20/38 recovers the denominator 19, leaking the position
    size that show_quantity=False exists to withhold. A whole percent does not."""
    _, magnitude = _qty_change(_deniz_ledger(), "THYAO", "2025-08-13T09:30:00+00:00")
    assert isinstance(magnitude, int)
    assert magnitude == 53  # not 52.63157894736842


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("All qty-change tests passed.")
