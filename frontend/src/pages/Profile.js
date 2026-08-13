import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, pct, relTime } from "@/lib/api";
import FeedCard from "@/components/FeedCard";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { UserPlus, UserCheck } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export default function Profile() {
  const { username } = useParams();
  const { user: me } = useAuth();
  const [user, setUser] = useState(null);
  const [posts, setPosts] = useState([]);
  const [disc, setDisc] = useState([]);

  const load = async () => {
    const [{ data: u }, { data: p }, { data: d }] = await Promise.all([
      api.get(`/users/${username}`), api.get(`/users/${username}/posts`), api.get(`/users/${username}/disclosures`),
    ]);
    setUser(u); setPosts(p); setDisc(d);
  };
  useEffect(() => { load(); }, [username]);

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
            <Button onClick={toggleFollow} className={`rounded-full ${user.is_following ? "bg-surface text-ink hover:bg-line" : "bg-ink hover:bg-black text-white"}`} data-testid="btn-follow">
              {user.is_following ? <><UserCheck size={16} className="mr-1"/> Takiptesin</> : <><UserPlus size={16} className="mr-1"/> Takip et</>}
            </Button>
          )}
        </div>
      </div>

      {/* Disclosed holdings */}
      {disc.length > 0 && (
        <div className="rounded-2xl border border-line bg-white">
          <div className="p-4 md:p-5 border-b border-line">
            <h2 className="font-heading font-semibold">Beyan Edilen Pozisyonlar</h2>
            <p className="text-xs text-mute">Yalnızca kullanıcının gönderilerde açıkça paylaştığı pozisyonlar listelenir.</p>
          </div>
          <ul className="divide-y divide-line">
            {disc.map(d => {
              const cur = d.current?.allocation_pct ?? 0;
              const last = d.last_disclosed ?? 0;
              const diff = cur - last;
              const trend = Math.abs(diff) < 0.1 ? "Değişmedi" : diff > 0 ? "Artırdı" : cur < 0.1 ? "Kapatıldı" : "Azalttı";
              const c = trend === "Artırdı" ? "text-pos" : trend === "Azalttı" ? "text-neg" : "text-mute";
              return (
                <li key={d.ticker} className="px-4 md:px-5 py-3 flex items-center gap-4" data-testid={`disc-${d.ticker}`}>
                  <span className="font-heading font-semibold w-16">{d.ticker}</span>
                  <div className="flex-1 text-xs text-mute">İlk beyan: {relTime(d.opened_at)} · Son beyan: {pct(last)}</div>
                  <div className="tabular font-medium">Güncel {pct(cur)}</div>
                  <span className={`text-xs font-semibold ${c}`}>{trend}</span>
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
