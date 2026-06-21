import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { signin, googleLogin } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { GoogleLogin } from "@react-oauth/google";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Eye, EyeOff, Loader2, Shield } from "lucide-react";
import { toast } from "sonner";

export default function SignIn() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleGoogleSuccess = async (tokenResponse: any) => {
    setIsGoogleLoading(true);
    try {
      // Use the credential (ID token) from Google's response
      const idToken = tokenResponse.credential;
      const data = await googleLogin(idToken);
      login(data.token, {
        name: data.name,
        email: data.email,
        role: data.role,
        profilePicture: data.profilePicture,
        authProvider: "google",
      });
      toast.success("Signed in with Google");
      navigate("/dashboard");
    } catch (err: any) {
      toast.error(err.message || "Google sign-in failed");
    } finally {
      setIsGoogleLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const data = await signin({ email, password });
      login(data.token, { name: data.name, email: data.email, role: data.role });
      toast.success("Successfully signed in");
      navigate("/dashboard");
    } catch (err: any) {
      const msg = err.message || "Failed to sign in";
      try {
        const parsed = JSON.parse(msg);
        toast.error(parsed.detail || msg);
      } catch {
        toast.error(msg);
      }
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
      <div className="absolute inset-0 bg-gradient-to-b from-[#080b14]/40 via-[#080b14]/10 to-[#080b14] pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-r from-blue-900/10 via-transparent to-purple-900/10 pointer-events-none" />
      <div className="absolute top-1/3 left-1/4 w-[400px] h-[400px] rounded-full bg-cyan-600/5 blur-[100px] pointer-events-none" />


      <div className="relative w-full max-w-md bg-[#1f2937] p-8 rounded-2xl border border-gray-700/50 shadow-2xl shadow-black/50">
        <div className="mb-8 text-center">
          <div className="mx-auto w-14 h-14 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mb-4">
            <Shield className="w-7 h-7 text-cyan-400" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Welcome Back</h1>
          <p className="text-gray-400 text-sm">Sign in to Cyberguard</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-gray-300 text-sm">Email</Label>
            <Input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="bg-gray-900/80 border-gray-700 text-white focus-visible:ring-cyan-500 h-11"
              placeholder="analyst@cyberguard.local"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-gray-300 text-sm">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-gray-900/80 border-gray-700 text-white focus-visible:ring-cyan-500 pr-10 h-11"
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox id="remember" className="border-gray-600 data-[state=checked]:bg-cyan-500" />
            <Label htmlFor="remember" className="text-sm text-gray-400 font-normal cursor-pointer">
              Remember me for 30 days
            </Label>
          </div>

          <Button
            type="submit"
            className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-semibold h-11 transition-all duration-200"
            disabled={isLoading || isGoogleLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Signing in...
              </>
            ) : (
              "Sign In"
            )}
          </Button>

          {/* Divider */}
          <div className="relative my-2">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-600" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-[#1f2937] px-3 text-gray-400">or</span>
            </div>
          </div>

          {/* Google Sign-In */}
          <div className="flex justify-center">
            {isGoogleLoading ? (
              <Button disabled className="w-full h-11 bg-gray-800 border border-gray-600 text-gray-300">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Signing in with Google...
              </Button>
            ) : (
              <div className="w-full [&>div]:!w-full [&_iframe]:!w-full">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={() => toast.error("Google sign-in failed")}
                  theme="filled_black"
                  size="large"
                  width="400"
                  text="continue_with"
                  shape="rectangular"
                />
              </div>
            )}
          </div>

          <p className="text-center text-sm text-gray-400">
            Don't have an account?{" "}
            <Link to="/signup" className="text-cyan-500 hover:text-cyan-400 font-medium transition-colors">
              Sign Up
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
