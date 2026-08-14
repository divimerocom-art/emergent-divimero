import { useEffect, useMemo, useRef, useState } from "react";
import { Search, X, Check, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { Input } from "@/components/ui/input";
import { api, num } from "@/lib/api";

/**
 * Instrument (BIST ticker) search combobox.
 * Props:
 *  - value:           currently selected symbol string
 *  - onChange(symbol) called on selection
 *  - restrictTo:      optional array of allowed symbols (used for disclosure_ticker)
 *  - placeholder:     search input placeholder
 *  - testIdPrefix:    prefix for data-testid attributes on rows
 */
export default function InstrumentPicker({ value, onChange, restrictTo, placeholder, testIdPrefix = "inst" }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const ref = useRef(null);

  // Fetch initial list + resolve name of selected symbol.
  // Debounce query so we don't hammer the backend on every keystroke.
  useEffect(() => {
    let alive = true;
    const handle = setTimeout(() => {
      setLoading(true);
      const url = q
        ? `/market/search?q=${encodeURIComponent(q)}&with_price=true&limit=25`
        : `/market/tickers?limit=25&with_price=false`;
      api.get(url)
        .then((r) => { if (alive) setItems(r.data); })
        .finally(() => { if (alive) setLoading(false); });
    }, q ? 180 : 0);
    return () => { alive = false; clearTimeout(handle); };
  }, [q]);

  useEffect(() => {
    if (!value) { setSelected(null); return; }
    if (selected?.symbol === value) return;
    api.get(`/market/search?q=${encodeURIComponent(value)}&limit=5&with_price=false`).then((r) => {
      const hit = (r.data || []).find((t) => t.symbol === value);
      setSelected(hit || { symbol: value, name: value });
    }).catch(()=>setSelected({ symbol: value, name: value }));
  }, [value]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const filtered = useMemo(() => {
    if (!restrictTo) return items;
    const s = new Set(restrictTo);
    return items.filter((t) => s.has(t.symbol));
  }, [items, restrictTo]);

  const pick = (t) => { onChange(t.symbol); setSelected(t); setOpen(false); setQ(""); };
  const clear = () => { onChange(""); setSelected(null); setQ(""); setOpen(true); };

  return (
    <div className="relative" ref={ref}>
      {selected ? (
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="w-full flex items-center justify-between h-10 px-3 rounded-full border border-line bg-white hover:bg-surface text-left transition-colors"
          data-testid={`${testIdPrefix}-selected`}
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="h-6 w-6 rounded-lg text-[10px] flex items-center justify-center font-heading font-bold" style={{ background: selected.logo_bg || "#F1F5F7", color: selected.logo_fg || "#171717" }}>
              {selected.symbol.slice(0, 2)}
            </span>
            <span className="font-heading font-semibold truncate">{selected.symbol}</span>
            {selected.name && selected.name !== selected.symbol && <span className="text-xs text-mute truncate hidden sm:inline">— {selected.name}</span>}
          </div>
          <span onClick={(e)=>{e.stopPropagation(); clear();}} className="h-6 w-6 rounded-full hover:bg-line flex items-center justify-center" data-testid={`${testIdPrefix}-clear`}>
            <X size={14} className="text-mute"/>
          </span>
        </button>
      ) : (
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-mute pointer-events-none"/>
          <Input
            autoComplete="off"
            value={q}
            onFocus={() => setOpen(true)}
            onChange={(e)=>{ setQ(e.target.value); setOpen(true); }}
            placeholder={placeholder || "Hisse ara: sembol veya şirket adı…"}
            className="pl-9 rounded-full"
            data-testid={`${testIdPrefix}-input`}
          />
        </div>
      )}

      {open && (
        <div className="absolute z-50 mt-2 w-full max-h-72 overflow-auto bg-white border border-line rounded-2xl shadow-sm" data-testid={`${testIdPrefix}-dropdown`}>
          {selected && (
            <div className="p-2 border-b border-line">
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-mute pointer-events-none"/>
                <Input autoFocus autoComplete="off" value={q} onChange={(e)=>setQ(e.target.value)} placeholder="Ara…" className="pl-8 h-8 rounded-full text-sm" data-testid={`${testIdPrefix}-search`}/>
              </div>
            </div>
          )}
          {loading && <div className="p-4 text-xs text-mute">Aranıyor…</div>}
          {!loading && filtered.length === 0 && (
            <div className="p-4 text-xs text-mute">
              {restrictTo ? "Portföyünüzde eşleşen hisse yok." : `"${q}" için sonuç bulunamadı.`}
            </div>
          )}
          {!loading && filtered.slice(0, 30).map((t) => {
            const up = (t.change_pct ?? 0) >= 0;
            const hasPrice = t.price_available;
            return (
              <button
                key={t.symbol}
                type="button"
                onClick={() => pick(t)}
                className={`w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-surface transition-colors ${value === t.symbol ? "bg-brand-soft/60" : ""}`}
                data-testid={`${testIdPrefix}-row-${t.symbol}`}
              >
                <span className="h-8 w-8 rounded-lg text-[11px] flex items-center justify-center font-heading font-bold shrink-0" style={{ background: t.logo_bg, color: t.logo_fg }}>
                  {t.symbol.slice(0, 2)}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-heading font-semibold text-sm">{t.symbol}</span>
                    {t.index && <span className="text-[9px] uppercase tracking-wider text-mute font-medium">{t.index}</span>}
                  </div>
                  <div className="text-xs text-mute truncate">{t.name}</div>
                </div>
                {hasPrice ? (
                  <div className="text-right shrink-0">
                    <div className="tabular text-xs font-medium">₺{num(t.price)}</div>
                    <div className={`tabular text-[11px] font-semibold inline-flex items-center gap-0.5 ${up ? "text-pos" : "text-neg"}`}>
                      {up ? <ArrowUpRight size={10}/> : <ArrowDownRight size={10}/>}
                      {up ? "+" : ""}{num(t.change_pct)}%
                    </div>
                  </div>
                ) : (
                  t.price_source === null && q ? (
                    <span className="text-[10px] text-mute shrink-0 italic max-w-[110px] text-right leading-tight">Piyasa verisi yok</span>
                  ) : null
                )}
                {value === t.symbol && <Check size={14} className="text-brand shrink-0 ml-2"/>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
