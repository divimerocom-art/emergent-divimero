import { useEffect, useState } from "react";
import { api, money, pct } from "@/lib/api";
import { Link } from "react-router-dom";
import { ArrowUpRight, ArrowDownRight, Plus, Info } from "lucide-react";
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

export default function Portfolio() {
  const [p, setP] = useState(null);
  const [series, setSeries] = useState([]);
  const [txs, setTxs] = useState([]);

  const load = async () => {
    try {
      const [{ data: port }, { data: perf }, { data: t }] = await Promise.all([
        api.get("/portfolio"), api.get("/portfolio/performance"), api.get("/portfolio/transactions")
      ]);
      setP(port); setSeries(perf.series || []); setTxs(t || []);
    } catch { setP({ total_value: 0, holdings: [], cash: 0 }); }
  };
  useEffect(() => { load(); }, []);

  if (!p) return <div className="text-mute">Yükleniyor…</div>;

  const gainPos = (p.total_gain_loss || 0) >= 0;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl md:text-3xl font-bold tracking-tight">Portföy</h1>
          <p className="text-sm text-mute inline-flex items-center gap-1.5"><Info size={14}/> Piyasa verisi: <span className="font-medium">{p.source === "yahoo" ? "Yahoo Finance (canlı BIST)" : "Demo — sabit fiyatlar"}</span></p>
        </div>
        <Link to="/portfolio/new" className="inline-flex items-center gap-1.5 h-10 px-4 rounded-full bg-ink hover:bg-black text-white text-sm font-medium" data-testid="cta-new-tx">
          <Plus size={16}/> Yeni işlem
        </Link>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPI title="Toplam Değer" value={money(p.total_value)} testId="kpi-total"/>
        <KPI title="Nakit" value={money(p.cash)} testId="kpi-cash"/>
        <KPI title="Net Yatırım" value={money(p.net_deposited)} testId="kpi-deposited"/>
        <KPI title="Toplam K/Z" testId="kpi-pl"
          value={<span className={`tabular ${gainPos ? "text-pos" : "text-neg"}`}>{gainPos ? "+" : ""}{money(p.total_gain_loss)}</span>}
          sub={<span className={`inline-flex items-center gap-1 text-xs font-semibold ${gainPos ? "text-pos" : "text-neg"}`}>{gainPos ? <ArrowUpRight size={12}/> : <ArrowDownRight size={12}/>} {pct(p.total_gain_loss_pct)}</span>}
        />
      </div>

      {/* Return metrics row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <KPI title="Gerçekleşen K/Z" value={<span className={`tabular ${(p.total_realized_pl||0)>=0?"text-pos":"text-neg"}`}>{money(p.total_realized_pl)}</span>} testId="kpi-realized"/>
        <KPI title="Toplam Temettü" testId="kpi-dividends"
          value={<span className="tabular text-violet">{money(p.total_dividends)}</span>}
          sub={<span className="text-xs text-mute">Kaydettiğiniz temettü işlemlerinden</span>}
        />
        <KPI title="XIRR (yıllıklandırılmış)" testId="kpi-xirr"
          value={p.xirr == null
            ? <span className="text-mute text-base">Yeterli veri yok</span>
            : <span className={`tabular ${p.xirr>=0?"text-pos":"text-neg"}`}>{pct(p.xirr*100)}</span>}
          sub={<span className="text-xs text-mute">Para ağırlıklı getiri · nakit akışlarına dayalı</span>}
        />
      </div>

      {/* Chart */}
      <div className="rounded-2xl border border-line bg-white p-4 md:p-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-heading font-semibold">Portföy Değeri</h2>
          <span className="text-xs text-mute">Kümülatif işlem sonrası anlık değer</span>
        </div>
        <div className="h-56">
          {series.length === 0 ? (
            <div className="h-full flex items-center justify-center text-sm text-mute">Yeterli veri yok. Bir işlem ekleyin.</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
                <CartesianGrid stroke="#E3E3E3" strokeDasharray="3 3" vertical={false} />
                {/* Same value as the `mute` token; these 11px tick labels sat at 4.51:1 on white. */}
                <XAxis dataKey="date" stroke="#5F656D" fontSize={11}/>
                <YAxis stroke="#5F656D" fontSize={11} tickFormatter={(v)=> new Intl.NumberFormat('tr-TR',{notation:'compact'}).format(v)} width={55}/>
                <Tooltip formatter={(v)=>money(v)} contentStyle={{ borderRadius: 12, border: '1px solid #E3E3E3' }}/>
                <Line type="monotone" dataKey="value" stroke="#35C7B2" strokeWidth={2.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Holdings */}
      <div className="rounded-2xl border border-line bg-white overflow-hidden">
        <div className="flex items-center justify-between p-4 md:p-5 border-b border-line">
          <h2 className="font-heading font-semibold">Pozisyonlar</h2>
          <span className="text-xs text-mute">{p.holdings.length} hisse</span>
        </div>
        {p.holdings.length === 0 ? (
          <div className="p-10 text-center text-sm text-mute">Henüz pozisyon yok. İlk alışınızı ekleyin.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs uppercase tracking-wider text-mute">
                <tr className="text-left">
                  {/* Ort. Maliyet / Fiyat / Değer are hidden below sm so that Ağırlık and K/Z —
                      the two columns the product is about — stay on screen at 375px instead of
                      sitting behind an undiscoverable horizontal scroll. Desktop is unchanged. */}
                  <th className="px-2 sm:px-4 py-3">Hisse</th>
                  <th className="px-2 sm:px-4 py-3 text-right">Adet</th>
                  <th className="hidden sm:table-cell px-2 sm:px-4 py-3 text-right">Ort. Maliyet</th>
                  <th className="hidden sm:table-cell px-2 sm:px-4 py-3 text-right">Fiyat</th>
                  <th className="hidden sm:table-cell px-2 sm:px-4 py-3 text-right">Değer</th>
                  <th className="px-2 sm:px-4 py-3 text-right">Ağırlık</th>
                  <th className="px-2 sm:px-4 py-3 text-right">K/Z</th>
                </tr>
              </thead>
              <tbody>
                {p.holdings.map((h) => {
                  const up = h.unrealized_pl >= 0;
                  return (
                    <tr key={h.ticker} className="border-t border-line" data-testid={`hold-${h.ticker}`}>
                      <td className="px-2 sm:px-4 py-3 font-heading font-semibold">{h.ticker}</td>
                      <td className="px-2 sm:px-4 py-3 text-right tabular">{h.quantity.toLocaleString('tr-TR')}</td>
                      <td className="hidden sm:table-cell px-2 sm:px-4 py-3 text-right tabular text-mute">{money(h.avg_cost)}</td>
                      <td className="hidden sm:table-cell px-2 sm:px-4 py-3 text-right tabular">{money(h.market_price)}</td>
                      <td className="hidden sm:table-cell px-2 sm:px-4 py-3 text-right tabular font-medium">{money(h.market_value)}</td>
                      <td className="px-2 sm:px-4 py-3 text-right tabular">{pct(h.allocation_pct)}</td>
                      <td className={`px-2 sm:px-4 py-3 text-right tabular font-semibold ${up ? "text-pos" : "text-neg"}`}>
                        {up ? "+" : ""}{money(h.unrealized_pl)} <span className="block sm:inline text-xs opacity-80">({pct(h.unrealized_pl_pct)})</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Transactions */}
      <div className="rounded-2xl border border-line bg-white">
        <div className="p-4 md:p-5 border-b border-line flex items-center justify-between">
          <div className="font-heading font-semibold">Temettü Geçmişi</div>
          <span className="text-xs text-mute">Kullanıcı tarafından girilen temettü işlemleri</span>
        </div>
        {(() => {
          const divs = txs.filter(t => t.type === "dividend");
          if (divs.length === 0) return <div className="p-8 text-center text-sm text-mute" data-testid="divs-empty">Henüz temettü kaydı yok. Yeni işlem → "Temettü" ile ekleyebilirsiniz.</div>;
          const totals = {};
          divs.forEach(d => { const k = d.ticker || "—"; totals[k] = (totals[k] || 0) + Number(d.amount || 0); });
          return (
            <div>
              <div className="flex flex-wrap gap-2 p-4 md:p-5 border-b border-line" data-testid="divs-by-ticker">
                {Object.entries(totals).sort((a,b)=>b[1]-a[1]).map(([sym, sum]) => (
                  <span key={sym} className="inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded-full bg-violet-soft text-violet font-heading font-semibold">
                    {sym} <span className="tabular text-ink font-bold">{money(sum)}</span>
                  </span>
                ))}
              </div>
              <ul className="divide-y divide-line">
                {[...divs].reverse().map(d => (
                  <li key={d.id} className="px-4 py-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm" data-testid={`div-${d.id}`}>
                    <span className="order-1 text-xs font-semibold uppercase tracking-wider text-violet min-w-[70px]">Temettü</span>
                    <span className="order-2 font-heading font-semibold w-16">{d.ticker || "—"}</span>
                    <span className="order-4 sm:order-3 basis-full sm:basis-auto sm:flex-1 min-w-0 text-mute truncate">{d.note || <span className="italic">not yok</span>}</span>
                    <span className="order-5 sm:order-4 tabular text-mute">{new Date(d.date).toLocaleDateString('tr-TR')}</span>
                    <span className="order-3 sm:order-5 ml-auto sm:ml-0 tabular font-medium text-violet">{money(d.amount)}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })()}
      </div>

      {/* Transactions */}
      <div className="rounded-2xl border border-line bg-white">
        <div className="p-4 md:p-5 border-b border-line font-heading font-semibold">İşlem Geçmişi</div>
        {txs.length === 0 ? (
          <div className="p-10 text-center text-sm text-mute">Henüz işlem yok.</div>
        ) : (
          <ul className="divide-y divide-line">
            {[...txs].reverse().map((t) => {
              const label = { buy:"Alım", sell:"Satım", deposit:"Nakit Yatırma", withdraw:"Nakit Çekme", dividend:"Temettü" }[t.type] || t.type;
              const color = { buy:"text-brand", sell:"text-orange", deposit:"text-mute", withdraw:"text-mute", dividend:"text-violet" }[t.type];
              return (
                // Five items cannot share one 375px line. Below sm the row wraps to two lines —
                // tür/hisse/tutar first, adet × fiyat and the date second — via order-* overrides
                // that all reset at sm, so the desktop row is unchanged.
                <li key={t.id} className="px-4 py-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                  <span className={`order-1 text-xs font-semibold uppercase tracking-wider ${color} min-w-[80px]`}>{label}</span>
                  <span className="order-2 font-heading font-semibold w-16">{t.ticker || "—"}</span>
                  <span className="order-4 sm:order-3 basis-full sm:basis-auto sm:flex-1 tabular text-mute">{t.quantity ? `${t.quantity} adet` : ""} {t.price ? `× ${money(t.price)}` : ""}</span>
                  <span className="order-5 sm:order-4 tabular text-mute">{new Date(t.date).toLocaleDateString('tr-TR')}</span>
                  <span className="order-3 sm:order-5 ml-auto sm:ml-0 tabular font-medium">{t.amount ? money(t.amount) : (t.quantity && t.price ? money(t.quantity * t.price) : "")}</span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

function KPI({ title, value, sub, testId }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-4" data-testid={testId}>
      <div className="text-xs uppercase tracking-wider text-mute font-medium">{title}</div>
      <div className="mt-1 font-heading text-2xl font-bold tabular">{value}</div>
      {sub && <div className="mt-1">{sub}</div>}
    </div>
  );
}
