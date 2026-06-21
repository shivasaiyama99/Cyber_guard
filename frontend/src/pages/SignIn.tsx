import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { signin } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Shield, Lock, Mail, KeyRound } from "lucide-react";
import { toast } from "sonner";

export default function SignIn() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Please fill in all fields");
      return;
    }

    setIsLoading(true);
    try {
      // 1. Check local users database in browser's localStorage
      const localUsersRaw = localStorage.getItem("cyberguard_local_users");
      const localUsers = localUsersRaw ? JSON.parse(localUsersRaw) : [];
      
      // Default administrator account fallback
      const defaultAdmin = {
        name: "SOC Administrator",
        email: "admin@cyberguard.com",
        password: "admin"
      };

      const allUsers = [...localUsers, defaultAdmin];
      const matchedUser = allUsers.find(
        (u: any) => u.email.toLowerCase() === email.toLowerCase()
      );

      if (!matchedUser) {
        throw new Error("Invalid email or password");
      }

      if (matchedUser.password !== password) {
        throw new Error("Invalid email or password");
      }

      // 2. Fetch signed JWT token from the backend
      const data = await signin({ email, password });
      
      // 3. Log in via AuthContext
      login(data.token, {
        name: matchedUser.name,
        email: matchedUser.email,
        role: data.role || "analyst",
        profilePicture: data.profilePicture || "",
        authProvider: "local",
      });

      toast.success(`Welcome back, ${matchedUser.name}!`);
      navigate("/dashboard");
    } catch (err: any) {
      toast.error(err.message || "Invalid credentials");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Video Background */}
      <video
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 w-full h-full object-cover opacity-90 contrast-125 brightness-110"
        aria-hidden="true"
      >
        <source src="https://assets.mixkit.co/videos/preview/mixkit-abstract-technology-world-map-loop-42352-large.mp4" type="video/mp4" />
      </video>

      {/* Background effects */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#080b14]/60 via-[#080b14]/30 to-[#080b14] pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-r from-blue-900/10 via-transparent to-purple-900/10 pointer-events-none" />
      <div className="absolute top-1/3 left-1/4 w-[400px] h-[400px] rounded-full bg-cyan-600/5 blur-[100px] pointer-events-none" />

      <div className="relative w-full max-w-md bg-slate-900/90 backdrop-blur-xl p-8 rounded-2xl border border-slate-800/80 shadow-2xl shadow-black/80 flex flex-col">
        <div className="mb-6 text-center flex flex-col items-center">
          <div className="w-14 h-14 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mb-4 animate-pulse">
            <Shield className="w-7 h-7 text-cyan-400" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Security Portal</h1>
          <p className="text-gray-400 text-sm">Access the Cyberguard SOC Platform</p>
        </div>

        {/* Demo credentials tip */}
        <div className="w-full bg-slate-950/60 rounded-xl p-3 border border-slate-800/60 mb-6 text-xs text-gray-400">
          <div className="font-semibold text-cyan-400 mb-1 flex items-center gap-1">
            <Lock className="w-3.5 h-3.5" />
            Quick Access Demo Account:
          </div>
          <div className="flex justify-between">
            <span>Email: <code className="text-gray-200">admin@cyberguard.com</code></span>
            <span>Password: <code className="text-gray-200">admin</code></span>
          </div>
        </div>

        <form onSubmit={handleSignIn} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="email" className="text-gray-300 text-sm font-medium">Email Address</Label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-3 h-4.5 w-4.5 text-gray-500" />
              <Input
                id="email"
                type="email"
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="pl-11 bg-slate-950/50 border-slate-800 text-white placeholder:text-gray-600 focus:border-cyan-500 focus:ring-cyan-500/20"
                disabled={isLoading}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="password" className="text-gray-300 text-sm font-medium">Password</Label>
            <div className="relative">
              <KeyRound className="absolute left-3.5 top-3 h-4.5 w-4.5 text-gray-500" />
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="pl-11 bg-slate-950/50 border-slate-800 text-white placeholder:text-gray-600 focus:border-cyan-500 focus:ring-cyan-500/20"
                disabled={isLoading}
              />
            </div>
          </div>

          <Button
            type="submit"
            className="w-full h-11 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold transition-colors mt-2"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin text-white" />
                Authenticating...
              </>
            ) : (
              "Sign In to Console"
            )}
          </Button>
        </form>

        <p className="text-center text-sm text-gray-400 mt-6">
          New analyst?{" "}
          <Link to="/signup" className="text-cyan-400 hover:text-cyan-300 font-medium transition-colors">
            Register Account
          </Link>
        </p>
      </div>
    </div>
  );
}
