import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { signup, googleLogin } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { GoogleLogin } from "@react-oauth/google";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Eye, EyeOff, Loader2, CheckCircle2, Shield } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export default function SignUp() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
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
      toast.success("Signed in with Google");
      navigate("/dashboard");
    } catch (err: any) {
      toast.error(err.message || "Google sign-in failed");
    } finally {
      setIsGoogleLoading(false);
    }
  };

  const isEmailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  const isPasswordValid = password.length >= 8;
  const passwordsMatch = password === confirmPassword && password.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isEmailValid) return toast.error("Invalid email format");
    if (!isPasswordValid) return toast.error("Password must be at least 8 characters");
    if (!passwordsMatch) return toast.error("Passwords must match");

    setIsLoading(true);
    try {
      await signup({ name, email, password });
      toast.success("Account created successfully. Please sign in.");
      navigate("/signin");
    } catch (err: any) {
      const msg = err.message || "Failed to create account";
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

  const getStrengthIndicator = () => {
    let score = 0;
    if (password.length >= 8) score += 1;
    if (/[A-Z]/.test(password)) score += 1;
    if (/[0-9]/.test(password)) score += 1;
    if (/[^a-zA-Z0-9]/.test(password)) score += 1;

    let color = "bg-gray-700";
    let text = "Too Weak";
    if (score === 2) { color = "bg-yellow-500"; text = "Fair"; }
    else if (score === 3) { color = "bg-cyan-400"; text = "Good"; }
    else if (score === 4) { color = "bg-emerald-500"; text = "Strong"; }

    return { score, color, text };
  };

  const strength = getStrengthIndicator();

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
        <source src="/bg_video.mp4" type="video/mp4" />
      </video>

      {/* Background effects */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#080b14]/40 via-[#080b14]/10 to-[#080b14] pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-r from-purple-900/10 via-transparent to-cyan-900/10 pointer-events-none" />
      <div className="absolute bottom-1/3 right-1/4 w-[400px] h-[400px] rounded-full bg-purple-600/5 blur-[100px] pointer-events-none" />


      <div className="relative w-full max-w-md bg-[#1f2937] p-8 rounded-2xl border border-gray-700/50 shadow-2xl shadow-black/50">
        <div className="mb-8 text-center">
          <div className="mx-auto w-14 h-14 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center mb-4">
            <Shield className="w-7 h-7 text-purple-400" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Create Account</h1>
          <p className="text-gray-400 text-sm">Join Cyberguard Platform</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="name" className="text-gray-300 text-sm">Full Name</Label>
            <Input
              id="name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="bg-gray-900/80 border-gray-700 text-white focus-visible:ring-cyan-500 h-11"
              placeholder="John Doe"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email" className="text-gray-300 text-sm">Email</Label>
            <Input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={cn(
                "bg-gray-900/80 text-white focus-visible:ring-cyan-500 h-11 transition-colors",
                email && !isEmailValid ? "border-red-500" : "border-gray-700"
              )}
              placeholder="analyst@cyberguard.local"
            />
            {email && !isEmailValid && <p className="text-xs text-red-500 mt-1">Invalid email format</p>}
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
            {password.length > 0 && (
              <div className="mt-2 space-y-1">
                <div className="flex h-1 gap-1">
                  {[...Array(4)].map((_, i) => (
                    <div
                      key={i}
                      className={cn(
                        "h-full flex-1 rounded-full transition-colors",
                        i < strength.score ? strength.color : "bg-gray-700"
                      )}
                    />
                  ))}
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className={cn(
                    "font-medium",
                    strength.score <= 1 ? "text-gray-400" :
                    strength.score === 2 ? "text-yellow-500" :
                    "text-cyan-400"
                  )}>{strength.text}</span>
                  {!isPasswordValid && <span className="text-red-500">Min 8 chars</span>}
                </div>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword" className="text-gray-300 text-sm">Confirm Password</Label>
            <Input
              id="confirmPassword"
              type={showPassword ? "text" : "password"}
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={cn(
                "bg-gray-900/80 text-white focus-visible:ring-cyan-500 h-11 transition-colors",
                confirmPassword && !passwordsMatch ? "border-red-500" :
                passwordsMatch ? "border-emerald-500" : "border-gray-700"
              )}
              placeholder="••••••••"
            />
            {confirmPassword && !passwordsMatch && (
              <p className="text-xs text-red-500 mt-1">Passwords do not match</p>
            )}
            {passwordsMatch && (
              <p className="text-xs text-emerald-500 mt-1 flex items-center gap-1">
                <CheckCircle2 size={12} /> Passwords match
              </p>
            )}
          </div>

          <Button
            type="submit"
            className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-semibold h-11 mt-2 transition-all duration-200"
            disabled={isLoading || isGoogleLoading || !isEmailValid || !isPasswordValid || !passwordsMatch}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating account...
              </>
            ) : (
              "Sign Up"
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

          {/* Google Sign-Up */}
          <div className="flex justify-center">
            {isGoogleLoading ? (
              <Button disabled className="w-full h-11 bg-gray-800 border border-gray-600 text-gray-300">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Signing up with Google...
              </Button>
            ) : (
              <div className="w-full [&>div]:!w-full [&_iframe]:!w-full">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={() => toast.error("Google sign-up failed")}
                  theme="filled_black"
                  size="large"
                  width="400"
                  text="signup_with"
                  shape="rectangular"
                />
              </div>
            )}
          </div>

          <p className="text-center text-sm text-gray-400 pt-2">
            Already have an account?{" "}
            <Link to="/signin" className="text-cyan-500 hover:text-cyan-400 font-medium transition-colors">
              Sign In
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
