import { Link } from "react-router-dom";
import { Heart, MessageCircle } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import PositionDisclosureCard from "@/components/PositionDisclosureCard";
import { api, relTime } from "@/lib/api";
import { useState } from "react";

export default function FeedCard({ post, onChange }) {
  const [liked, setLiked] = useState(post.liked);
  const [likes, setLikes] = useState(post.likes_count);

  const toggleLike = async () => {
    try {
      const { data } = await api.post(`/posts/${post.id}/like`);
      setLiked(data.liked);
      setLikes((n) => n + (data.liked ? 1 : -1));
      onChange?.();
    } catch {}
  };

  const a = post.author || {};
  return (
    <article className="rounded-2xl border border-line bg-white p-4 md:p-6 animate-fade-up" data-testid={`feed-card-${post.id}`}>
      <header className="flex items-center gap-3">
        <Link to={`/u/${a.username}`}>
          <Avatar className="h-10 w-10 border border-line">
            {a.avatar_url && <AvatarImage src={a.avatar_url} />}
            <AvatarFallback className="bg-brand-soft text-brand font-heading">{(a.display_name || "?").slice(0,1)}</AvatarFallback>
          </Avatar>
        </Link>
        <div className="flex-1 min-w-0">
          <Link to={`/u/${a.username}`} className="font-heading font-semibold text-ink hover:underline">{a.display_name}</Link>
          <div className="text-xs text-mute">@{a.username} · {relTime(post.created_at)}</div>
        </div>
      </header>

      <p className="mt-3 text-[15px] leading-relaxed text-ink whitespace-pre-wrap">{post.text}</p>

      {post.tickers?.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {post.tickers.map((t) => (
            <span key={t} className="text-xs font-heading font-semibold px-2.5 py-1 rounded-full bg-violet-soft text-violet">${t}</span>
          ))}
        </div>
      )}

      {post.image_url && (
        <div className="mt-3 overflow-hidden rounded-xl border border-line">
          <img src={post.image_url} alt="" className="w-full max-h-96 object-cover" />
        </div>
      )}

      {post.video_url && (
        <div className="mt-3 overflow-hidden rounded-xl border border-line bg-black">
          <video src={post.video_url} controls playsInline preload="metadata" className="w-full max-h-96" data-testid={`video-${post.id}`}/>
        </div>
      )}

      {post.disclosure && (
        <div className="mt-4">
          <PositionDisclosureCard disclosure={post.disclosure} current={post.current_position} />
        </div>
      )}

      <footer className="mt-4 flex items-center gap-5 text-mute">
        <button onClick={toggleLike} className={`flex items-center gap-1.5 text-sm hover:text-ink transition-colors ${liked ? "text-neg" : ""}`} data-testid={`like-${post.id}`}>
          <Heart size={18} fill={liked ? "#FF3B30" : "none"} strokeWidth={2} />
          <span className="tabular">{likes}</span>
        </button>
        <Link to={`/p/${post.id}`} className="flex items-center gap-1.5 text-sm hover:text-ink transition-colors" data-testid={`comments-${post.id}`}>
          <MessageCircle size={18} />
          <span className="tabular">{post.comments_count}</span>
        </Link>
      </footer>
    </article>
  );
}
