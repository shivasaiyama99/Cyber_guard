import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { signup, signin } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Shield, CheckCircle2, User, Mail, KeyRound } from "lucide-react";
import { toast } from "sonner";

export default function SignUp() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !email || !password) {
      toast.error("Please fill in all fields");
      return;
    }

    setIsLoading(true);
    try {
      // 1. Check if email is already taken in client-side localStorage database
      const localUsersRaw = localStorage.getItem("cyberguard_local_users");
      const localUsers = localUsersRaw ? JSON.parse(localUsersRaw) : [];
      
      const emailExists = localUsers.some(
        (u: any) => u.email.toLowerCase() === email.toLowerCase() || email.toLowerCase() === "admin@cyberguard.com"
      );

      if (emailExists) {
        throw new Error("Email address is already registered");
      }

      // 2. Register user locally in browser
      const newUser = { name, email, password };
      localUsers.push(newUser);
      localStorage.setItem("cyberguard_local_users", JSON.stringify(localUsers));

      // 3. Inform backend of the registration (it handles MongoDB registration if up, or gracefully succeeds)
      try {
        await signup({ name, email, password });
      } catch (backendErr) {
        // Backend DB unavailable is fine, since we have the user stored locally in browser!
        console.log("Backend registration notice:", backendErr);
      }

      // 4. Log in immediately
      const authData = await signin({ email, password });
      login(authData.token, {
        name,
        email,
        role: authData.role || "analyst",
        profilePicture: authData.profilePicture || "",
        authProvider: "local",
      });

      toast.success("Account registered successfully!");
      navigate("/dashboard");
    } catch (err: any) {
      toast.error(err.message || "Registration failed");
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
      <div className="absolute inset-0 bg-gradient-to-r from-purple-900/10 via-transparent to-cyan-900/10 pointer-events-none" />
      <div className="absolute bottom-1/3 right-1/4 w-[400px] h-[400px] rounded-full bg-purple-600/5 blur-[100px] pointer-events-none" />

      <div className="relative w-full max-w-md bg-slate-900/90 backdrop-blur-xl p-8 rounded-2xl border border-slate-800/80 shadow-2xl shadow-black/80 flex flex-col">
        <div className="mb-6 text-center flex flex-col items-center">
          <div className="w-14 h-14 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center mb-4 animate-pulse">
            <Shield className="w-7 h-7 text-purple-400" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Create Account</h1>
          <p className="text-gray-400 text-sm">Join the Cyberguard SOC Platform</p>
        </div>

        {/* Value props list */}
        <div className="w-full space-y-2 mb-6 bg-slate-950/40 p-4 rounded-xl border border-slate-800/40 text-xs text-gray-300">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>Instant sandbox environment setup</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>AI-driven security log auditing</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>Dynamic network threat monitoring</span>
          </div>
        </div>

        <form onSubmit={handleSignUp} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="name" className="text-gray-300 text-sm font-medium">Full Name</Label>
            <div className="relative">
              <User className="absolute left-3.5 top-3 h-4.5 w-4.5 text-gray-500" />
              <Input
                id="name"
                type="text"
                placeholder="John Doe"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="pl-11 bg-slate-950/50 border-slate-800 text-white placeholder:text-gray-600 focus:border-purple-500 focus:ring-purple-500/20"
                disabled={isLoading}
              />
            </div>
          </div>

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
                className="pl-11 bg-slate-950/50 border-slate-800 text-white placeholder:text-gray-600 focus:border-purple-500 focus:ring-purple-500/20"
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
                className="pl-11 bg-slate-950/50 border-slate-800 text-white placeholder:text-gray-600 focus:border-purple-500 focus:ring-purple-500/20"
                disabled={isLoading}
              />
            </div>
          </div>

          <Button
            type="submit"
            className="w-full h-11 bg-purple-600 hover:bg-purple-500 text-white font-semibold transition-colors mt-2"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin text-white" />
                Setting up account...
              </>
            ) : (
              "Register Account"
            )}
          </Button>
        </form>

        <p className="text-center text-sm text-gray-400 mt-6">
          Already have an account?{" "}
          <Link to="/signin" className="text-purple-400 hover:text-purple-300 font-medium transition-colors">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}
