import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

const TYPES = [
  { v:"buy", l:"Alım" }, { v:"sell", l:"Satım" },
  { v:"deposit", l:"Nakit Yatırma" }, { v:"withdraw", l:"Nakit Çekme" },
  { v:"dividend", l:"Temettü" },
];

export default function TransactionNew() {
  const nav = useNavigate();
  const [tickers, setTickers] = useState([]);
  const [f, setF] = useState({
    type: "buy", ticker: "", quantity: "", price: "", fees: "0", amount: "",
    date: new Date().toISOString().slice(0,10), note: "",
  });
  useEffect(() => { api.get("/market/tickers").then(r => setTickers(r.data)); }, []);

  const upd = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const needsTicker = ["buy","sell","dividend"].includes(f.type);
  const needsQty = ["buy","sell"].includes(f.type);
  const needsAmount = ["deposit","withdraw","dividend"].includes(f.type);

  const submit = async (e) => {
    e.preventDefault();
    const payload = {
      type: f.type,
      ticker: needsTicker ? f.ticker : null,
      date: new Date(f.date + "T10:00:00Z").toISOString(),
      quantity: needsQty ? Number(f.quantity || 0) : 0,
      price: needsQty ? Number(f.price || 0) : 0,
      fees: Number(f.fees || 0),
      amount: needsAmount ? Number(f.amount || 0) : (needsQty ? Number(f.quantity||0) * Number(f.price||0) : 0),
      note: f.note,
    };
    try {
      await api.post("/portfolio/transactions", payload);
      toast.success("İşlem kaydedildi");
      nav("/portfolio");
    } catch (e) { toast.error(e.response?.data?.detail || "Kaydedilemedi"); }
  };

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="font-heading text-2xl md:text-3xl font-bold tracking-tight">Yeni işlem</h1>
      <p className="text-sm text-mute mt-1">BIST — TRY bazında portföyünüze işlem ekleyin.</p>

      <form onSubmit={submit} className="mt-6 rounded-2xl border border-line bg-white p-5 space-y-4">
        <div>
          <Label>İşlem türü</Label>
          <Select value={f.type} onValueChange={(v)=>upd("type", v)}>
            <SelectTrigger data-testid="tx-type" className="rounded-full"><SelectValue/></SelectTrigger>
            <SelectContent>{TYPES.map(t => <SelectItem key={t.v} value={t.v}>{t.l}</SelectItem>)}</SelectContent>
          </Select>
        </div>

        {needsTicker && (
          <div>
            <Label>Hisse</Label>
            <Select value={f.ticker} onValueChange={(v)=>upd("ticker", v)}>
              <SelectTrigger data-testid="tx-ticker" className="rounded-full"><SelectValue placeholder="Bir sembol seçin"/></SelectTrigger>
              <SelectContent>{tickers.map(t => <SelectItem key={t.symbol} value={t.symbol}>{t.symbol} — {t.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        )}

        {needsQty && (
          <div className="grid grid-cols-2 gap-3">
            <div><Label>Adet</Label><Input value={f.quantity} onChange={(e)=>upd("quantity", e.target.value)} type="number" step="any" min="0" required data-testid="tx-quantity"/></div>
            <div><Label>Birim Fiyat (TRY)</Label><Input value={f.price} onChange={(e)=>upd("price", e.target.value)} type="number" step="any" min="0" required data-testid="tx-price"/></div>
          </div>
        )}

        {needsAmount && (
          <div><Label>Tutar (TRY)</Label><Input value={f.amount} onChange={(e)=>upd("amount", e.target.value)} type="number" step="any" min="0" required data-testid="tx-amount"/></div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div><Label>Tarih</Label><Input value={f.date} onChange={(e)=>upd("date", e.target.value)} type="date" required data-testid="tx-date"/></div>
          {needsQty && <div><Label>Komisyon (opsiyonel)</Label><Input value={f.fees} onChange={(e)=>upd("fees", e.target.value)} type="number" step="any" min="0" data-testid="tx-fees"/></div>}
        </div>

        <div><Label>Not (opsiyonel)</Label><Textarea value={f.note} onChange={(e)=>upd("note", e.target.value)} rows={2} data-testid="tx-note"/></div>

        <div className="flex gap-2 pt-2">
          <Button type="button" variant="outline" className="rounded-full border-line" onClick={()=>nav(-1)}>Vazgeç</Button>
          <Button type="submit" className="flex-1 rounded-full bg-brand hover:bg-brand/90 text-white" data-testid="tx-submit">Kaydet</Button>
        </div>
      </form>
    </div>
  );
}
