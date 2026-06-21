import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { googleLogin } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { GoogleLogin } from "@react-oauth/google";
import { Button } from "@/components/ui/button";
import { Loader2, Shield, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

export default function SignUp() {
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
      toast.success("Successfully registered with Google");
      navigate("/dashboard");
    } catch (err: any) {
      toast.error(err.message || "Google sign-up failed");
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
      <div className="absolute inset-0 bg-gradient-to-r from-purple-900/10 via-transparent to-cyan-900/10 pointer-events-none" />
      <div className="absolute bottom-1/3 right-1/4 w-[400px] h-[400px] rounded-full bg-purple-600/5 blur-[100px] pointer-events-none" />

      <div className="relative w-full max-w-md bg-slate-900/90 backdrop-blur-xl p-8 rounded-2xl border border-slate-800/80 shadow-2xl shadow-black/80 flex flex-col items-center">
        <div className="mb-8 text-center flex flex-col items-center">
          <div className="w-14 h-14 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center mb-4 animate-pulse">
            <Shield className="w-7 h-7 text-purple-400" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Create Account</h1>
          <p className="text-gray-400 text-sm">Join the Cyberguard SOC Platform</p>
        </div>

        {/* Value props list */}
        <div className="w-full space-y-3 mb-6 bg-slate-950/30 p-4 rounded-xl border border-slate-800/30 text-xs text-gray-300">
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

        {/* Google Sign-Up */}
        <div className="w-full flex justify-center mb-6">
          {isGoogleLoading ? (
            <Button disabled className="w-full h-11 bg-slate-950 border border-slate-800 text-gray-300">
              <Loader2 className="mr-2 h-4 w-4 animate-spin text-purple-400" />
              Setting up account...
            </Button>
          ) : (
            <div className="w-full [&>div]:!w-full [&_iframe]:!w-full flex justify-center">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => toast.error("Google authentication failed")}
                theme="filled_black"
                size="large"
                width="340"
                text="signup_with"
                shape="rectangular"
              />
            </div>
          )}
        </div>

        <p className="text-center text-sm text-gray-400">
          Already have an account?{" "}
          <Link to="/signin" className="text-purple-400 hover:text-purple-300 font-medium transition-colors">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}
