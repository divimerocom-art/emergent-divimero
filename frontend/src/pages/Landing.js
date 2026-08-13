import { Link, useNavigate } from "react-router-dom";
import { TrendingUp, ShieldCheck, Eye, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { useState } from "react";
import { toast } from "sonner";

export default function Landing() {
  const nav = useNavigate();
  const { login } = useAuth();
  const [busy, setBusy] = useState(false);

  const demo = async (email) => {
    setBusy(true);
    const r = await login(email, "demo1234");
    setBusy(false);
    if (r.ok) { toast.success("Demo hesabına giriş yapıldı"); nav("/feed"); }
    else toast.error(r.error);
  };

  return (
    <div className="min-h-screen bg-white text-ink">
      <header className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-9 w-9 rounded-xl bg-brand-soft flex items-center justify-center">
            <TrendingUp size={20} className="text-brand" strokeWidth={2}/>
          </div>
          <span className="font-heading text-xl font-bold tracking-tight">divimero</span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login" className="text-sm text-mute hover:text-ink" data-testid="link-login">Giriş</Link>
          <Button onClick={()=>nav("/register")} className="rounded-full bg-ink hover:bg-black text-white" data-testid="cta-register">Ücretsiz üye ol</Button>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-6 pt-10 md:pt-20 grid md:grid-cols-2 gap-10 md:gap-16 items-center">
        <div>
          <span className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1 rounded-full bg-violet-soft text-violet">Building Türkiye Challenge</span>
          <h1 className="mt-4 font-heading text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.05]">
            Yatırımcıların<br/>
            <span className="text-brand">söylediklerini değil</span>,<br/>
            yaptıklarını takip edin.
          </h1>
          <p className="mt-5 text-lg text-mute max-w-xl">
            Divimero, BIST portföyünüzü takip etmenizi ve — istediğinizde — pozisyon oranınızı içeriklerinizle şeffaf biçimde paylaşmanızı sağlar.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Button onClick={()=>nav("/register")} size="lg" className="rounded-full bg-brand hover:bg-brand/90 text-white h-12 px-6" data-testid="hero-register">
              Hemen başla <ArrowRight size={18} className="ml-1"/>
            </Button>
            <Button onClick={()=>demo("deniz@divimero.com")} disabled={busy} size="lg" variant="outline" className="rounded-full h-12 px-6 border-line" data-testid="hero-demo-deniz">
              Demo: İçerik üreticisi (Deniz)
            </Button>
            <Button onClick={()=>demo("ece@divimero.com")} disabled={busy} size="lg" variant="outline" className="rounded-full h-12 px-6 border-line" data-testid="hero-demo-ece">
              Demo: Takipçi (Ece)
            </Button>
          </div>
          <p className="mt-4 text-xs text-mute">Piyasa fiyatları demo amaçlı, açıkça etiketlenmiştir. Yatırım tavsiyesi değildir.</p>
        </div>

        <div className="relative">
          <div className="rounded-2xl border border-line bg-white p-5 shadow-sm">
            <div className="text-xs uppercase tracking-wider text-mute font-heading font-semibold">Portföye Bağlı Pozisyon</div>
            <div className="mt-2 flex items-center justify-between">
              <div>
                <div className="text-xs text-mute">THYAO</div>
                <div className="font-heading text-xl font-bold">Türk Hava Yolları</div>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-white border border-line text-mute">Kişisel beyan</span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-xl bg-surface p-3">
                <div className="text-[11px] uppercase tracking-wider text-mute font-medium">Yayınlandığında</div>
                <div className="mt-1 font-heading text-2xl font-bold tabular">%5.20</div>
              </div>
              <div className="rounded-xl bg-surface p-3">
                <div className="text-[11px] uppercase tracking-wider text-mute font-medium">Güncel</div>
                <div className="mt-1 font-heading text-2xl font-bold tabular">%2.60</div>
              </div>
            </div>
            <div className="mt-3">
              <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-orangeSoft text-neg">↓ Azalttı</span>
              <span className="ml-2 text-[11px] text-mute">Adet gizli · Tutar gizli</span>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-3 gap-3">
            <Feature icon={<TrendingUp className="text-brand" size={18}/>} bg="bg-brand-soft" title="Portföy" text="Manuel işlem, FIFO maliyet, gerçek/gerçekleşmemiş K/Z."/>
            <Feature icon={<ShieldCheck className="text-violet" size={18}/>} bg="bg-violet-soft" title="Gizlilik" text="Oranı paylaş, adet ve tutarı gizle."/>
            <Feature icon={<Eye className="text-orange" size={18}/>} bg="bg-orangeSoft" title="Şeffaflık" text="Pozisyon değişimini takipçilerin görsün."/>
          </div>
        </div>
      </section>
    </div>
  );
}

function Feature({ icon, title, text, bg }) {
  return (
    <div className="rounded-2xl border border-line p-3 bg-white">
      <div className={`h-8 w-8 rounded-lg ${bg} flex items-center justify-center`}>{icon}</div>
      <div className="mt-2 font-heading font-semibold text-sm">{title}</div>
      <div className="text-xs text-mute leading-snug">{text}</div>
    </div>
  );
}
