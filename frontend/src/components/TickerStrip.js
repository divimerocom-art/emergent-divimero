import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, num } from "@/lib/api";
import { ArrowUpRight, ArrowDownRight } from "lucide-react";

export default function TickerStrip() {
  const [data, setData] = useState(null);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try { const { data } = await api.get("/market/movers?limit=6"); if (alive) setData(data); } catch {}
    };
    load();
    const t = setInterval(load, 60000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  if (!data) return null;
  const rows = [...(data.gainers || []), ...(data.losers || [])];
  // Deduplicate (small universe may overlap when gainers < 6)
  const seen = new Set();
  const uniq = rows.filter((r) => (seen.has(r.symbol) ? false : (seen.add(r.symbol), true)));
  if (uniq.length === 0) return null;

  return (
    <div className="rounded-2xl border border-line bg-white overflow-hidden" data-testid="ticker-strip">
      <div className="flex items-center gap-2 px-3 md:px-4 py-2 border-b border-line">
        <span className="h-2 w-2 rounded-full bg-pos animate-pulse"></span>
        <span className="text-[11px] uppercase tracking-wider text-mute font-semibold font-heading">Piyasa Nabzı</span>
        <span className="ml-auto text-[10px] text-mute">
          {data.source === "yahoo" ? "Canlı · Yahoo Finance" : "Demo veri"}
        </span>
      </div>
      <div className="overflow-x-auto no-scrollbar">
        <ul className="flex gap-1 py-1 px-1 min-w-max">
          {uniq.map((r) => {
            const up = r.change_pct >= 0;
            return (
              <li key={r.symbol}>
                <Link to={`/portfolio`} className="flex items-center gap-2 h-10 px-3 rounded-xl hover:bg-surface transition-colors" title={r.name} data-testid={`mover-${r.symbol}`}>
                  <span className="font-heading font-semibold text-sm">{r.symbol}</span>
                  <span className="tabular text-xs text-mute">₺{num(r.price)}</span>
                  <span className={`tabular text-xs font-semibold inline-flex items-center gap-0.5 ${up ? "text-pos" : "text-neg"}`}>
                    {up ? <ArrowUpRight size={12}/> : <ArrowDownRight size={12}/>}
                    {up ? "+" : ""}{num(r.change_pct)}%
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
