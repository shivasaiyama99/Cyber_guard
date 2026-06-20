import React, { createContext, useContext, useEffect, useState } from "react";
import { isTokenValid } from "@/lib/api";

interface User {
  name: string;
  email: string;
  role?: string;
  profilePicture?: string;
  authProvider?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string, user: User) => void;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      setIsLoading(true);
      const valid = isTokenValid();
      if (valid) {
        const storedToken = localStorage.getItem("cyberguard_token");
        const storedUser = localStorage.getItem("cyberguard_user");
        if (storedToken && storedUser) {
          setToken(storedToken);
          setUser(JSON.parse(storedUser));
        }
      } else {
        localStorage.removeItem("cyberguard_token");
        localStorage.removeItem("cyberguard_user");
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  const login = (newToken: string, newUser: User) => {
    localStorage.setItem("cyberguard_token", newToken);
    localStorage.setItem("cyberguard_user", JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
  };

  const logout = () => {
    const tok = localStorage.getItem("cyberguard_token");
    if (tok) {
      fetch(
        `${(import.meta as any).env?.VITE_API_BASE_URL ?? "http://localhost:8000"}/auth/logout`,
        { method: "POST", headers: { Authorization: `Bearer ${tok}` } }
      ).catch(() => {});
    }
    localStorage.removeItem("cyberguard_token");
    localStorage.removeItem("cyberguard_user");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        logout,
        isAuthenticated: !!token,
        isLoading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};


export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
