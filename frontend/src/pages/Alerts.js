import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, pct, relTime } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Bell, Trash2, ArrowUpDown, TrendingUp, TrendingDown } from "lucide-react";
import { toast } from "sonner";

const DIR = {
  any:      { l: "Herhangi yön", i: <ArrowUpDown size={13}/>, cls: "bg-surface text-ink" },
  increase: { l: "Artış",       i: <TrendingUp size={13} className="text-pos"/>, cls: "bg-brand-soft text-brand" },
  decrease: { l: "Azalış",      i: <TrendingDown size={13} className="text-neg"/>, cls: "bg-orangeSoft text-neg" },
};

export default function Alerts() {
  const [alerts, setAlerts] = useState(null);

  const load = async () => { try { const { data } = await api.get("/alerts"); setAlerts(data); } catch { setAlerts([]); } };
  useEffect(() => { load(); }, []);

  const toggle = async (a) => {
    try { await api.patch(`/alerts/${a.id}`, { active: !a.active }); toast.success(a.active ? "Uyarı duraklatıldı" : "Uyarı yeniden aktif"); load(); }
    catch { toast.error("Güncellenemedi"); }
  };
  const remove = async (a) => {
    try { await api.delete(`/alerts/${a.id}`); toast.success("Uyarı kaldırıldı"); load(); }
    catch { toast.error("Silinemedi"); }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div>
        <h1 className="font-heading text-2xl md:text-3xl font-bold tracking-tight inline-flex items-center gap-2"><Bell size={22} className="text-brand"/> Uyarılarım</h1>
        <p className="text-sm text-mute mt-1">Takip ettiğin yaratıcıların pozisyon değişimlerinde ne zaman bildirim istediğini burada yönet.</p>
      </div>

      {alerts === null && (
        <div className="rounded-2xl border border-line bg-white p-6 animate-pulse h-24"/>
      )}

      {alerts?.length === 0 && (
        <div className="rounded-2xl border border-line bg-surface p-10 text-center" data-testid="alerts-empty">
          <Bell className="mx-auto text-mute" size={32}/>
          <div className="mt-3 font-heading font-semibold">Henüz uyarın yok</div>
          <div className="text-sm text-mute mt-1">Bir yaratıcının profilinde "Uyarı kur" butonuyla başla.</div>
          <Link to="/feed" className="inline-block mt-4 px-4 py-2 rounded-full bg-ink text-white text-sm font-medium">Akışa dön</Link>
        </div>
      )}

      {alerts?.length > 0 && (
        <ul className="rounded-2xl border border-line bg-white divide-y divide-line" data-testid="alerts-list">
          {alerts.map(a => {
            const dir = DIR[a.direction] || DIR.any;
            return (
              <li key={a.id} className="p-4 flex items-center gap-3" data-testid={`alert-row-${a.id}`}>
                <Link to={`/u/${a.followee?.username}`} className="shrink-0">
                  <Avatar className="h-10 w-10 border border-line">
                    {a.followee?.avatar_url && <AvatarImage src={a.followee.avatar_url}/>}
                    <AvatarFallback className="bg-brand-soft text-brand font-heading">{(a.followee?.display_name||"?").slice(0,1)}</AvatarFallback>
                  </Avatar>
                </Link>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Link to={`/u/${a.followee?.username}`} className="font-heading font-semibold hover:underline">{a.followee?.display_name}</Link>
                    <span className="text-xs text-mute">@{a.followee?.username}</span>
                    <span className="text-[10px] font-heading font-semibold px-2 py-0.5 rounded-full bg-violet-soft text-violet">{a.ticker}</span>
                  </div>
                  <div className="mt-1.5 flex items-center gap-2 flex-wrap text-xs">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full ${dir.cls} font-semibold`}>{dir.i} {dir.l}</span>
                    <span className="text-mute">Eşik <b className="tabular text-ink">{pct(a.threshold_pct)}</b></span>
                    <span className="text-mute">· Kurulma: {relTime(a.created_at)}</span>
                    {!a.active && <span className="text-mute">· <span className="italic">Duraklatıldı</span></span>}
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <Switch checked={a.active} onCheckedChange={()=>toggle(a)} data-testid={`alert-toggle-${a.id}`}/>
                  <button onClick={()=>remove(a)} className="p-2 rounded-full hover:bg-orangeSoft text-mute hover:text-neg transition-colors" title="Uyarıyı sil" data-testid={`alert-delete-${a.id}`}>
                    <Trash2 size={16}/>
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
