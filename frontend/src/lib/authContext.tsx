"use client";
import React, { createContext, useContext, useEffect, useState } from "react";
import type { User, UserRole } from "@/types";
import { api } from "./api";

const demoAccounts: Record<UserRole, [string, string]> = {
  Administrator: ["alex.vance", "admin123456"],
  "Security Analyst": ["sarah.chen", "analyst123456"],
  User: ["james.wilson", "user123456"],
};
type AuthState = { currentUser: User | null; userRole: UserRole; isAdmin: boolean; isLoading: boolean; login: (role: UserRole, username?: string, password?: string) => Promise<void>; switchRole: (role: UserRole) => Promise<void>; logout: () => void };
const Context = createContext<AuthState | null>(null);
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isLoading, setLoading] = useState(true);
  useEffect(() => { if (api.getToken()) api.getMe().then(setCurrentUser).catch(() => api.setToken(null)).finally(() => setLoading(false)); else setLoading(false); }, []);
  const login = async (role: UserRole, username?: string, password?: string) => {
    const [defaultUser, defaultPass] = demoAccounts[role];
    const result = await api.login(username || defaultUser, password || defaultPass);
    api.setToken(result.access_token);
    setCurrentUser(await api.getMe());
  };
  const userRole = currentUser?.role || "User";
  return <Context.Provider value={{ currentUser, userRole, isAdmin: userRole === "Administrator", isLoading, login, switchRole: (role) => login(role), logout: () => { api.setToken(null); setCurrentUser(null); } }}>{children}</Context.Provider>;
}
export function useAuth() { const context = useContext(Context); if (!context) throw new Error("AuthProvider missing"); return context; }
