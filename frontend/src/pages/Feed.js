import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import FeedCard from "@/components/FeedCard";
import { Link } from "react-router-dom";
import { Plus, Sparkles } from "lucide-react";

export default function Feed() {
  const [posts, setPosts] = useState(null);
  const load = async () => { try { const { data } = await api.get("/feed"); setPosts(data); } catch { setPosts([]); } };
  useEffect(() => { load(); }, []);

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-end justify-between mb-4">
        <div>
          <h1 className="font-heading text-2xl md:text-3xl font-bold tracking-tight">Akış</h1>
          <p className="text-sm text-mute">Yatırımcıların söyledikleri ve — paylaşırlarsa — yaptıkları.</p>
        </div>
        <Link to="/compose" className="hidden md:inline-flex items-center gap-1.5 text-sm font-medium text-ink hover:text-brand transition-colors" data-testid="feed-compose">
          <Plus size={16}/> Yeni gönderi
        </Link>
      </div>

      {posts === null && (
        <div className="space-y-3">
          {[0,1,2].map(i => <div key={i} className="rounded-2xl border border-line bg-white p-6 animate-pulse h-40" />)}
        </div>
      )}
      {posts?.length === 0 && (
        <div className="rounded-2xl border border-line bg-surface p-10 text-center">
          <Sparkles className="mx-auto text-brand" size={32} />
          <div className="mt-3 font-heading font-semibold">Akışta henüz gönderi yok</div>
          <div className="text-sm text-mute">İlk paylaşımı yapan sen ol.</div>
          <Link to="/compose" className="inline-block mt-4 px-4 py-2 rounded-full bg-ink text-white text-sm font-medium">Paylaş</Link>
        </div>
      )}
      <div className="space-y-4">
        {posts?.map((p) => <FeedCard key={p.id} post={p} onChange={load} />)}
      </div>
    </div>
  );
}
