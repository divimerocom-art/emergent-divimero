import axios from "axios";

const BACKEND = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND}/api`;

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const t = localStorage.getItem("divimero_token");
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

export function formatApiError(detail) {
  if (detail == null) return "Bir hata oluştu.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export const money = (v, opts = {}) =>
  new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY", maximumFractionDigits: 2, ...opts }).format(Number(v || 0));

export const pct = (v) => `%${Number(v || 0).toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
export const num = (v, d = 2) => Number(v || 0).toLocaleString("tr-TR", { minimumFractionDigits: d, maximumFractionDigits: d });

// Turkish possessive suffix for a number, chosen by the last word of how it is read:
// 50 "elli" -> 'si, 53 "elli üç" -> 'ü, 100 "yüz" -> 'ü, 1000 "bin" -> 'i.
const ONES_SUFFIX = ["", "i", "si", "ü", "ü", "i", "sı", "si", "i", "u"];
const TENS_SUFFIX = ["", "u", "si", "u", "ı", "si", "ı", "i", "i", "ı"];
export function numSuffix(n) {
  const v = Math.abs(Math.round(Number(n) || 0));
  if (v % 10) return ONES_SUFFIX[v % 10];
  if (v % 100) return TENS_SUFFIX[(v % 100) / 10];
  if (v % 1000) return "ü";
  return v ? "i" : "ı";
}

// Privacy-safe relative magnitude: a share of the position at publication, never a
// quantity or a value. The backend already rounds it to a whole percent.
export const positionShare = (n) => `pozisyonun ~%${n}'${numSuffix(n)}`;

export function relTime(iso) {
  const t = new Date(iso).getTime();
  const diff = Math.max(0, Date.now() - t);
  const m = Math.floor(diff / 60000);
  if (m < 1) return "az önce";
  if (m < 60) return `${m} dk`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} sa`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d} gün`;
  return new Date(iso).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" });
}
