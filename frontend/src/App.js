import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import AppShell from "@/components/AppShell";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Feed from "@/pages/Feed";
import Portfolio from "@/pages/Portfolio";
import Profile from "@/pages/Profile";
import Compose from "@/pages/Compose";
import TransactionNew from "@/pages/TransactionNew";
import PostDetail from "@/pages/PostDetail";
import Onboarding from "@/pages/Onboarding";
import Alerts from "@/pages/Alerts";

function Private({ children }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <div className="p-10 text-mute">Yükleniyor…</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  return children;
}

function AppRoutes() {
  const { user, loading } = useAuth();
  return (
    <Routes>
      <Route path="/" element={loading ? <div className="p-10 text-mute">Yükleniyor…</div> : (user ? <Navigate to="/feed" replace /> : <Landing />)} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route path="/feed" element={<Private><AppShell><Feed /></AppShell></Private>} />
      <Route path="/onboarding" element={<Private><Onboarding /></Private>} />
      <Route path="/portfolio" element={<Private><AppShell><Portfolio /></AppShell></Private>} />
      <Route path="/portfolio/new" element={<Private><AppShell><TransactionNew /></AppShell></Private>} />
      <Route path="/alerts" element={<Private><AppShell><Alerts /></AppShell></Private>} />
      <Route path="/compose" element={<Private><AppShell><Compose /></AppShell></Private>} />
      <Route path="/u/:username" element={<AppShell><Profile /></AppShell>} />
      <Route path="/p/:postId" element={<AppShell><PostDetail /></AppShell>} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
          <Toaster position="top-center" richColors closeButton />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}
