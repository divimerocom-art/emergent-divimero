import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { TrendingUp } from "lucide-react";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate(); const loc = useLocation();
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    const r = await login(email, password);
    setBusy(false);
    if (r.ok) { toast.success("Hoşgeldin"); nav(loc.state?.from || "/feed"); }
    else toast.error(r.error);
  };

  const fill = (em) => { setEmail(em); setPassword("demo1234"); };

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <Link to="/" className="flex items-center gap-2 mb-6">
          <div className="h-9 w-9 rounded-xl bg-brand-soft flex items-center justify-center"><TrendingUp size={20} className="text-brand"/></div>
          <span className="font-heading text-xl font-bold tracking-tight">divimero</span>
        </Link>
        <h1 className="font-heading text-3xl font-bold">Giriş yap</h1>
        <p className="text-mute mt-1">Portföyün ve akışın seni bekliyor.</p>

        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <Label>E-posta</Label>
            <Input value={email} onChange={(e)=>setEmail(e.target.value)} type="email" placeholder="ornek@divimero.com" required data-testid="login-email"/>
          </div>
          <div>
            <Label>Şifre</Label>
            <Input value={password} onChange={(e)=>setPassword(e.target.value)} type="password" placeholder="En az 6 karakter" required data-testid="login-password"/>
          </div>
          <Button type="submit" disabled={busy} className="w-full h-11 rounded-full bg-ink hover:bg-black text-white" data-testid="login-submit">
            {busy ? "Giriş yapılıyor…" : "Giriş yap"}
          </Button>
        </form>

        <div className="mt-6">
          <div className="text-xs text-mute mb-2">Hızlı jüri demosu:</div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" className="rounded-full border-line" onClick={()=>fill("deniz@divimero.com")} data-testid="fill-deniz">Deniz (üretici)</Button>
            <Button variant="outline" size="sm" className="rounded-full border-line" onClick={()=>fill("ece@divimero.com")} data-testid="fill-ece">Ece (takipçi)</Button>
          </div>
        </div>

        <p className="mt-6 text-sm text-mute">Hesabın yok mu? <Link to="/register" className="text-ink font-medium hover:underline">Üye ol</Link></p>
      </div>
    </div>
  );
}
