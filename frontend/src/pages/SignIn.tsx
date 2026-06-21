import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { googleLogin } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { GoogleLogin } from "@react-oauth/google";
import { Button } from "@/components/ui/button";
import { Loader2, Shield, Lock } from "lucide-react";
import { toast } from "sonner";

export default function SignIn() {
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleGoogleSuccess = async (tokenResponse: any) => {
    setIsGoogleLoading(true);
    try {
      const idToken = tokenResponse.credential;
      const data = await googleLogin(idToken);
      login(data.token, {
        name: data.name,
        email: data.email,
        role: data.role,
        profilePicture: data.profilePicture,
        authProvider: "google",
      });
      toast.success("Successfully signed in with Google");
      navigate("/dashboard");
    } catch (err: any) {
      toast.error(err.message || "Google sign-in failed");
    } finally {
      setIsGoogleLoading(false);
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
      <div className="absolute inset-0 bg-gradient-to-b from-[#080b14]/50 via-[#080b14]/20 to-[#080b14] pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-r from-blue-900/10 via-transparent to-purple-900/10 pointer-events-none" />
      <div className="absolute top-1/3 left-1/4 w-[400px] h-[400px] rounded-full bg-cyan-600/5 blur-[100px] pointer-events-none" />

      <div className="relative w-full max-w-md bg-slate-900/90 backdrop-blur-xl p-8 rounded-2xl border border-slate-800/80 shadow-2xl shadow-black/80 flex flex-col items-center">
        <div className="mb-8 text-center flex flex-col items-center">
          <div className="w-14 h-14 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mb-4 animate-pulse">
            <Shield className="w-7 h-7 text-cyan-400" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Welcome Back</h1>
          <p className="text-gray-400 text-sm">Access the Cyberguard SOC Platform</p>
        </div>

        {/* Info card */}
        <div className="w-full bg-slate-950/50 rounded-xl p-4 border border-slate-800/50 mb-6 text-center text-xs text-gray-400 flex items-center gap-2 justify-center">
          <Lock className="w-4 h-4 text-cyan-400 flex-shrink-0" />
          <span>Secured by Google OAuth 2.0 SSO</span>
        </div>

        {/* Google Sign-In */}
        <div className="w-full flex justify-center mb-6">
          {isGoogleLoading ? (
            <Button disabled className="w-full h-11 bg-slate-950 border border-slate-800 text-gray-300">
              <Loader2 className="mr-2 h-4 w-4 animate-spin text-cyan-400" />
              Verifying credentials...
            </Button>
          ) : (
            <div className="w-full [&>div]:!w-full [&_iframe]:!w-full flex justify-center">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => toast.error("Google authentication failed")}
                theme="filled_black"
                size="large"
                width="340"
                text="signin_with"
                shape="rectangular"
              />
            </div>
          )}
        </div>

        <p className="text-center text-sm text-gray-400">
          New to the platform?{" "}
          <Link to="/signup" className="text-cyan-400 hover:text-cyan-300 font-medium transition-colors">
            Create Account
          </Link>
        </p>
      </div>
    </div>
  );
}
