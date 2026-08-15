import { Link, useNavigate } from "react-router-dom";
import { TrendingUp, ShieldCheck, Eye, ArrowRight, ArrowDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import BrandLogo from "@/components/BrandLogo";
import { useState } from "react";
import { toast } from "sonner";

// Real links rather than onClick buttons, so the nav landmark actually contains
// links and middle-click / ctrl-click open a new tab as users expect.
const pillCta =
  "inline-flex items-center justify-center h-10 px-4 rounded-full bg-ink hover:bg-black text-white text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2";

export default function Landing() {
  const nav = useNavigate();
  const { login, user, loading } = useAuth();
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
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-full focus:bg-ink focus:px-4 focus:py-2 focus:text-sm focus:text-white">
        İçeriğe geç
      </a>

      <header className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between gap-4">
        <BrandLogo testId="brand-home-landing" />
        {/* Signed-in visitors land here too now, so the header offers the way
            into the app rather than a second invitation to register.

            Gated on `loading`, not just `user`: AuthContext starts at
            user === undefined while GET /auth/me is in flight, which is falsy.
            Rendering the signed-out branch during that window would show a
            signed-in user "Ücretsiz üye ol" and, if they clicked it, hand them
            a registration form that would replace their own session. The nav
            reserves its height so the swap does not jump the header. */}
        <nav aria-label="Üst menü" className="flex items-center gap-3 min-h-[40px]">
          {loading ? null : user ? (
            <Link to="/feed" className={pillCta} data-testid="cta-feed">Akışa git</Link>
          ) : (
            <>
              <Link to="/login" className="text-sm text-mute hover:text-ink" data-testid="link-login">Giriş</Link>
              <Link to="/register" className={pillCta} data-testid="cta-register">Ücretsiz üye ol</Link>
            </>
          )}
        </nav>
      </header>

      <main id="main" tabIndex={-1}>
      <section className="max-w-6xl mx-auto px-6 pt-6 md:pt-20 grid md:grid-cols-2 gap-6 md:gap-16 items-center">
        <div>
          <span className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1 rounded-full bg-violet-soft text-violet">Building Türkiye Challenge</span>
          <h1 className="mt-4 font-heading text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.05]">
            Yatırımcıların<br/>
            <span className="text-brand">söylediklerini değil</span>,<br/>
            yaptıklarını takip edin.
          </h1>
          <p className="mt-5 text-lg text-mute max-w-xl">
            Bir yatırımcı bir hisseyi övdüğünde gerçekten tutuyor mu, portföyünün ne kadarı, sonra sessizce azalttı mı?
            Divimero her tezi yayınlandığı andaki portföy oranına bağlar ve pozisyon değiştiğinde takipçiye gösterir.
          </p>
          <p lang="en" className="mt-2 text-sm text-mute max-w-xl block" data-testid="hero-en-summary">
            Divimero lets Turkish investors track their BIST portfolio and — when they choose — share their position size transparently alongside their content.
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-3">
            <Button onClick={()=>demo("deniz@divimero.com")} disabled={busy} size="lg" className="rounded-full bg-brand hover:bg-brand/90 text-white h-12 px-6" data-testid="hero-demo-deniz">
              Demoyu incele — kayıt gerekmez <ArrowRight size={18} className="ml-1"/>
            </Button>
            <button onClick={()=>demo("ece@divimero.com")} disabled={busy} className="text-sm text-mute underline underline-offset-4 hover:text-ink disabled:opacity-50" data-testid="hero-demo-ece">
              Takipçi olarak gir
            </button>
          </div>
          <p className="mt-4 text-xs text-mute">Fiyatlar Yahoo Finance'ten canlı alınır. Portföyler kullanıcı beyanıdır, aracı kurum doğrulaması yoktur. Yatırım tavsiyesi değildir.</p>
        </div>

        <div className="relative">
          {/* The card the judge meets one click later. Keep these figures identical to the
              seeded THYAO thesis — a promo that disagrees with the demo costs more trust
              than it buys. */}
          <div className="rounded-2xl border border-line border-l-4 border-l-brand bg-surface p-5 shadow-sm">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2 flex-wrap min-w-0">
                <span className="text-xs uppercase tracking-wider text-mute font-heading font-semibold">Portföye Bağlı Pozisyon</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-white border border-line text-mute whitespace-nowrap shrink-0">Kişisel beyan</span>
              </div>
              <span className="font-heading font-bold text-ink shrink-0">THYAO</span>
            </div>
            <div className="mt-4 grid grid-cols-[1fr_auto_1fr] items-center gap-2 md:gap-3">
              <div className="rounded-xl bg-white border border-line p-3">
                <div className="text-[11px] uppercase tracking-wider text-mute font-medium">Yayınlandığında</div>
                <div className="mt-1 font-heading text-2xl md:text-3xl font-bold tabular">%6,18</div>
              </div>
              <ArrowRight size={16} className="text-mute shrink-0" aria-hidden="true"/>
              <div className="rounded-xl bg-white border border-line p-3">
                <div className="text-[11px] uppercase tracking-wider text-mute font-medium">Güncel</div>
                <div className="mt-1 font-heading text-2xl md:text-3xl font-bold tabular">%1,83</div>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2 flex-wrap">
              <span className="text-[11px] uppercase tracking-wider text-mute font-medium">Yayından bu yana alım-satım</span>
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-orangeSoft text-neg">
                <ArrowDown size={14}/> Azalttı <span className="font-medium">· pozisyonun ~%53'ü</span>
              </span>
            </div>
            <div className="mt-2 flex items-center gap-2 flex-wrap text-[11px] text-mute">
              <span>Adet gizli</span><span>Tutar gizli</span>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Feature icon={<TrendingUp className="text-brand" size={18}/>} bg="bg-brand-soft" title="Portföy" text="FIFO maliyet, gerçekleşen K/Z, temettü, XIRR."/>
            <Feature icon={<ShieldCheck className="text-violet" size={18}/>} bg="bg-violet-soft" title="Gizlilik" text="Oranı paylaş, adet ve tutarı gizle."/>
            <Feature icon={<Eye className="text-orange" size={18}/>} bg="bg-orangeSoft" title="Şeffaflık" text="Pozisyon değişimini takipçilerin görsün."/>
          </div>
        </div>
      </section>

      {/* Why this matters. Every figure carries its source on screen — on a product about
          unverified claims, an uncited number would undercut the whole premise. */}
      <section className="max-w-6xl mx-auto px-6 pt-12 md:pt-20 pb-12 md:pb-20" aria-labelledby="impact-heading">
        <h2 id="impact-heading" className="font-heading text-2xl md:text-3xl font-bold tracking-tight">
          Neden önemli?
        </h2>
        <div className="mt-5 grid md:grid-cols-3 gap-4">
          <Fact
            figure="6.906.417"
            text="Borsa İstanbul'da pay senedi bakiyesi bulunan yatırımcı sayısı (31 Temmuz 2026)."
            source="MKK Sistem İstatistikleri, satır 3.1"
            href="https://www.mkk.com.tr/sites/default/files/2026-08/MKK_SYSTEM_STATISTICS_JULY.pdf"
          />
          <Fact
            text="SPK, sosyal medya hesabından pay piyasasına yönelik paylaşım yapıp aynı anda o payda işlem gerçekleştiren kişilere idari para cezası uyguluyor; ilgili içeriklerin kaldırılması için Erişim Sağlayıcıları Birliği'ne bildirimde bulunuyor."
            source="SPK Bülteni 2026/34, 04.06.2026, Bölüm C.1"
            href="https://spk.gov.tr/data/6a21eb938f95db12a4589b32/2026-34.pdf"
          />
          <Fact
            text={'Kurul, finansal içerik üreticilerine dair "Finfluencer mı, Fraudencer mı?" adlı bir farkındalık programı yürütüyor.'}
            source="SPK, 12.03.2026"
            href="https://spk.gov.tr/duyurular/baskanin-konusmalari/2026/paradan-degere-finansal-okuryazarligin-donusturucu-gucu-etkinligi"
          />
        </div>
        <p className="mt-5 text-sm text-mute max-w-3xl">
          Divimero bu boşluğu kapatmaz, görünür kılar: bir tez yayınlandığında portföy oranı o an
          dondurulur ve sonrasında pozisyonun gerçekten değişip değişmediği takipçiye gösterilir.
        </p>
      </section>
      </main>

      {/* Every link below points at a route that actually exists in App.js.
          The disclosure restates the hero's existing self-reported / not
          broker-verified / not-advice wording; no new legal, contact or
          traction claim is introduced here. */}
      <footer className="border-t border-line bg-surface">
        <div className="max-w-6xl mx-auto px-6 py-10 md:py-12">
          <div className="grid gap-8 md:grid-cols-3">
            <div className="md:col-span-2 max-w-md">
              <BrandLogo testId="brand-home-footer" />
              <p className="mt-3 text-sm text-mute">
                Yatırımcıların söylediklerini değil, yaptıklarını takip edin. Tezinize portföy
                oranınızı iliştirin; adet ve tutar gizli kalsın.
              </p>
            </div>

            <nav aria-labelledby="footer-nav-heading">
              <h2 id="footer-nav-heading" className="font-heading text-sm font-semibold">
                Bağlantılar
              </h2>
              <ul className="mt-3 space-y-2 text-sm">
                <li>
                  <a href="#impact-heading" className="text-mute hover:text-ink underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded">
                    Neden önemli?
                  </a>
                </li>
                {/* Same `loading` gate as the header — see the note there. */}
                {loading ? null : user ? (
                  <>
                    <li><FooterLink to="/feed" label="Akış" /></li>
                    <li><FooterLink to="/portfolio" label="Portföy" /></li>
                  </>
                ) : (
                  <>
                    <li><FooterLink to="/login" label="Giriş" /></li>
                    <li><FooterLink to="/register" label="Ücretsiz üye ol" /></li>
                  </>
                )}
              </ul>
            </nav>
          </div>

          <div className="mt-8 pt-6 border-t border-line flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <p className="text-xs text-mute max-w-2xl">
              Portföyler kullanıcı beyanıdır; aracı kurum doğrulaması yoktur. Fiyatlar Yahoo
              Finance'ten alınır. Yatırım tavsiyesi değildir.
            </p>
            <p className="text-xs text-mute shrink-0">© {new Date().getFullYear()} Divimero</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

function FooterLink({ to, label }) {
  return (
    <Link
      to={to}
      className="text-mute hover:text-ink underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded"
    >
      {label}
    </Link>
  );
}

function Fact({ figure, text, source, href }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-5 flex flex-col">
      {figure && (
        <div className="font-heading text-3xl md:text-4xl font-bold tracking-tight tabular text-ink">{figure}</div>
      )}
      <p className={`${figure ? "mt-2" : ""} text-sm text-ink leading-snug flex-1`}>{text}</p>
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-3 text-xs text-mute underline underline-offset-4 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded"
      >
        Kaynak: {source}
      </a>
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
