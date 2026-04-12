import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Register from "./pages/Register";
import type { ReactNode } from "react";

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="loading">Se incarca...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function Placeholder({ title }: { title: string }) {
  return (
    <div style={{ padding: "2rem" }}>
      <h1>{title}</h1>
      <p>In constructie.</p>
    </div>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Placeholder title="Dashboard" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/quiz/setup"
        element={
          <ProtectedRoute>
            <Placeholder title="Quiz Setup" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/quiz/config"
        element={
          <ProtectedRoute>
            <Placeholder title="Quiz Config" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/quiz/:sessionId"
        element={
          <ProtectedRoute>
            <Placeholder title="Quiz" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/quiz/:sessionId/results"
        element={
          <ProtectedRoute>
            <Placeholder title="Results" />
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
