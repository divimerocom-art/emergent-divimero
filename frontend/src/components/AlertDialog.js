import { useState, useEffect } from "react";
import { api, pct } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Bell, TrendingUp, TrendingDown, ArrowUpDown } from "lucide-react";

export default function AlertDialog({ open, onOpenChange, followee, tickers }) {
  const [ticker, setTicker] = useState(tickers?.[0] || "");
  const [direction, setDirection] = useState("any");
  const [threshold, setThreshold] = useState("1");
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (tickers?.length) setTicker(tickers[0]); }, [tickers]);

  const submit = async () => {
    if (!ticker) { toast.error("Bir hisse seçin"); return; }
    const t = Number(threshold);
    if (!(t > 0 && t <= 100)) { toast.error("Eşik %0 ile %100 arasında olmalı"); return; }
    setBusy(true);
    try {
      await api.post("/alerts", {
        followee_username: followee.username, ticker, direction, threshold_pct: t,
      });
      toast.success(`Uyarı kuruldu: ${followee.display_name} · ${ticker}`);
      onOpenChange(false);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Uyarı kurulamadı");
    }
    setBusy(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-white border border-line rounded-2xl">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2"><Bell size={18} className="text-brand"/> Pozisyon uyarısı kur</DialogTitle>
          <DialogDescription>
            {followee?.display_name} bu hissedeki portföy ağırlığını değiştirdiğinde bildirim alırsın.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div>
            <Label>Hisse</Label>
            <Select value={ticker} onValueChange={setTicker}>
              <SelectTrigger className="rounded-full" data-testid="alert-ticker"><SelectValue placeholder="Beyan edilmiş pozisyonlardan seçin"/></SelectTrigger>
              <SelectContent>
                {(tickers || []).map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
              </SelectContent>
            </Select>
            {(!tickers || tickers.length === 0) && (
              <p className="text-xs text-mute mt-1">Bu yaratıcının henüz açıkladığı bir pozisyon yok.</p>
            )}
          </div>

          <div>
            <Label>Yön</Label>
            <div className="mt-1 grid grid-cols-3 gap-2">
              {[
                { v: "any", l: "Herhangi", i: <ArrowUpDown size={14}/> },
                { v: "increase", l: "Artış", i: <TrendingUp size={14} className="text-pos"/> },
                { v: "decrease", l: "Azalış", i: <TrendingDown size={14} className="text-neg"/> },
              ].map(o => (
                <button key={o.v} type="button" onClick={()=>setDirection(o.v)}
                  className={`inline-flex items-center justify-center gap-1.5 h-9 rounded-full border text-sm font-medium transition-colors ${direction===o.v ? "bg-ink text-white border-ink" : "bg-white text-ink border-line hover:bg-surface"}`}
                  data-testid={`alert-dir-${o.v}`}>
                  {o.i} {o.l}
                </button>
              ))}
            </div>
          </div>

          <div>
            <Label>Eşik (%)</Label>
            <Input type="number" step="0.1" min="0.1" max="100" value={threshold} onChange={(e)=>setThreshold(e.target.value)} data-testid="alert-threshold"/>
            <p className="text-xs text-mute mt-1">Örn: %1 → yaratıcı bu hissedeki pozisyon ağırlığını 1 puan artırdığında/azalttığında bildirim gelir.</p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" className="rounded-full border-line" onClick={()=>onOpenChange(false)}>Vazgeç</Button>
          <Button className="rounded-full bg-brand hover:bg-brand/90 text-white" onClick={submit} disabled={busy} data-testid="alert-submit">
            {busy ? "Kaydediliyor…" : "Uyarı kur"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
