import { ArrowDown, ArrowUp, Lock, Minus, Circle } from "lucide-react";
import { pct, positionShare } from "@/lib/api";

/**
 * The HERO component: shows publication-time allocation vs current allocation.
 * Enforces disclosure privacy controls exactly as chosen by the creator.
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
      case "unchanged": return { label: "Değişmedi", icon: Minus, color: "text-mute", bg: "bg-surface" };
      case "closed":    return { label: "Kapatıldı", icon: Circle, color: "text-mute", bg: "bg-surface" };
      default:          return null;
    }
  })();

  // Relative size of the move, e.g. "pozisyonun ~%50'si". Only present for
  // increased/reduced — "Kapatıldı" and "Değişmedi" are already unambiguous.
  const magnitude = disclosure.change_magnitude_pct ?? null;

  return (
    <div className="rounded-2xl border border-line bg-surface p-4 md:p-5" data-testid="position-disclosure-card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs uppercase tracking-wider text-mute font-heading font-semibold">Portföye Bağlı Pozisyon</span>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-white border border-line text-mute" title="Kullanıcı beyanı — doğrulanmış değildir">Kişisel beyan</span>
        </div>
        <span className="font-heading font-bold text-ink" data-testid="disclosure-ticker">{disclosure.ticker}</span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-white border border-line p-3">
          <div className="text-[11px] uppercase tracking-wider text-mute font-medium">Yayınlandığında</div>
          <div className="mt-1 font-heading text-2xl font-bold tabular text-ink" data-testid="disclosure-published">
            {publishedHidden ? (
              <span className="inline-flex items-center gap-1 text-mute text-base"><Lock size={14} /> Gizli</span>
            ) : publishedPct != null ? pct(publishedPct) : publishedRange || "—"}
          </div>
        </div>
        <div className="rounded-xl bg-white border border-line p-3">
          <div className="text-[11px] uppercase tracking-wider text-mute font-medium">Güncel</div>
          <div className="mt-1 font-heading text-2xl font-bold tabular text-ink" data-testid="disclosure-current">
            {currentAlloc == null ? "—" : pct(currentAlloc)}
          </div>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2 flex-wrap">
        {status && (
          <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full ${status.bg} ${status.color}`} data-testid="disclosure-status">
            <status.icon size={14} /> {status.label}
          </span>
        )}
        {magnitude != null && (
          <span className="text-[11px] text-mute" data-testid="disclosure-magnitude">· {positionShare(magnitude)}</span>
        )}
        {disclosure.show_quantity === false && <span className="text-[11px] text-mute">Adet gizli</span>}
        {disclosure.show_value === false && <span className="text-[11px] text-mute">Tutar gizli</span>}
      </div>
    </div>
  );
}
