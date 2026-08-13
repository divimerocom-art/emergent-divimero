"""Deterministic unit tests for portfolio calculations."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from portfolio_calc import compute_state, valuation, allocation_for_symbol


def _txs_basic():
    return [
        {"type": "deposit", "amount": 100000, "date": "2025-01-01"},
        {"type": "buy", "ticker": "THYAO", "quantity": 100, "price": 300, "fees": 0, "date": "2025-01-05"},
        {"type": "buy", "ticker": "THYAO", "quantity": 100, "price": 320, "fees": 0, "date": "2025-02-05"},
        {"type": "sell", "ticker": "THYAO", "quantity": 50, "price": 350, "fees": 0, "date": "2025-03-05"},
    ]


def test_fifo_realized_pl():
    st = compute_state(_txs_basic())
    # sold 50 units from the first FIFO lot (300) → realized = 50*(350-300) = 2500
    assert abs(st.total_realized_pl - 2500) < 1e-6
    h = st.holdings["THYAO"]
    # 50 remaining at 300 + 100 at 320 → total cost = 15000 + 32000 = 47000
    assert abs(h.total_cost - 47000) < 1e-6
    assert abs(h.quantity - 150) < 1e-6


def test_cash_and_deposit():
    st = compute_state(_txs_basic())
    # cash: 100000 - 30000 - 32000 + 17500 = 55500
    assert abs(st.cash - 55500) < 1e-6
    assert abs(st.net_deposited - 100000) < 1e-6


def test_allocation_percentage():
    quotes = {"THYAO": 340.0}
    st = compute_state(_txs_basic())
    val = valuation(st, quotes)
    # holdings MV = 150 * 340 = 51000; total = 51000 + 55500 = 106500
    assert abs(val["holdings_value"] - 51000) < 1e-6
    assert abs(val["total_value"] - 106500) < 1e-6
    row = val["holdings"][0]
    assert row["ticker"] == "THYAO"
    assert abs(row["allocation_pct"] - (51000/106500*100)) < 1e-6


def test_allocation_for_symbol_helper():
    quotes = {"THYAO": 340.0}
    alloc, qty = allocation_for_symbol(_txs_basic(), quotes, "THYAO")
    assert abs(qty - 150) < 1e-6
    assert abs(alloc - (51000/106500*100)) < 1e-6


def test_closed_position():
    txs = [
        {"type": "deposit", "amount": 10000, "date": "2025-01-01"},
        {"type": "buy", "ticker": "ASELS", "quantity": 100, "price": 80, "fees": 0, "date": "2025-01-05"},
        {"type": "sell", "ticker": "ASELS", "quantity": 100, "price": 95, "fees": 0, "date": "2025-02-05"},
    ]
    st = compute_state(txs)
    assert abs(st.total_realized_pl - 1500) < 1e-6
    # holding stays for realized pl reporting but quantity is 0
    if "ASELS" in st.holdings:
        assert st.holdings["ASELS"].quantity == 0


def test_dividend_flow():
    txs = [
        {"type": "deposit", "amount": 10000, "date": "2025-01-01"},
        {"type": "buy", "ticker": "GARAN", "quantity": 100, "price": 100, "fees": 0, "date": "2025-01-05"},
        {"type": "dividend", "ticker": "GARAN", "amount": 500, "date": "2025-03-01"},
    ]
    st = compute_state(txs)
    assert abs(st.total_dividends - 500) < 1e-6
    assert abs(st.cash - (10000 - 10000 + 500)) < 1e-6


if __name__ == "__main__":
    test_fifo_realized_pl()
    test_cash_and_deposit()
    test_allocation_percentage()
    test_allocation_for_symbol_helper()
    test_closed_position()
    test_dividend_flow()
    print("All portfolio tests passed.")
