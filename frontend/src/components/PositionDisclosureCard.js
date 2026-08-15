import { ArrowDown, ArrowUp, ArrowRight, Lock, Equal, CircleSlash } from "lucide-react";
import { pct, positionShare } from "@/lib/api";

/**
 * The HERO component: shows publication-time allocation vs current allocation.
 * Enforces disclosure privacy controls exactly as chosen by the creator.
 *
 * The two percentages move with the share price; the badge moves only when the
 * creator actually trades. That distinction IS the product, so the card states
 * it rather than leaving the reader to infer it from numbers that look wrong.
 */
export default function PositionDisclosureCard({ disclosure, current }) {
  if (!disclosure) return null;

  const publishedPct = disclosure.disclosed_allocation_pct;
  const publishedRange = disclosure.disclosed_range;
  const publishedHidden = !disclosure.show_allocation || disclosure.allocation_mode === "hidden";
  const currentAlloc = current?.allocation_pct ?? null;

  // Status label comes from the backend — the underlying private value is never exposed to the client.
  const status = (() => {
    switch (disclosure.change_status) {
      case "increased": return { label: "Artırdı", icon: ArrowUp, color: "text-pos", bg: "bg-brand-soft" };
      case "reduced":   return { label: "Azalttı", icon: ArrowDown, color: "text-neg", bg: "bg-orangeSoft" };
      case "unchanged": return { label: "Değişmedi", icon: Equal, color: "text-ink", bg: "bg-white border border-line" };
      case "closed":    return { label: "Kapattı", icon: CircleSlash, color: "text-ink", bg: "bg-white border border-line" };
      default:          return null;
    }
  })();

  // Relative size of the move, e.g. "pozisyonun ~%50'si". Only present for
  // increased/reduced — "Kapattı" and "Değişmedi" are already unambiguous.
  const magnitude = disclosure.change_magnitude_pct ?? null;

  // The allocation drifted but the share count did not. Without this line the card
  // reads as broken arithmetic; with it, it is the proof that the badge is trade-based.
  const driftOnly =
    disclosure.change_status === "unchanged" &&
    !publishedHidden && publishedPct != null && currentAlloc != null &&
    Math.abs(currentAlloc - publishedPct) >= 0.01;

  return (
    <div className="rounded-2xl border border-line border-l-4 border-l-brand bg-surface p-4 md:p-5" data-testid="position-disclosure-card">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          <span className="text-xs uppercase tracking-wider text-mute font-heading font-semibold">Portföye Bağlı Pozisyon</span>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-white border border-line text-mute whitespace-nowrap shrink-0" title="Kullanıcı beyanı — doğrulanmış değildir">Kişisel beyan</span>
        </div>
        <span className="font-heading font-bold text-ink shrink-0" data-testid="disclosure-ticker">{disclosure.ticker}</span>
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 md:gap-3">
        <div className="rounded-xl bg-white border border-line p-3">
          <div className="text-[11px] uppercase tracking-wider text-mute font-medium">Yayınlandığında</div>
          <div className="mt-1 font-heading text-2xl md:text-3xl font-bold tabular text-ink" data-testid="disclosure-published">
            {publishedHidden ? (
              <span className="inline-flex items-center gap-1 text-mute text-base"><Lock size={14} /> Gizli</span>
            ) : publishedPct != null ? pct(publishedPct) : publishedRange || "—"}
          </div>
        </div>
        <ArrowRight size={16} className="text-mute shrink-0" aria-hidden="true" />
        <div className="rounded-xl bg-white border border-line p-3">
          <div className="text-[11px] uppercase tracking-wider text-mute font-medium">Güncel</div>
          <div className="mt-1 font-heading text-2xl md:text-3xl font-bold tabular text-ink" data-testid="disclosure-current">
            {currentAlloc == null ? "—" : pct(currentAlloc)}
          </div>
        </div>
      </div>

      {status && (
        <div className="mt-3 flex items-center gap-2 flex-wrap">
          <span className="text-[11px] uppercase tracking-wider text-mute font-medium">Yayından bu yana</span>
          <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full ${status.bg} ${status.color}`} data-testid="disclosure-status">
            <status.icon size={14} /> {status.label}
            {magnitude != null && (
              <span className="font-medium" data-testid="disclosure-magnitude">· {positionShare(magnitude)}</span>
            )}
          </span>
        </div>
      )}

      {driftOnly && (
        <p className="mt-2 text-[11px] text-mute leading-snug" data-testid="disclosure-drift-note">
          Adet değişmedi — orandaki fark fiyat hareketinden.
        </p>
      )}

      <div className="mt-2 flex items-center gap-2 flex-wrap text-[11px] text-mute">
        {disclosure.show_quantity === false && <span>Adet gizli</span>}
        {disclosure.show_value === false && <span>Tutar gizli</span>}
      </div>
    </div>
  );
}
