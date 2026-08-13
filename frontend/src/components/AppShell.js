import { Link, NavLink, useNavigate } from "react-router-dom";
import { Home, PieChart, User as UserIcon, LogOut, Plus, TrendingUp } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import NotificationsBell from "@/components/NotificationsBell";

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  return (
    <div className="min-h-screen bg-bg text-ink">
      {/* Top bar (desktop) */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-sm border-b border-line">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          <Link to="/feed" className="flex items-center gap-2 group" data-testid="brand-home">
            <div className="h-8 w-8 rounded-xl bg-brand-soft flex items-center justify-center">
              <TrendingUp size={18} strokeWidth={2} className="text-brand" />
            </div>
            <span className="font-heading font-bold text-lg tracking-tight">divimero</span>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            <TopLink to="/feed" icon={<Home size={18} />} label="Akış" testId="nav-feed" />
            <TopLink to="/portfolio" icon={<PieChart size={18} />} label="Portföy" testId="nav-portfolio" />
            {user && <TopLink to={`/u/${user.username}`} icon={<UserIcon size={18} />} label="Profil" testId="nav-profile" />}
          </nav>

          <div className="flex items-center gap-2">
            <Button onClick={() => nav("/compose")} size="sm" className="rounded-full bg-ink hover:bg-black text-white font-medium" data-testid="cta-compose">
              <Plus size={16} className="mr-1" /> Paylaş
            </Button>
            {user && <NotificationsBell />}
            {user ? (
              <button onClick={async ()=>{await logout(); nav("/");}} className="p-2 rounded-full hover:bg-surface transition-colors" title="Çıkış" data-testid="btn-logout">
                <LogOut size={18} className="text-mute" />
              </button>
            ) : (
              <Link to="/login" className="text-sm text-mute hover:text-ink" data-testid="nav-login">Giriş</Link>
            )}
            {user && (
              <Link to={`/u/${user.username}`} data-testid="nav-avatar">
                <Avatar className="h-8 w-8 border border-line">
                  {user.avatar_url && <AvatarImage src={user.avatar_url} />}
                  <AvatarFallback className="bg-brand-soft text-brand font-heading">{(user.display_name || user.username || "?").slice(0,1).toUpperCase()}</AvatarFallback>
                </Avatar>
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 sm:px-6 py-6 pb-24 md:pb-10">{children}</main>

      {/* Bottom nav (mobile) */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 h-16 bg-white border-t border-line flex justify-around items-center">
        <BottomLink to="/feed" icon={<Home size={22} />} label="Akış" testId="mnav-feed" />
        <BottomLink to="/portfolio" icon={<PieChart size={22} />} label="Portföy" testId="mnav-portfolio" />
        {user && <BottomLink to={`/u/${user.username}`} icon={<UserIcon size={22} />} label="Profil" testId="mnav-profile" />}
      </nav>
    </div>
  );
}

function TopLink({ to, icon, label, testId }) {
  return (
    <NavLink to={to} data-testid={testId} className={({ isActive }) => `flex items-center gap-2 px-3 py-2 rounded-full text-sm font-medium transition-colors ${isActive ? "bg-surface text-ink" : "text-mute hover:text-ink"}`}>
      {icon}<span>{label}</span>
    </NavLink>
  );
}

function BottomLink({ to, icon, label, testId }) {
  return (
    <NavLink to={to} data-testid={testId} className={({ isActive }) => `flex flex-col items-center gap-0.5 px-4 py-1 text-xs font-medium transition-colors ${isActive ? "text-brand" : "text-mute"}`}>
      {icon}<span>{label}</span>
    </NavLink>
  );
}
