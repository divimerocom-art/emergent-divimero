import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { toast } from "sonner";
import { Camera, ArrowRight, Check } from "lucide-react";

export default function Onboarding() {
  const { user, setUser } = useAuth();
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [f, setF] = useState({ display_name: user?.display_name || "", bio: user?.bio || "", avatar_url: user?.avatar_url || "" });
  const [uploading, setUploading] = useState(false);

  const pickAvatar = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    if (file.size > 8 * 1024 * 1024) { toast.error("Görsel 8 MB'ı aşamaz"); return; }
    setUploading(true);
    try {
      const form = new FormData(); form.append("file", file);
      const { data } = await api.post("/uploads", form, { headers: { "Content-Type": "multipart/form-data" } });
      const backend = process.env.REACT_APP_BACKEND_URL;
      setF((x) => ({ ...x, avatar_url: `${backend}${data.url}` }));
    } catch (er) { toast.error("Yükleme başarısız"); }
    setUploading(false);
  };

  const save = async () => {
    try {
      const { data } = await api.patch("/auth/me", f);
      setUser(data);
      toast.success("Profil kaydedildi");
      nav("/feed");
    } catch { toast.error("Kaydedilemedi"); }
  };

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-lg">
        <div className="mb-6">
          <div className="text-xs uppercase tracking-wider text-mute font-semibold">Divimero'ya hoşgeldin</div>
          <h1 className="font-heading text-3xl font-bold mt-1">Profilini birkaç adımda tamamla</h1>
        </div>

        <div className="rounded-2xl border border-line bg-white p-6 space-y-5">
          {step === 0 && (
            <>
              <div className="flex items-center gap-4">
                <Avatar className="h-20 w-20 border border-line">
                  {f.avatar_url && <AvatarImage src={f.avatar_url}/>}
                  <AvatarFallback className="bg-brand-soft text-brand text-2xl font-heading">{(f.display_name||"?").slice(0,1)}</AvatarFallback>
                </Avatar>
                <label className="inline-flex items-center gap-2 h-10 px-4 rounded-full border border-line bg-white cursor-pointer hover:bg-surface transition-colors text-sm" data-testid="pick-avatar">
                  <Camera size={16}/>{uploading ? "Yükleniyor…" : "Profil fotoğrafı seç"}
                  <input type="file" accept="image/*" className="hidden" onChange={pickAvatar}/>
                </label>
              </div>
              <div>
                <Label>Görünen ad</Label>
                <Input value={f.display_name} onChange={(e)=>setF({...f, display_name:e.target.value})} data-testid="ob-name"/>
              </div>
              <div>
                <Label>Kısa biyografi</Label>
                <Textarea value={f.bio} onChange={(e)=>setF({...f, bio:e.target.value})} rows={3} placeholder="Yatırım tarzınız, ilgilendiğiniz sektörler…" data-testid="ob-bio"/>
              </div>
              <div className="flex justify-between pt-2">
                <button onClick={()=>nav("/feed")} className="text-sm text-mute hover:text-ink" data-testid="ob-skip">Sonra yaparım</button>
                <Button onClick={()=>setStep(1)} className="rounded-full bg-ink hover:bg-black text-white" data-testid="ob-next">Devam <ArrowRight size={16} className="ml-1"/></Button>
              </div>
            </>
          )}

          {step === 1 && (
            <>
              <div className="text-sm">
                <div className="font-heading font-semibold text-lg">Portföyün gizli, sen açmadıkça</div>
                <p className="text-mute mt-1">Portföyüne işlem ekleyerek başlayabilir ya da daha sonra ekleyebilirsin. Her paylaşımda pozisyon oranını göstermek zorunda değilsin — kontrol tamamen sende.</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-line p-3">
                  <div className="text-xs uppercase tracking-wider text-mute font-medium">Varsayılan</div>
                  <div className="mt-1 font-heading font-semibold flex items-center gap-1"><Check size={14} className="text-pos"/> Tümü gizli</div>
                </div>
                <div className="rounded-xl border border-line p-3">
                  <div className="text-xs uppercase tracking-wider text-mute font-medium">Paylaşım kontrolü</div>
                  <div className="mt-1 font-heading font-semibold">Her post için ayrı</div>
                </div>
              </div>
              <div className="flex justify-between pt-2">
                <Button variant="outline" className="rounded-full border-line" onClick={()=>setStep(0)}>Geri</Button>
                <div className="flex gap-2">
                  <Button variant="outline" className="rounded-full border-line" onClick={save} data-testid="ob-finish">Kaydet ve akışa git</Button>
                  <Button className="rounded-full bg-brand hover:bg-brand/90 text-white" onClick={async ()=>{await save(); nav("/portfolio/new");}} data-testid="ob-add-tx">İlk işlemi ekle</Button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
