import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import type { User } from "../types";
import * as authApi from "../api";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, inviteCode: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem("grile_token")
  );
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    authApi
      .getMe()
      .then((u) => {
        setUser(u);
      })
      .catch(() => {
        authApi.clearToken();
        setToken(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, [token]);

  const login = useCallback(
    async (username: string, password: string) => {
      const res = await authApi.login(username, password);
      authApi.setToken(res.token);
      setToken(res.token);
      setUser(res.user);
      navigate("/dashboard");
    },
    [navigate]
  );

  const register = useCallback(
    async (username: string, password: string, inviteCode: string) => {
      const res = await authApi.register(username, password, inviteCode);
      authApi.setToken(res.token);
      setToken(res.token);
      setUser(res.user);
      navigate("/dashboard");
    },
    [navigate]
  );

  const logout = useCallback(() => {
    authApi.clearToken();
    setToken(null);
    setUser(null);
    navigate("/login");
  }, [navigate]);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
