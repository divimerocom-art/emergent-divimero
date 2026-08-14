"""Market data provider abstraction + BIST instrument catalog.

Catalog source: Borsa İstanbul official CSV `hisse_endeks_ds.csv` (587 unique symbols
as of 2026-08). Loaded from /app/backend/bist_catalog.json at import time.

Two live providers:
  - DemoMarketDataProvider   : deterministic reference prices for a subset
  - YahooBistProvider        : Yahoo Finance v8 chart endpoint (public data)
                                per-symbol TTL cache + failure cooldown + demo fallback
"""
from __future__ import annotations

import json
import os
import time
import logging
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


log = logging.getLogger("divimero.market")


@dataclass
class TickerInfo:
    symbol: str
    name: str
    sector: str
    logo_bg: str
    logo_fg: str
    index: str = ""   # primary BIST index membership (e.g. XU100)


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

    @abstractmethod
    def search(self, query: str, limit: int = 25) -> List[TickerInfo]: ...


# --- Symbol normalisation ---------------------------------------------------

_TR_MAP = str.maketrans({
    'İ': 'I', 'ı': 'i', 'Ş': 'S', 'ş': 's',
    'Ğ': 'G', 'ğ': 'g', 'Ü': 'U', 'ü': 'u',
    'Ö': 'O', 'ö': 'o', 'Ç': 'C', 'ç': 'c',
})


def normalise_text(s: str) -> str:
    """Turkish-aware, diacritic-stripped, lowercase, whitespace-collapsed."""
    if not s:
        return ""
    s = s.translate(_TR_MAP)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return " ".join(s.lower().split())


def clean_symbol(raw: str) -> str:
    """Accept THYAO, THYAO.IS, BIST:THYAO, BIST:THYAO.IS, ' thyao ', etc. → THYAO"""
    if not raw:
        return ""
    s = raw.strip().upper()
    # strip common exchange prefixes
    for p in ("BIST:", "IST:", "XIST:", "BORSA:", "BIST-"):
        if s.startswith(p):
            s = s[len(p):]
            break
    # strip common Yahoo/BIST suffixes
    for suf in (".IS", ".E", ".BIST", ".IST"):
        if s.endswith(suf):
            s = s[:-len(suf)]
            break
    return s.strip()


# --- Palette / icon colours -------------------------------------------------

_PALETTES = [
    ("#E1F4F1", "#35C7B2"),   # turquoise
    ("#E6E2FD", "#7361F7"),   # violet
    ("#FFE4D6", "#FF7733"),   # orange
    ("#FFF8DF", "#D6B130"),   # yellow
]


def _palette_for(sym: str) -> tuple[str, str]:
    return _PALETTES[sum(ord(c) for c in sym) % len(_PALETTES)]


# --- Sector inference from name (best-effort) -------------------------------

_SECTOR_HINTS = [
    ("BANK", "Bankacılık"),
    ("HOLD", "Holding"),
    ("GMYO", "Gayrimenkul"),
    ("GYO",  "Gayrimenkul"),
    ("ENERJ", "Enerji"),
    ("PETRO", "Enerji"),
    ("OTO", "Otomotiv"),
    ("MAG",   "Perakende"),
    ("TICARET","Perakende"),
    ("MARKET","Perakende"),
    ("GIDA",  "Gıda & İçecek"),
    ("SUT",   "Gıda & İçecek"),
    ("BIRA",  "Gıda & İçecek"),
    ("ICECEK","Gıda & İçecek"),
    ("CAM",   "Sanayi"),
    ("DEMIR", "Sanayi"),
    ("CELIK", "Sanayi"),
    ("CIMENTO","Sanayi"),
    ("INSAAT","İnşaat"),
    ("YAT",   "Yatırım"),
    ("SIGORTA","Sigorta"),
    ("TELEKOM","Telekom"),
    ("TEKNOL","Teknoloji"),
    ("YAZILIM","Teknoloji"),
    ("ILAC",  "Sağlık"),
    ("SAGLIK","Sağlık"),
    ("HAVA",  "Ulaştırma"),
    ("HAVAY", "Ulaştırma"),
    ("SAVUN", "Savunma"),
    ("KIMYA", "Kimya"),
    ("POLYE", "Kimya"),
    ("TARIM", "Tarım"),
    ("TEKSTIL","Tekstil"),
]


def _infer_sector(name_norm: str) -> str:
    for k, v in _SECTOR_HINTS:
        if k.lower() in name_norm:
            return v
    return "Diğer"


# --- Catalog loader ---------------------------------------------------------

_CATALOG_PATH = Path(__file__).parent / "bist_catalog.json"


def _load_catalog() -> Dict[str, TickerInfo]:
    """Load the BIST catalog and enrich with sector + palette."""
    try:
        with open(_CATALOG_PATH, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        log.error("BIST catalog not found at %s", _CATALOG_PATH)
        return {}

    universe: Dict[str, TickerInfo] = {}
    for row in raw:
        sym = str(row.get("symbol") or "").upper().strip()
        if not sym:
            continue
        name = row.get("name") or sym
        norm = row.get("norm") or normalise_text(name)
        sector = _infer_sector(norm)
        bg, fg = _palette_for(sym)
        universe[sym] = TickerInfo(
            symbol=sym, name=name, sector=sector,
            logo_bg=bg, logo_fg=fg, index=row.get("index") or "",
        )
    # Small alias table for very common human names → symbol
    _ALIASES.update({
        normalise_text("Türk Hava Yolları"): "THYAO",
        normalise_text("THY"):                "THYAO",
        normalise_text("Tüpraş"):            "TUPRS",
        normalise_text("Aselsan"):           "ASELS",
        normalise_text("BİM"):               "BIMAS",
        normalise_text("Koç Holding"):       "KCHOL",
        normalise_text("Sabancı Holding"):   "SAHOL",
        normalise_text("Şişecam"):           "SISE",
        normalise_text("Turkcell"):          "TCELL",
        normalise_text("Türk Telekom"):      "TTKOM",
        normalise_text("Ereğli"):            "EREGL",
        normalise_text("Ereğli Demir Çelik"):"EREGL",
        normalise_text("Yapı Kredi"):        "YKBNK",
        normalise_text("İş Bankası"):        "ISCTR",
        normalise_text("Akbank"):            "AKBNK",
        normalise_text("Garanti"):           "GARAN",
        normalise_text("Garanti BBVA"):      "GARAN",
        normalise_text("Halkbank"):          "HALKB",
        normalise_text("Vakıfbank"):         "VAKBN",
        normalise_text("Ford Otosan"):       "FROTO",
        normalise_text("Tofaş"):             "TOASO",
        normalise_text("Migros"):            "MGROS",
        normalise_text("Anadolu Efes"):      "AEFES",
        normalise_text("Ülker"):             "ULKER",
        normalise_text("Petkim"):            "PETKM",
        normalise_text("Astor"):             "ASTOR",
        normalise_text("Astor Enerji"):      "ASTOR",
        normalise_text("Arçelik"):           "ARCLK",
    })
    return universe


_ALIASES: Dict[str, str] = {}
_UNIVERSE: Dict[str, TickerInfo] = _load_catalog()
log.info("BIST catalog loaded: %d symbols", len(_UNIVERSE))


# --- Deterministic demo reference prices ------------------------------------

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
    "AEFES": (192.40, 190.10), "HALKB": (24.62, 24.30),   "VAKBN": (28.94, 28.70),
    "OTKAR": (325.75, 320.10), "TAVHL": (315.20, 310.80),
}


# --- Search -----------------------------------------------------------------

def _match_score(t: TickerInfo, needle_raw: str, needle_norm: str) -> int:
    """Higher score = better match. Returns 0 if no match."""
    sym = t.symbol
    name_norm = normalise_text(t.name)
    # Exact symbol / alias
    if sym == needle_raw:
        return 1000
    if _ALIASES.get(needle_norm) == sym:
        return 950
    # Symbol prefix / substring
    if sym.startswith(needle_raw):
        return 800
    if needle_raw and needle_raw in sym:
        return 600
    # Name prefix / substring
    if name_norm.startswith(needle_norm):
        return 500
    if needle_norm and needle_norm in name_norm:
        return 300
    # Token match
    tokens = name_norm.split()
    if needle_norm in tokens:
        return 350
    if any(tok.startswith(needle_norm) for tok in tokens):
        return 250
    return 0


def search_catalog(query: str, limit: int = 25) -> List[TickerInfo]:
    q = clean_symbol(query) if query else ""     # THYAO.IS → THYAO
    needle_norm = normalise_text(query)          # 'Türk Hava' → 'turk hava'
    if not q and not needle_norm:
        return list(_UNIVERSE.values())[:limit]
    scored: List[tuple[int, TickerInfo]] = []
    for t in _UNIVERSE.values():
        s = _match_score(t, q, needle_norm)
        if s > 0:
            scored.append((s, t))
    scored.sort(key=lambda x: (-x[0], x[1].symbol))
    return [t for _, t in scored[:limit]]


# --- Providers --------------------------------------------------------------

class DemoMarketDataProvider(MarketDataProvider):
    name = "demo"

    def list_tickers(self) -> List[TickerInfo]:
        return list(_UNIVERSE.values())

    def get_ticker(self, symbol: str) -> Optional[TickerInfo]:
        return _UNIVERSE.get(clean_symbol(symbol))

    def _reference_quote(self, sym: str) -> Optional[Quote]:
        if sym not in _DEMO_PRICES:
            return None
        price, prev = _DEMO_PRICES[sym]
        chg = 0.0 if prev == 0 else (price - prev) / prev * 100
        return Quote(symbol=sym, price=price, prev_close=prev, change_pct=round(chg, 2),
                     source="demo", as_of=datetime.now(timezone.utc).isoformat())

    def get_quote(self, symbol: str) -> Optional[Quote]:
        sym = clean_symbol(symbol)
        if sym not in _UNIVERSE:
            return None
        return self._reference_quote(sym)

    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        out = {}
        for s in symbols:
            q = self.get_quote(s)
            if q is not None:
                out[clean_symbol(s)] = q
        return out

    def search(self, query: str, limit: int = 25) -> List[TickerInfo]:
        return search_catalog(query, limit)


class YahooBistProvider(MarketDataProvider):
    """Live BIST via Yahoo Finance v8 chart endpoint. No auth required."""
    name = "yahoo"
    TTL_SECONDS = 5 * 60
    FAILURE_COOLDOWN = 60

    def __init__(self):
        self._cache: Dict[str, tuple[float, Quote]] = {}
        self._failures: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._demo = DemoMarketDataProvider()

    def list_tickers(self) -> List[TickerInfo]:
        return list(_UNIVERSE.values())

    def get_ticker(self, symbol: str) -> Optional[TickerInfo]:
        return _UNIVERSE.get(clean_symbol(symbol))

    def _fetch_from_yahoo(self, symbol: str) -> Optional[Quote]:
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
        sym = clean_symbol(symbol)
        if sym not in _UNIVERSE:
            return None
        # Single-symbol path is just a batch of one — reuse the parallel batch
        # so cache/failure logic never diverges between the two entry points.
        got = self.get_quotes([sym])
        return got.get(sym)

    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Parallel Yahoo fetch across symbols with cache + failure cooldown."""
        cleaned = list({clean_symbol(s) for s in symbols if clean_symbol(s) in _UNIVERSE})
        if not cleaned:
            return {}
        now = time.time()
        result: Dict[str, Quote] = {}
        to_fetch: List[str] = []
        with self._lock:
            for s in cleaned:
                hit = self._cache.get(s)
                if hit and now - hit[0] < self.TTL_SECONDS:
                    result[s] = hit[1]
                elif now - self._failures.get(s, 0) < self.FAILURE_COOLDOWN:
                    if hit:
                        result[s] = hit[1]
                    else:
                        d = self._demo.get_quote(s)
                        if d is not None:
                            result[s] = d
                else:
                    to_fetch.append(s)
        if to_fetch:
            with ThreadPoolExecutor(max_workers=min(8, len(to_fetch))) as ex:
                fetched = list(ex.map(self._fetch_from_yahoo, to_fetch))
            with self._lock:
                for sym, q in zip(to_fetch, fetched):
                    if q is not None:
                        self._cache[sym] = (now, q)
                        self._failures.pop(sym, None)
                        result[sym] = q
                    else:
                        self._failures[sym] = now
                        stale = self._cache.get(sym)
                        if stale:
                            result[sym] = stale[1]
                        else:
                            d = self._demo.get_quote(sym)
                            if d is not None:
                                result[sym] = d
        return result

    def search(self, query: str, limit: int = 25) -> List[TickerInfo]:
        return search_catalog(query, limit)


_provider: Optional[MarketDataProvider] = None


def get_market_data_provider() -> MarketDataProvider:
    global _provider
    if _provider is None:
        which = (os.environ.get("MARKET_DATA_PROVIDER") or "yahoo").lower()
        _provider = YahooBistProvider() if which == "yahoo" else DemoMarketDataProvider()
        log.info("Market data provider: %s", _provider.name)
    return _provider
