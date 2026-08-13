"""Market data provider abstraction.

For the Divimero MVP, we ship a deterministic DemoMarketDataProvider that
returns clearly-labelled demo prices for BIST tickers. Replacing this with a
real provider (e.g. Fintables, BIST API) only requires implementing the same
interface and swapping the provider in `get_market_data_provider()`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List


@dataclass
class TickerInfo:
    symbol: str
    name: str
    sector: str
    logo_bg: str  # background tint for icon
    logo_fg: str  # stroke color


@dataclass
class Quote:
    symbol: str
    price: float           # last / reference price in TRY
    prev_close: float
    change_pct: float
    currency: str = "TRY"
    source: str = "demo"   # NEVER call it "verified" or "real"
    as_of: str = ""        # ISO timestamp


class MarketDataProvider(ABC):
    @abstractmethod
    def list_tickers(self) -> List[TickerInfo]: ...

    @abstractmethod
    def get_ticker(self, symbol: str) -> TickerInfo | None: ...

    @abstractmethod
    def get_quote(self, symbol: str) -> Quote | None: ...

    @abstractmethod
    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]: ...


# --- Demo provider ----------------------------------------------------------

# A small curated BIST universe covering everyday-known Turkish equities.
_DEMO_TICKERS: Dict[str, TickerInfo] = {
    "THYAO": TickerInfo("THYAO", "Türk Hava Yolları", "Ulaştırma", "#E1F4F1", "#35C7B2"),
    "TUPRS": TickerInfo("TUPRS", "Tüpraş", "Enerji", "#FFE4D6", "#FF7733"),
    "ASELS": TickerInfo("ASELS", "Aselsan", "Savunma", "#E6E2FD", "#7361F7"),
    "BIMAS": TickerInfo("BIMAS", "BİM Mağazalar", "Perakende", "#FFF8DF", "#D6B130"),
    "GARAN": TickerInfo("GARAN", "Garanti BBVA", "Bankacılık", "#E1F4F1", "#35C7B2"),
    "AKBNK": TickerInfo("AKBNK", "Akbank", "Bankacılık", "#E6E2FD", "#7361F7"),
    "KCHOL": TickerInfo("KCHOL", "Koç Holding", "Holding", "#FFE4D6", "#FF7733"),
    "SAHOL": TickerInfo("SAHOL", "Sabancı Holding", "Holding", "#FFF8DF", "#D6B130"),
    "EREGL": TickerInfo("EREGL", "Ereğli Demir Çelik", "Sanayi", "#E1F4F1", "#35C7B2"),
    "SISE":  TickerInfo("SISE",  "Şişecam", "Sanayi", "#E6E2FD", "#7361F7"),
    "FROTO": TickerInfo("FROTO", "Ford Otosan", "Otomotiv", "#FFE4D6", "#FF7733"),
    "TOASO": TickerInfo("TOASO", "Tofaş", "Otomotiv", "#FFF8DF", "#D6B130"),
}

# Deterministic reference prices (TRY). These are demo values, NOT real market
# quotes. They stay constant across restarts so the golden demo remains stable.
_DEMO_PRICES: Dict[str, tuple[float, float]] = {
    # symbol: (price, prev_close)
    "THYAO": (312.50, 305.00),
    "TUPRS": (168.90, 170.20),
    "ASELS": (94.35, 92.10),
    "BIMAS": (521.00, 518.75),
    "GARAN": (128.40, 126.10),
    "AKBNK": (72.85, 73.50),
    "KCHOL": (232.00, 228.90),
    "SAHOL": (105.70, 103.20),
    "EREGL": (54.20, 54.90),
    "SISE":  (48.15, 47.60),
    "FROTO": (985.00, 977.50),
    "TOASO": (287.40, 282.10),
}


class DemoMarketDataProvider(MarketDataProvider):
    """Deterministic demo provider — clearly labelled, safe for judges."""

    def list_tickers(self) -> List[TickerInfo]:
        return list(_DEMO_TICKERS.values())

    def get_ticker(self, symbol: str) -> TickerInfo | None:
        return _DEMO_TICKERS.get(symbol.upper())

    def get_quote(self, symbol: str) -> Quote | None:
        s = symbol.upper()
        if s not in _DEMO_PRICES:
            return None
        price, prev = _DEMO_PRICES[s]
        chg = 0.0 if prev == 0 else (price - prev) / prev * 100
        return Quote(
            symbol=s,
            price=price,
            prev_close=prev,
            change_pct=round(chg, 2),
            as_of=datetime.now(timezone.utc).isoformat(),
        )

    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        return {s: q for s in symbols if (q := self.get_quote(s)) is not None}


_provider: MarketDataProvider | None = None


def get_market_data_provider() -> MarketDataProvider:
    global _provider
    if _provider is None:
        _provider = DemoMarketDataProvider()
    return _provider
