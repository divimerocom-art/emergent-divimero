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
# A broader BIST catalog so instrument search feels like a genuine market picker.
# Prices below are DETERMINISTIC DEMO/REFERENCE values (source: "demo"). The Yahoo
# provider layered on top of this returns live quotes for the same symbols.
def _t(sym, name, sector, palette=0):
    palettes = [
        ("#E1F4F1", "#35C7B2"),
        ("#E6E2FD", "#7361F7"),
        ("#FFE4D6", "#FF7733"),
        ("#FFF8DF", "#D6B130"),
    ]
    bg, fg = palettes[palette % len(palettes)]
    return TickerInfo(sym, name, sector, bg, fg)


_UNIVERSE: Dict[str, TickerInfo] = {t.symbol: t for t in [
    # Banks & Finance
    _t("GARAN", "Garanti BBVA", "Bankacılık", 0),
    _t("AKBNK", "Akbank", "Bankacılık", 1),
    _t("YKBNK", "Yapı ve Kredi Bankası", "Bankacılık", 0),
    _t("ISCTR", "Türkiye İş Bankası (C)", "Bankacılık", 1),
    _t("HALKB", "Halk Bankası", "Bankacılık", 2),
    _t("VAKBN", "VakıfBank", "Bankacılık", 3),
    _t("ALBRK", "Albaraka Türk", "Bankacılık", 1),
    _t("TSKB",  "Türkiye Sınai Kalkınma Bankası", "Bankacılık", 0),
    # Holdings
    _t("KCHOL", "Koç Holding", "Holding", 2),
    _t("SAHOL", "Sabancı Holding", "Holding", 3),
    _t("DOHOL", "Doğan Holding", "Holding", 1),
    _t("ENKAI", "Enka İnşaat", "Holding", 0),
    _t("AGHOL", "AG Anadolu Grubu Holding", "Holding", 3),
    _t("TAVHL", "TAV Havalimanları Holding", "Holding", 1),
    # Airlines / Transport
    _t("THYAO", "Türk Hava Yolları", "Ulaştırma", 0),
    _t("PGSUS", "Pegasus Hava Yolları", "Ulaştırma", 2),
    _t("CLEBI", "Çelebi Hava Servisi", "Ulaştırma", 1),
    # Energy & Refining
    _t("TUPRS", "Tüpraş", "Enerji", 2),
    _t("PETKM", "Petkim Petrokimya", "Enerji", 1),
    _t("AKSEN", "Aksa Enerji", "Enerji", 3),
    _t("ODAS",  "Odaş Elektrik", "Enerji", 0),
    _t("ZOREN", "Zorlu Enerji", "Enerji", 1),
    _t("ENJSA", "Enerjisa Enerji", "Enerji", 2),
    _t("AKSA",  "Aksa Akrilik", "Sanayi", 3),
    _t("EUPWR", "Europower Enerji", "Enerji", 0),
    # Defence / Aerospace / Electronics
    _t("ASELS", "Aselsan", "Savunma", 1),
    _t("OTKAR", "Otokar", "Savunma", 3),
    _t("KATMR", "Katmerciler", "Savunma", 2),
    _t("BAYRK", "Bayrak Elektrik", "Sanayi", 0),
    # Retail / Consumer
    _t("BIMAS", "BİM Mağazalar", "Perakende", 3),
    _t("MGROS", "Migros", "Perakende", 0),
    _t("SOKM",  "Şok Marketler", "Perakende", 2),
    _t("MAVI",  "Mavi Giyim", "Perakende", 1),
    _t("BIZIM", "Bizim Toptan", "Perakende", 3),
    _t("CCOLA", "Coca-Cola İçecek", "Gıda & İçecek", 0),
    _t("AEFES", "Anadolu Efes", "Gıda & İçecek", 2),
    _t("ULKER", "Ülker Bisküvi", "Gıda & İçecek", 1),
    _t("BANVT", "Banvit", "Gıda & İçecek", 3),
    _t("PNSUT", "Pınar Süt", "Gıda & İçecek", 0),
    _t("PENGD", "Penguen Gıda", "Gıda & İçecek", 2),
    # Industrials / Materials
    _t("EREGL", "Ereğli Demir Çelik", "Sanayi", 0),
    _t("KRDMD", "Kardemir (D)", "Sanayi", 2),
    _t("SISE",  "Şişecam", "Sanayi", 1),
    _t("TRKCM", "Trakya Cam", "Sanayi", 3),
    _t("ANACM", "Anadolu Cam", "Sanayi", 0),
    _t("SASA",  "Sasa Polyester", "Kimya", 2),
    _t("KORDS", "Kordsa", "Sanayi", 1),
    _t("HEKTS", "Hektaş", "Kimya", 3),
    _t("GUBRF", "Gübre Fabrikaları", "Kimya", 0),
    _t("BAGFS", "Bagfaş", "Kimya", 2),
    # Automotive
    _t("FROTO", "Ford Otosan", "Otomotiv", 2),
    _t("TOASO", "Tofaş Türk Otomobil", "Otomotiv", 3),
    _t("DOAS",  "Doğuş Otomotiv", "Otomotiv", 1),
    _t("PARSN", "Parsan", "Otomotiv", 0),
    # Real Estate & Construction
    _t("EKGYO", "Emlak Konut GYO", "Gayrimenkul", 1),
    _t("ISGYO", "İş GYO", "Gayrimenkul", 3),
    _t("TORNK", "Torunlar GYO", "Gayrimenkul", 0),
    # Telecom / Media / Tech
    _t("TCELL", "Turkcell", "Telekom", 1),
    _t("TTKOM", "Türk Telekom", "Telekom", 3),
    _t("LOGO",  "Logo Yazılım", "Teknoloji", 2),
    _t("NETAS", "Netaş Telekomünikasyon", "Teknoloji", 0),
    _t("KAREL", "Karel Elektronik", "Teknoloji", 1),
    # Renewables & Utilities
    _t("ASTOR", "ASTOR Enerji", "Enerji", 3),   # 🎯 The demo instrument search must find this
    _t("KONTR", "Kontrolmatik Teknoloji", "Enerji", 0),
    _t("SMRTG", "Smart Güneş Enerjisi", "Enerji", 2),
    _t("KARSN", "Karsan Otomotiv", "Otomotiv", 1),
    _t("ISDMR", "İskenderun Demir Çelik", "Sanayi", 3),
    # Others
    _t("ARCLK", "Arçelik", "Dayanıklı Tüketim", 0),
    _t("VESTL", "Vestel Elektronik", "Dayanıklı Tüketim", 2),
    _t("SELEC", "Selçuk Ecza Deposu", "Sağlık", 1),
    _t("DEVA",  "Deva Holding", "Sağlık", 3),
    _t("BAGFS", "Bagfaş", "Kimya", 2),
    _t("ALARK", "Alarko Holding", "Holding", 0),
]}

_DEMO_PRICES: Dict[str, tuple[float, float]] = {
    "THYAO": (312.50, 305.00), "TUPRS": (168.90, 170.20), "ASELS": (94.35, 92.10),
    "BIMAS": (521.00, 518.75), "GARAN": (128.40, 126.10), "AKBNK": (72.85, 73.50),
    "KCHOL": (232.00, 228.90), "SAHOL": (105.70, 103.20), "EREGL": (54.20, 54.90),
    "SISE":  (48.15, 47.60),   "FROTO": (985.00, 977.50), "TOASO": (287.40, 282.10),
    "ASTOR": (128.75, 125.40), "TCELL": (95.20, 94.10),   "TTKOM": (52.40, 51.90),
    "PGSUS": (270.10, 268.75), "PETKM": (18.42, 18.60),   "ISCTR": (14.62, 14.55),
    "YKBNK": (33.70, 33.20),   "SASA":  (3.61, 3.55),     "ARCLK": (172.30, 170.90),
    "MGROS": (485.75, 479.00), "AKSEN": (36.20, 36.55),   "ENKAI": (48.90, 48.30),
    "HEKTS": (12.44, 12.31),   "LOGO":  (108.30, 107.10), "KONTR": (94.80, 93.20),
    "SMRTG": (204.50, 199.80), "KRDMD": (22.15, 22.55),   "ULKER": (110.20, 108.40),
    "AEFES": (192.40, 190.10),
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
