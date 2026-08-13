"""XIRR (money-weighted annualised return) via Newton's method with a bisection fallback.

Contract:
- cashflows: list of (date_iso, amount) tuples. Deposits/buys are NEGATIVE (money going in),
  withdrawals/proceeds are POSITIVE. The final position value at "as_of" must be included
  as a POSITIVE cash flow.
- as_of: ISO date string of the reference date for the final valuation.

Returns annualised rate as a decimal (e.g. 0.14 == 14%). Returns None if not solvable
(too few data points, all zero, or the algorithm fails to converge).
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Tuple, Optional


def _to_dt(iso: str) -> datetime:
    # Accept either "YYYY-MM-DD" or full ISO with T
    if "T" in iso:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return datetime.fromisoformat(iso)


def _npv(rate: float, cashflows: List[Tuple[float, float]]) -> float:
    # cashflows: list of (years_offset, amount)
    return sum(a / ((1.0 + rate) ** t) for t, a in cashflows)


def _npv_deriv(rate: float, cashflows: List[Tuple[float, float]]) -> float:
    return sum(-t * a / ((1.0 + rate) ** (t + 1)) for t, a in cashflows)


def xirr(cashflows_dated: List[Tuple[str, float]]) -> Optional[float]:
    if not cashflows_dated or len(cashflows_dated) < 2:
        return None
    # Convert dates to year offsets from the earliest cashflow
    parsed = [( _to_dt(d), a) for d, a in cashflows_dated]
    parsed.sort(key=lambda x: x[0])
    t0 = parsed[0][0]
    flows = [((d - t0).days / 365.25, a) for d, a in parsed]
    # Need at least one positive and one negative flow
    if not (any(a > 0 for _, a in flows) and any(a < 0 for _, a in flows)):
        return None

    # Newton-Raphson
    rate = 0.1
    for _ in range(80):
        f = _npv(rate, flows)
        df = _npv_deriv(rate, flows)
        if df == 0:
            break
        new_rate = rate - f / df
        if new_rate <= -0.9999:  # prevent < -1
            new_rate = (rate - 0.9999) / 2 - 0.5
        if abs(new_rate - rate) < 1e-7:
            return round(new_rate, 6)
        rate = new_rate

    # Bisection fallback in a wide range
    lo, hi = -0.9999, 10.0
    flo, fhi = _npv(lo, flows), _npv(hi, flows)
    if flo * fhi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        fm = _npv(mid, flows)
        if abs(fm) < 1e-7 or (hi - lo) < 1e-9:
            return round(mid, 6)
        if flo * fm < 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return None


def build_cashflows(transactions: List[dict], as_of_iso: str, final_value: float) -> List[Tuple[str, float]]:
    """Translate Divimero transactions into cash flows for XIRR:
    - deposit  → negative (money invested)
    - withdraw → positive (money returned)
    - buy/sell/dividend inside the portfolio boundary → NOT counted; only external
      cash movement matters for money-weighted return.
    - final_value at as_of → positive (theoretical liquidation)
    """
    flows: List[Tuple[str, float]] = []
    for tx in transactions:
        t = (tx.get("type") or "").lower()
        d = tx.get("date")
        if not d:
            continue
        if t == "deposit":
            flows.append((d, -float(tx.get("amount") or 0)))
        elif t == "withdraw":
            flows.append((d, float(tx.get("amount") or 0)))
    flows.append((as_of_iso, float(final_value)))
    return flows
