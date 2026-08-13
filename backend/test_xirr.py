"""Unit tests for XIRR — deterministic fixtures."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from xirr import xirr, build_cashflows


def test_xirr_simple_annual():
    # Invest 100 at t=0, get back 110 exactly 1 year later → 10%
    r = xirr([("2024-01-01", -100), ("2025-01-01", 110)])
    assert r is not None
    assert abs(r - 0.10) < 1e-3


def test_xirr_no_solution():
    # All positive → no root
    r = xirr([("2024-01-01", 100), ("2025-01-01", 110)])
    assert r is None


def test_xirr_multiple_flows():
    # Two deposits, one final value
    flows = [
        ("2024-01-01", -1000),
        ("2024-07-01", -500),
        ("2025-01-01", 1650),
    ]
    r = xirr(flows)
    assert r is not None
    # Between 5% and 30% (money-weighted)
    assert 0.03 < r < 0.35


def test_build_cashflows_ignores_buy_sell():
    txs = [
        {"type": "deposit", "date": "2024-01-01", "amount": 1000},
        {"type": "buy", "date": "2024-02-01", "quantity": 5, "price": 100},
        {"type": "withdraw", "date": "2024-06-01", "amount": 200},
    ]
    cfs = build_cashflows(txs, "2025-01-01", 1100)
    assert cfs == [
        ("2024-01-01", -1000),
        ("2024-06-01", 200),
        ("2025-01-01", 1100),
    ]


if __name__ == "__main__":
    test_xirr_simple_annual()
    test_xirr_no_solution()
    test_xirr_multiple_flows()
    test_build_cashflows_ignores_buy_sell()
    print("All XIRR tests passed.")
