import { useEffect, useState } from "react";
import { api, pct } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Lock, TrendingUp, Image as ImageIcon, Video as VideoIcon, X, Info } from "lucide-react";
import InstrumentPicker from "@/components/InstrumentPicker";

export default function Compose() {
  const nav = useNavigate();
  const [portfolio, setPortfolio] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [f, setF] = useState({
    text: "", tickers: [],
    image_url: "",
    video_url: "",
    attach_position: false,
    disclosure_ticker: "",
    show_allocation: true,
    allocation_mode: "exact",
    show_quantity: false,
    show_value: false,
  });
  const [tagPickerOpen, setTagPickerOpen] = useState(false);
  const [tagDraft, setTagDraft] = useState("");

  useEffect(() => {
    api.get("/portfolio").then(r => setPortfolio(r.data)).catch(()=>{});
  }, []);

  const upd = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const heldTickers = portfolio?.holdings?.map(h => h.ticker) || [];
  const previewAlloc = portfolio?.holdings?.find(h => h.ticker === f.disclosure_ticker)?.allocation_pct;

  // Auto-suggest: when a user tags a ticker they currently hold, auto-select it as the disclosure candidate
  useEffect(() => {
    if (!f.attach_position) return;
    if (f.disclosure_ticker) return;
    const firstHeld = (f.tickers || []).find(t => heldTickers.includes(t));
    if (firstHeld) upd("disclosure_ticker", firstHeld);
  }, [f.tickers, f.attach_position, heldTickers.join(",")]); // eslint-disable-line

  const submit = async (e) => {
    e.preventDefault();
    const payload = {
      ...f,
      tickers: (f.tickers || []).filter(Boolean),
      image_url: f.image_url || null,
      video_url: f.video_url || null,
      disclosure_ticker: f.attach_position ? f.disclosure_ticker : null,
    };
    if (payload.attach_position && !payload.disclosure_ticker) {
      toast.error("Portföye eklemek için bir hisse seçin"); return;
    }
    try {
      const { data } = await api.post("/posts", payload);
      toast.success("Gönderi yayınlandı");
      nav(`/p/${data.id}`);
    } catch (e) { toast.error(e.response?.data?.detail || "Yayınlanamadı"); }
  };

  const addTag = (sym) => {
    setF((x) => {
      if (x.tickers.includes(sym) || x.tickers.length >= 5) return x;
      return { ...x, tickers: [...x.tickers, sym] };
    });
    setTagPickerOpen(false); setTagDraft("");
  };
  const removeTag = (sym) => setF((x) => ({ ...x, tickers: x.tickers.filter(t => t !== sym) }));

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="font-heading text-2xl md:text-3xl font-bold tracking-tight">Yeni gönderi</h1>
      <p className="text-sm text-mute mt-1">Yatırım fikrinizi paylaşın. İsterseniz portföyünüzdeki pozisyon oranınızı da ekleyin.</p>

      <form onSubmit={submit} className="mt-6 rounded-2xl border border-line bg-white p-5 space-y-5">
        <div>
          <Label>Metin</Label>
          <Textarea value={f.text} onChange={(e)=>upd("text", e.target.value)} rows={5} required placeholder="Tezinizi kısa ve net yazın…" data-testid="post-text"/>
        </div>

        <div>
          <Label>Hisse etiketleri (opsiyonel, en fazla 5)</Label>
          <div className="mt-2 flex flex-wrap gap-2 items-center">
            {f.tickers.map((sym) => (
              <span key={sym} className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-heading font-semibold bg-violet text-white" data-testid={`tag-${sym}`}>
                ${sym}
                <button type="button" onClick={()=>removeTag(sym)} className="hover:bg-white/20 rounded-full p-0.5"><X size={12}/></button>
              </span>
            ))}
            {f.tickers.length < 5 && (
              tagPickerOpen ? (
                <div className="w-full sm:w-72">
                  <InstrumentPicker value="" onChange={addTag} testIdPrefix="tag-pick" placeholder="Hisse ara ve etiketle…"/>
                </div>
              ) : (
                <button type="button" onClick={()=>setTagPickerOpen(true)} className="text-xs px-2.5 py-1 rounded-full border border-dashed border-line text-mute hover:bg-surface" data-testid="tag-add">
                  + Hisse etiketi ekle
                </button>
              )
            )}
          </div>
        </div>

        <div>
          <Label>Medya (opsiyonel)</Label>
          <div className="mt-2 flex flex-wrap gap-2">
            <label className={`inline-flex items-center gap-2 h-9 px-3 rounded-full border border-line bg-white cursor-pointer hover:bg-surface transition-colors text-sm ${uploading?"opacity-60":""}`} data-testid="upload-image">
              <ImageIcon size={16} className="text-brand"/> Görsel yükle
              <input type="file" accept="image/*" className="hidden" onChange={async (e)=>{
                const file = e.target.files?.[0]; if (!file) return;
                if (file.size > 8*1024*1024) { toast.error("Görsel 8 MB'ı aşamaz"); return; }
                setUploading(true);
                try {
                  const form = new FormData(); form.append("file", file);
                  const { data } = await api.post("/uploads", form, { headers: { "Content-Type": "multipart/form-data" } });
                  const url = `${process.env.REACT_APP_BACKEND_URL}${data.url}`;
                  upd("image_url", url);
                } catch { toast.error("Yükleme başarısız"); }
                setUploading(false);
              }}/>
            </label>
            <label className={`inline-flex items-center gap-2 h-9 px-3 rounded-full border border-line bg-white cursor-pointer hover:bg-surface transition-colors text-sm ${uploading?"opacity-60":""}`} data-testid="upload-video">
              <VideoIcon size={16} className="text-violet"/> Video yükle (≤ 60 MB)
              <input type="file" accept="video/mp4,video/webm,video/quicktime" className="hidden" onChange={async (e)=>{
                const file = e.target.files?.[0]; if (!file) return;
                if (file.size > 60*1024*1024) { toast.error("Video 60 MB'ı aşamaz"); return; }
                setUploading(true);
                try {
                  const form = new FormData(); form.append("file", file);
                  const { data } = await api.post("/uploads", form, { headers: { "Content-Type": "multipart/form-data" } });
                  const url = `${process.env.REACT_APP_BACKEND_URL}${data.url}`;
                  upd("video_url", url);
                } catch { toast.error("Yükleme başarısız"); }
                setUploading(false);
              }}/>
            </label>
            {uploading && <span className="text-xs text-mute self-center">Yükleniyor…</span>}
          </div>
          {f.image_url && (
            <div className="mt-2 relative inline-block">
              <img src={f.image_url} alt="" className="max-h-40 rounded-lg border border-line"/>
              <button type="button" onClick={()=>upd("image_url","")} className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-white border border-line flex items-center justify-center"><X size={12}/></button>
            </div>
          )}
          {f.video_url && (
            <div className="mt-2 relative inline-block">
              <video src={f.video_url} className="max-h-40 rounded-lg border border-line" controls playsInline/>
              <button type="button" onClick={()=>upd("video_url","")} className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-white border border-line flex items-center justify-center"><X size={12}/></button>
            </div>
          )}
        </div>

        {/* Portfolio disclosure section */}
        <div className="rounded-2xl border border-line bg-surface p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="font-heading font-semibold flex items-center gap-2"><TrendingUp size={16} className="text-brand"/> Portföyü ekle</div>
              <div className="text-xs text-mute mt-0.5">Bu hissede kendi pozisyonunuzu şeffaf biçimde paylaşın. Adet ve tutar varsayılan olarak gizlidir.</div>
            </div>
            <Switch checked={f.attach_position} onCheckedChange={(v)=>upd("attach_position", v)} data-testid="switch-attach"/>
          </div>

          {f.attach_position && (
            <div className="mt-4 space-y-3">
              <div>
                <Label>Portföydeki hisse</Label>
                <InstrumentPicker
                  value={f.disclosure_ticker}
                  onChange={(v)=>upd("disclosure_ticker", v)}
                  restrictTo={heldTickers}
                  testIdPrefix="disc-inst"
                  placeholder="Portföyünüzden bir hisse seçin"
                />
                {heldTickers.length === 0 && (
                  <p className="text-xs text-mute mt-1.5 inline-flex items-center gap-1"><Info size={12}/> Portföyünüzde hisse yok. Önce bir alım işlemi ekleyin.</p>
                )}
                {f.tickers.includes(f.disclosure_ticker) && heldTickers.includes(f.disclosure_ticker) && (
                  <p className="text-xs text-brand mt-1.5 inline-flex items-center gap-1"><Info size={12}/> Etiketlediğiniz hisseyi tanıdık — bu pozisyonu paylaşacaksınız.</p>
                )}
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">Ağırlık (%) paylaş</div>
                  <div className="text-xs text-mute">Portföyünüzdeki oran</div>
                </div>
                <Switch checked={f.show_allocation} onCheckedChange={(v)=>upd("show_allocation", v)} data-testid="switch-alloc"/>
              </div>

              {f.show_allocation && (
                <div>
                  <Label>Ağırlık modu</Label>
                  <Select value={f.allocation_mode} onValueChange={(v)=>upd("allocation_mode", v)}>
                    <SelectTrigger className="rounded-full" data-testid="alloc-mode"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="exact">Kesin oran</SelectItem>
                      <SelectItem value="range">Aralık</SelectItem>
                      <SelectItem value="hidden">Gizle</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}

              <div className="flex items-center justify-between">
                <div className="text-sm font-medium inline-flex items-center gap-1.5"><Lock size={14} className="text-mute"/> Adet paylaş</div>
                <Switch checked={f.show_quantity} onCheckedChange={(v)=>upd("show_quantity", v)} data-testid="switch-qty"/>
              </div>
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium inline-flex items-center gap-1.5"><Lock size={14} className="text-mute"/> Tutar paylaş</div>
                <Switch checked={f.show_value} onCheckedChange={(v)=>upd("show_value", v)} data-testid="switch-value"/>
              </div>

              {previewAlloc != null && (
                <div className="rounded-xl bg-white border border-line p-3 flex items-center justify-between">
                  <div className="text-xs text-mute">Önizleme</div>
                  <div className="font-heading text-lg font-bold tabular">
                    {f.show_allocation
                      ? (f.allocation_mode === "hidden" ? "Gizli" : (f.allocation_mode === "exact" ? pct(previewAlloc) : "%1-3 (örnek)"))
                      : <span className="text-mute text-sm inline-flex items-center gap-1"><Lock size={12}/> Gizli</span>}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex gap-2">
          <Button type="button" variant="outline" className="rounded-full border-line" onClick={()=>nav(-1)}>Vazgeç</Button>
          <Button type="submit" className="flex-1 rounded-full bg-ink hover:bg-black text-white" data-testid="post-submit">Yayınla</Button>
        </div>
        <p className="text-[11px] text-mute">Divimero bilgilendirme amaçlıdır, yatırım tavsiyesi değildir.</p>
      </form>
    </div>
  );
}
