"""Market data provider abstraction.

Two providers ship out of the box:
  - DemoMarketDataProvider: deterministic, safe for judges
  - YahooBistProvider     : live BIST quotes from Yahoo Finance (public data)
                            with in-memory TTL cache and demo fallback

Which one is used is decided at startup based on env `MARKET_DATA_PROVIDER`:
  "yahoo" (default) → YahooBistProvider (falls back to demo on failure)
  "demo"            → DemoMarketDataProvider
"""
from __future__ import annotations

import os
import time
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional


log = logging.getLogger("divimero.market")


@dataclass
class TickerInfo:
    symbol: str
    name: str
    sector: str
    logo_bg: str
    logo_fg: str


@dataclass
class Quote:
    symbol: str
    price: float
    prev_close: float
    change_pct: float
    currency: str = "TRY"
    source: str = "demo"
    as_of: str = ""


class MarketDataProvider(ABC):
    name: str = "demo"

    @abstractmethod
    def list_tickers(self) -> List[TickerInfo]: ...

    @abstractmethod
    def get_ticker(self, symbol: str) -> Optional[TickerInfo]: ...

    @abstractmethod
    def get_quote(self, symbol: str) -> Optional[Quote]: ...

    @abstractmethod
    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]: ...


# --- Shared BIST universe ---------------------------------------------------
_UNIVERSE: Dict[str, TickerInfo] = {
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

_DEMO_PRICES: Dict[str, tuple[float, float]] = {
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
    name = "demo"

    def list_tickers(self) -> List[TickerInfo]:
        return list(_UNIVERSE.values())

    def get_ticker(self, symbol: str) -> Optional[TickerInfo]:
        return _UNIVERSE.get(symbol.upper())

    def get_quote(self, symbol: str) -> Optional[Quote]:
        s = symbol.upper()
        if s not in _DEMO_PRICES:
            return None
        price, prev = _DEMO_PRICES[s]
        chg = 0.0 if prev == 0 else (price - prev) / prev * 100
        return Quote(symbol=s, price=price, prev_close=prev, change_pct=round(chg, 2),
                     source="demo", as_of=datetime.now(timezone.utc).isoformat())

    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        return {s: q for s in symbols if (q := self.get_quote(s)) is not None}


class YahooBistProvider(MarketDataProvider):
    """Yahoo Finance BIST provider — appends `.IS` to symbols (public data)."""
    name = "yahoo"
    TTL_SECONDS = 5 * 60      # 5-minute cache
    FAILURE_COOLDOWN = 60     # if yahoo fails, don't retry for 60s per symbol

    def __init__(self):
        self._cache: Dict[str, tuple[float, Quote]] = {}
        self._failures: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._demo = DemoMarketDataProvider()

    def list_tickers(self) -> List[TickerInfo]:
        return list(_UNIVERSE.values())

    def get_ticker(self, symbol: str) -> Optional[TickerInfo]:
        return _UNIVERSE.get(symbol.upper())

    def _fetch_from_yahoo(self, symbol: str) -> Optional[Quote]:
        """Use Yahoo Finance's public v8 chart endpoint (no auth required)."""
        try:
            import requests
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.IS?interval=1d&range=5d"
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 Divimero/1.0"}, timeout=8)
            if r.status_code != 200:
                return None
            data = r.json()
            res = (data.get("chart", {}).get("result") or [None])[0]
            if not res:
                return None
            meta = res.get("meta", {})
            price = float(meta.get("regularMarketPrice") or 0)
            prev = float(meta.get("previousClose") or meta.get("chartPreviousClose") or 0)
            if not price:
                return None
            chg = 0.0 if not prev else (price - prev) / prev * 100
            return Quote(
                symbol=symbol, price=round(price, 2), prev_close=round(prev, 2),
                change_pct=round(chg, 2), currency=meta.get("currency", "TRY"),
                source="yahoo", as_of=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            log.warning("Yahoo fetch failed for %s: %s", symbol, e)
            return None

    def get_quote(self, symbol: str) -> Optional[Quote]:
        s = symbol.upper()
        if s not in _UNIVERSE:
            return None
        now = time.time()
        with self._lock:
            hit = self._cache.get(s)
            if hit and now - hit[0] < self.TTL_SECONDS:
                return hit[1]
            recent_fail = self._failures.get(s, 0)
        if now - recent_fail < self.FAILURE_COOLDOWN:
            # Within cooldown — return whatever's cached (even stale) or demo fallback
            with self._lock:
                if hit: return hit[1]
            return self._demo.get_quote(s)

        q = self._fetch_from_yahoo(s)
        with self._lock:
            if q is not None:
                self._cache[s] = (now, q)
                self._failures.pop(s, None)
                return q
            self._failures[s] = now
        return (hit[1] if hit else self._demo.get_quote(s))

    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        return {s: q for s in symbols if (q := self.get_quote(s)) is not None}


_provider: Optional[MarketDataProvider] = None


def get_market_data_provider() -> MarketDataProvider:
    global _provider
    if _provider is None:
        which = (os.environ.get("MARKET_DATA_PROVIDER") or "yahoo").lower()
        _provider = YahooBistProvider() if which == "yahoo" else DemoMarketDataProvider()
        log.info("Market data provider: %s", _provider.name)
    return _provider
