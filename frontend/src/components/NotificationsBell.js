import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Bell } from "lucide-react";
import { api, relTime } from "@/lib/api";

export default function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState({ unread: 0, items: [] });
  const ref = useRef(null);

  const load = async () => {
    try { const r = await api.get("/notifications"); setData(r.data); } catch {}
  };
  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => { clearInterval(t); document.removeEventListener("mousedown", h); };
  }, []);

  const toggle = async () => {
    setOpen(v => !v);
    if (!open && data.unread > 0) {
      try { await api.post("/notifications/read"); setData(d => ({ ...d, unread: 0 })); } catch {}
    }
  };

  return (
    <div className="relative" ref={ref}>
      <button onClick={toggle} className="relative p-2 rounded-full hover:bg-surface transition-colors" data-testid="notif-bell">
        <Bell size={18} className="text-mute" />
        {data.unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 h-4 min-w-[16px] px-1 rounded-full bg-neg text-white text-[10px] font-bold flex items-center justify-center tabular" data-testid="notif-badge">
            {data.unread > 9 ? "9+" : data.unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 md:w-96 bg-white border border-line rounded-2xl shadow-sm overflow-hidden z-50" data-testid="notif-panel">
          <div className="px-4 py-3 border-b border-line font-heading font-semibold">Bildirimler</div>
          {data.items.length === 0 ? (
            <div className="p-6 text-sm text-mute text-center">Henüz bildirim yok.</div>
          ) : (
            <ul className="max-h-96 overflow-auto divide-y divide-line">
              {data.items.map(n => (
                <li key={n.id}>
                  {n.kind === "alert" ? (
                    <div className="block px-4 py-3 hover:bg-surface transition-colors" data-testid={`notif-alert-${n.id}`}>
                      <div className="text-sm">
                        <span className="font-heading font-semibold">{n.actor?.display_name}</span>
                        <span className="text-mute"> pozisyonunu {n.change_kind}</span>
                        <span className="ml-1.5 text-[10px] font-heading font-semibold px-1.5 py-0.5 rounded-full bg-brand-soft text-brand align-middle">{n.ticker}</span>
                      </div>
                      <div className="text-xs text-mute mt-0.5 tabular">
                        {Number(n.before_pct||0).toLocaleString('tr-TR',{maximumFractionDigits:2})}% → {Number(n.after_pct||0).toLocaleString('tr-TR',{maximumFractionDigits:2})}%
                        <span className={`ml-2 font-semibold ${n.delta_pct>=0?"text-pos":"text-neg"}`}>{n.delta_pct>=0?"+":""}{Number(n.delta_pct||0).toLocaleString('tr-TR',{maximumFractionDigits:2})} puan</span>
                      </div>
                      <div className="text-[11px] text-mute mt-1">{relTime(n.created_at)}</div>
                    </div>
                  ) : (
                    <Link to={`/p/${n.post_id}`} onClick={()=>setOpen(false)} className="block px-4 py-3 hover:bg-surface transition-colors">
                      <div className="text-sm">
                        <span className="font-heading font-semibold">{n.actor?.display_name}</span>
                        <span className="text-mute"> yeni bir gönderi paylaştı</span>
                        {n.has_disclosure && n.post_ticker && (
                          <span className="ml-1.5 text-[10px] font-heading font-semibold px-1.5 py-0.5 rounded-full bg-violet-soft text-violet align-middle">{n.post_ticker} · Pozisyon açıklamalı</span>
                        )}
                      </div>
                      {n.post_preview && <div className="text-xs text-mute mt-0.5 line-clamp-2">{n.post_preview}</div>}
                      <div className="text-[11px] text-mute mt-1">{relTime(n.created_at)}</div>
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
