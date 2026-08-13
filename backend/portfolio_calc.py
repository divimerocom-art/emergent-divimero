"""Deterministic portfolio calculations for the Divimero MVP.

- FIFO realized cost basis
- Current holdings from transaction history
- Allocation percentages against total portfolio value (holdings + cash)
- Unrealized P&L from current quotes

All calculations are pure functions; no LLM, no randomness.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple


TxType = str  # "buy" | "sell" | "deposit" | "withdraw" | "dividend"


@dataclass
class Holding:
    symbol: str
    quantity: float = 0.0
    avg_cost: float = 0.0          # cost basis per share (from remaining FIFO lots)
    total_cost: float = 0.0        # total cost of remaining lots
    realized_pl: float = 0.0       # cumulative realized P&L for this symbol
    dividends: float = 0.0         # cumulative dividends received for this symbol


@dataclass
class PortfolioState:
    cash: float = 0.0
    net_deposited: float = 0.0
    holdings: Dict[str, Holding] = field(default_factory=dict)
    total_realized_pl: float = 0.0
    total_dividends: float = 0.0


def _sorted_txs(txs: Iterable[dict]) -> List[dict]:
    return sorted(txs, key=lambda t: (t.get("date", ""), t.get("created_at", "")))


def compute_state(transactions: Iterable[dict]) -> PortfolioState:
    """Fold transactions into a final portfolio state using FIFO lots."""
    state = PortfolioState()
    # FIFO lot queues per symbol: deque[(qty, cost_per_share)]
    lots: Dict[str, deque] = defaultdict(deque)

    for tx in _sorted_txs(transactions):
        ttype = (tx.get("type") or "").lower()
        qty = float(tx.get("quantity") or 0)
        price = float(tx.get("price") or 0)
        fees = float(tx.get("fees") or 0)
        amount = float(tx.get("amount") or 0)
        symbol = (tx.get("ticker") or "").upper()

        if ttype == "deposit":
            state.cash += amount
            state.net_deposited += amount
        elif ttype == "withdraw":
            state.cash -= amount
            state.net_deposited -= amount
        elif ttype == "buy":
            gross = qty * price + fees
            state.cash -= gross
            lots[symbol].append((qty, price + (fees / qty if qty else 0)))
            h = state.holdings.setdefault(symbol, Holding(symbol=symbol))
            h.quantity += qty
            h.total_cost += qty * price + fees
            h.avg_cost = h.total_cost / h.quantity if h.quantity else 0
        elif ttype == "sell":
            proceeds = qty * price - fees
            state.cash += proceeds
            # consume FIFO lots
            remaining = qty
            cost_consumed = 0.0
            dq = lots[symbol]
            while remaining > 1e-9 and dq:
                lot_qty, lot_cost = dq[0]
                take = min(lot_qty, remaining)
                cost_consumed += take * lot_cost
                lot_qty -= take
                remaining -= take
                if lot_qty <= 1e-9:
                    dq.popleft()
                else:
                    dq[0] = (lot_qty, lot_cost)
            realized = proceeds - cost_consumed
            h = state.holdings.setdefault(symbol, Holding(symbol=symbol))
            h.quantity -= qty
            h.total_cost = sum(q * c for q, c in lots[symbol])
            h.avg_cost = h.total_cost / h.quantity if h.quantity > 1e-9 else 0.0
            h.realized_pl += realized
            state.total_realized_pl += realized
            if h.quantity <= 1e-9:
                h.quantity = 0.0
                h.total_cost = 0.0
                h.avg_cost = 0.0
        elif ttype == "dividend":
            state.cash += amount
            h = state.holdings.setdefault(symbol, Holding(symbol=symbol))
            h.dividends += amount
            state.total_dividends += amount

    # remove closed holdings from public view
    state.holdings = {s: h for s, h in state.holdings.items() if h.quantity > 1e-9 or h.realized_pl or h.dividends}
    return state


def valuation(state: PortfolioState, quotes: Dict[str, float]) -> dict:
    """Return the full valuation snapshot including allocations."""
    holdings_out: List[dict] = []
    holdings_value = 0.0

    for sym, h in state.holdings.items():
        px = float(quotes.get(sym, 0.0))
        mv = h.quantity * px
        holdings_value += mv
        unreal = mv - h.total_cost if h.quantity > 0 else 0.0
        holdings_out.append({
            "ticker": sym,
            "quantity": h.quantity,
            "avg_cost": h.avg_cost,
            "market_price": px,
            "market_value": mv,
            "cost_basis": h.total_cost,
            "unrealized_pl": unreal,
            "unrealized_pl_pct": (unreal / h.total_cost * 100) if h.total_cost > 0 else 0.0,
            "realized_pl": h.realized_pl,
            "dividends": h.dividends,
        })

    total_value = holdings_value + state.cash
    for row in holdings_out:
        row["allocation_pct"] = (row["market_value"] / total_value * 100) if total_value > 0 else 0.0

    holdings_out.sort(key=lambda r: r["market_value"], reverse=True)
    total_unrealized = sum(r["unrealized_pl"] for r in holdings_out)
    total_gain_loss = total_value - state.net_deposited
    return {
        "cash": state.cash,
        "net_deposited": state.net_deposited,
        "holdings_value": holdings_value,
        "total_value": total_value,
        "total_realized_pl": state.total_realized_pl,
        "total_unrealized_pl": total_unrealized,
        "total_dividends": state.total_dividends,
        "total_gain_loss": total_gain_loss,
        "total_gain_loss_pct": (total_gain_loss / state.net_deposited * 100) if state.net_deposited > 0 else 0.0,
        "holdings": holdings_out,
    }


def allocation_for_symbol(transactions: Iterable[dict], quotes: Dict[str, float], symbol: str) -> Tuple[float, float]:
    """Return (allocation_pct, quantity) for a symbol at the given point in time."""
    st = compute_state(transactions)
    v = valuation(st, quotes)
    sym = symbol.upper()
    for row in v["holdings"]:
        if row["ticker"] == sym:
            return row["allocation_pct"], row["quantity"]
    return 0.0, 0.0
