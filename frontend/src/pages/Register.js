import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { TrendingUp } from "lucide-react";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ email: "", password: "", display_name: "", username: "" });
  const [busy, setBusy] = useState(false);
  const upd = (k, v) => setF((x) => ({ ...x, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    const r = await register(f);
    setBusy(false);
    if (r.ok) { toast.success("Divimero'ya hoşgeldin"); nav("/onboarding"); }
    else toast.error(r.error);
  };

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <Link to="/" className="flex items-center gap-2 mb-6">
          <div className="h-9 w-9 rounded-xl bg-brand-soft flex items-center justify-center"><TrendingUp size={20} className="text-brand"/></div>
          <span className="font-heading text-xl font-bold tracking-tight">divimero</span>
        </Link>
        <h1 className="font-heading text-3xl font-bold">Hesap oluştur</h1>
        <p className="text-mute mt-1">Portföyün sana özel, paylaşımların sana ait.</p>

        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <Label>Görünen ad</Label>
            <Input value={f.display_name} onChange={(e)=>upd("display_name", e.target.value)} required data-testid="reg-name"/>
          </div>
          <div>
            <Label>Kullanıcı adı</Label>
            <Input value={f.username} onChange={(e)=>upd("username", e.target.value.replace(/[^a-zA-Z0-9._]/g,'').toLowerCase())} required data-testid="reg-username"/>
          </div>
          <div>
            <Label>E-posta</Label>
            <Input value={f.email} onChange={(e)=>upd("email", e.target.value)} type="email" required data-testid="reg-email"/>
          </div>
          <div>
            <Label>Şifre</Label>
            <Input value={f.password} onChange={(e)=>upd("password", e.target.value)} type="password" placeholder="En az 6 karakter" required data-testid="reg-password"/>
          </div>
          <Button type="submit" disabled={busy} className="w-full h-11 rounded-full bg-ink hover:bg-black text-white" data-testid="reg-submit">
            {busy ? "Oluşturuluyor…" : "Ücretsiz üye ol"}
          </Button>
        </form>
        <p className="mt-4 text-xs text-mute">Portföyün varsayılan olarak gizlidir. İçerik paylaşırken pozisyon bilgini ekleyip eklememeye siz karar verirsiniz.</p>
        <p className="mt-6 text-sm text-mute">Hesabın var mı? <Link to="/login" className="text-ink font-medium hover:underline">Giriş yap</Link></p>
      </div>
    </div>
  );
}
