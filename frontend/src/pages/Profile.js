import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, pct, relTime, positionShare } from "@/lib/api";
import FeedCard from "@/components/FeedCard";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { UserPlus, UserCheck, Bell } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import AlertDialog from "@/components/AlertDialog";

export default function Profile() {
  const { username } = useParams();
  const { user: me } = useAuth();
  const [user, setUser] = useState(null);
  const [posts, setPosts] = useState([]);
  const [disc, setDisc] = useState([]);
  const [alertOpen, setAlertOpen] = useState(false);

  const load = async () => {
    const [{ data: u }, { data: p }, { data: d }] = await Promise.all([
      api.get(`/users/${username}`), api.get(`/users/${username}/posts`), api.get(`/users/${username}/disclosures`),
    ]);
    setUser(u); setPosts(p); setDisc(d);
  };
  useEffect(() => { load(); }, [username]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!user) return <div className="text-mute">Yükleniyor…</div>;

  const isMe = me?.username === user.username;

  const toggleFollow = async () => {
    if (!me) { toast("Takip için giriş yapın"); return; }
    try { await api.post(`/users/${user.username}/follow`); load(); } catch {}
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="rounded-2xl border border-line bg-white p-5 md:p-6">
        <div className="flex items-start gap-4">
          <Avatar className="h-16 w-16 border border-line">
            {user.avatar_url && <AvatarImage src={user.avatar_url}/>}
            <AvatarFallback className="bg-brand-soft text-brand font-heading">{(user.display_name||"?").slice(0,1)}</AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <div className="font-heading text-xl font-bold">{user.display_name}</div>
            <div className="text-mute text-sm">@{user.username}</div>
            {user.bio && <p className="text-sm text-ink mt-2">{user.bio}</p>}
            <div className="mt-3 flex items-center gap-4 text-sm">
              <span><b className="tabular">{user.followers_count ?? 0}</b> <span className="text-mute">Takipçi</span></span>
              <span><b className="tabular">{user.following_count ?? 0}</b> <span className="text-mute">Takip</span></span>
            </div>
          </div>
          {!isMe && (
            <div className="flex items-center gap-2">
              {me && (
                <Button variant="outline" onClick={()=>setAlertOpen(true)} className="rounded-full border-line" data-testid="btn-alert">
                  <Bell size={16} className="mr-1"/> Uyarı kur
                </Button>
              )}
              <Button onClick={toggleFollow} className={`rounded-full ${user.is_following ? "bg-surface text-ink hover:bg-line" : "bg-ink hover:bg-black text-white"}`} data-testid="btn-follow">
                {user.is_following ? <><UserCheck size={16} className="mr-1"/> Takiptesin</> : <><UserPlus size={16} className="mr-1"/> Takip et</>}
              </Button>
            </div>
          )}
        </div>
      </div>

      <AlertDialog open={alertOpen} onOpenChange={setAlertOpen} followee={user} tickers={disc.map(d => d.ticker)}/>

      {/* Disclosed holdings */}
      {disc.length > 0 && (
        <div className="rounded-2xl border border-line bg-white">
          <div className="p-4 md:p-5 border-b border-line">
            <h2 className="font-heading font-semibold">Portföy Özeti — Beyan Edilen Pozisyonlar</h2>
            <p className="text-xs text-mute">Yalnızca kullanıcının gönderilerde açıkça paylaştığı ağırlıklar gösterilir. Adet ve tutar gizli tutulur.</p>
          </div>
          {/* Compact allocation bar (uses only DISCLOSED values, never live private data) */}
          {(() => {
            const rows = disc
              .filter(d => d.last_disclosed != null)
              .map(d => ({ ticker: d.ticker, val: Math.max(0, d.last_disclosed) }))
              .sort((a,b)=>b.val-a.val);
            const colors = ["#35C7B2","#7361F7","#FF7733","#D6B130","#12BD57","#171717"];
            const shown = rows.slice(0, 5);
            const totalShown = shown.reduce((s,r)=>s+r.val, 0);
            const remainingPct = Math.max(0, 100 - totalShown);
            return (
              <div className="p-4 md:p-5 border-b border-line" data-testid="alloc-bar">
                {rows.length === 0 ? (
                  <div className="text-xs text-mute">Bu kullanıcı henüz oran paylaşmadı — sadece hisse etiketleri açıklanmış.</div>
                ) : (
                  <>
                    <div className="h-3 rounded-full overflow-hidden flex bg-surface">
                      {shown.map((r, i) => (
                        <div key={r.ticker} title={`${r.ticker} · ${r.val.toFixed(1)}% (son beyan)`} style={{ width: `${r.val}%`, background: colors[i % colors.length] }} data-testid={`alloc-seg-${r.ticker}`}/>
                      ))}
                      {remainingPct > 0 && <div title={`Beyan edilmemiş · ${remainingPct.toFixed(1)}%`} style={{ width: `${remainingPct}%`, background: "#E3E3E3" }}/>}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-3 text-xs">
                      {shown.map((r,i) => (
                        <span key={r.ticker} className="inline-flex items-center gap-1.5">
                          <span className="h-2 w-2 rounded-full" style={{ background: colors[i % colors.length] }}/>
                          <span className="font-heading font-semibold">{r.ticker}</span>
                          <span className="tabular text-mute">{pct(r.val)}</span>
                        </span>
                      ))}
                      {remainingPct > 0 && (
                        <span className="inline-flex items-center gap-1.5">
                          <span className="h-2 w-2 rounded-full bg-line"/>
                          <span className="text-mute">Beyan edilmemiş</span>
                          <span className="tabular text-mute">{pct(remainingPct)}</span>
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] text-mute mt-2">Kişisel beyan · Adet ve tutar gizli · Yalnızca gönderilerde açıkça paylaşılan son beyan oranları kullanıldı.</p>
                  </>
                )}
              </div>
            );
          })()}
          <ul className="divide-y divide-line">
            {disc.map(d => {
              const cur = d.current?.allocation_pct ?? 0;
              const last = d.last_disclosed;
              const status = d.change_status;
              const trend = status === "increased" ? "Artırdı" : status === "reduced" ? "Azalttı" : status === "closed" ? "Kapattı" : status === "unchanged" ? "Değişmedi" : "—";
              const c = status === "increased" ? "text-pos" : status === "reduced" ? "text-neg" : "text-mute";
              return (
                <li key={d.ticker} className="px-4 md:px-5 py-3 flex items-center gap-4 flex-wrap" data-testid={`disc-${d.ticker}`}>
                  <span className="font-heading font-semibold w-16">{d.ticker}</span>
                  <div className="flex-1 min-w-0 text-xs text-mute">
                    İlk beyan: {relTime(d.opened_at)}
                    {last != null && <> · Son beyan: <b className="text-ink tabular">{pct(last)}</b></>}
                  </div>
                  {last != null && <div className="tabular font-medium">Güncel {pct(cur)}</div>}
                  {status && <span className={`text-xs font-semibold ${c}`} data-testid={`disc-status-${d.ticker}`}>{trend}</span>}
                  {d.change_magnitude_pct != null && (
                    <span className="text-[11px] text-mute">· {positionShare(d.change_magnitude_pct)}</span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Posts */}
      <div>
        <h2 className="font-heading font-semibold mb-3">Gönderiler</h2>
        {posts.length === 0 ? (
          <div className="rounded-2xl border border-line bg-surface p-8 text-center text-sm text-mute">Henüz gönderi yok.</div>
        ) : (
          <div className="space-y-4">{posts.map(p => <FeedCard key={p.id} post={p} onChange={load}/>)}</div>
        )}
      </div>
    </div>
  );
}
