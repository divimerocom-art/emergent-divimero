import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, relTime } from "@/lib/api";
import FeedCard from "@/components/FeedCard";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export default function PostDetail() {
  const { postId } = useParams();
  const { user } = useAuth();
  const [post, setPost] = useState(null);
  const [comments, setComments] = useState([]);
  const [text, setText] = useState("");

  const load = async () => {
    const [{ data: p }, { data: c }] = await Promise.all([
      api.get(`/posts/${postId}`), api.get(`/posts/${postId}/comments`),
    ]);
    setPost(p); setComments(c);
  };
  useEffect(() => { load(); }, [postId]);

  const submit = async (e) => {
    e.preventDefault();
    if (!user) { toast("Yorum için giriş yapın"); return; }
    if (!text.trim()) return;
    try { await api.post(`/posts/${postId}/comments`, { text }); setText(""); load(); } catch {}
  };

  if (!post) return <div className="text-mute">Yükleniyor…</div>;

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <FeedCard post={post} onChange={load}/>
      <div className="rounded-2xl border border-line bg-white p-5">
        <h2 className="font-heading font-semibold mb-3">Yorumlar ({comments.length})</h2>
        <form onSubmit={submit} className="flex gap-2 mb-4">
          <Input value={text} onChange={(e)=>setText(e.target.value)} placeholder="Yorumunuzu yazın…" data-testid="comment-input"/>
          <Button type="submit" className="rounded-full bg-ink hover:bg-black text-white" data-testid="comment-submit">Gönder</Button>
        </form>
        <ul className="space-y-3">
          {comments.map(c => (
            <li key={c.id} className="flex items-start gap-3">
              <Avatar className="h-8 w-8 border border-line">
                {c.author?.avatar_url && <AvatarImage src={c.author.avatar_url}/>}
                <AvatarFallback className="bg-brand-soft text-brand text-xs">{(c.author?.display_name||"?").slice(0,1)}</AvatarFallback>
              </Avatar>
              <div className="flex-1">
                <div className="text-sm"><span className="font-heading font-semibold">{c.author?.display_name}</span> <span className="text-mute">· {relTime(c.created_at)}</span></div>
                <div className="text-sm text-ink">{c.text}</div>
              </div>
            </li>
          ))}
          {comments.length === 0 && <div className="text-sm text-mute">İlk yorumu yapan sen ol.</div>}
        </ul>
      </div>
    </div>
  );
}
