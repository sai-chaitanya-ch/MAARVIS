import React, { useState } from "react";
import { X, Lock, Mail, Loader2, CheckCircle2, AlertCircle, Eye, EyeOff } from "lucide-react";
import { signInWithEmail, signUpWithEmail, isSupabaseConfigured } from "../lib/supabase";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAuthSuccess?: () => void;
}

export default function AuthModal({ isOpen, onClose, onAuthSuccess }: AuthModalProps) {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const cleanEmail = email.trim();
    if (!cleanEmail || !password) {
      setError("Please provide both email and password.");
      return;
    }

    if (!isSupabaseConfigured) {
      setError("Supabase Auth is not configured on this environment. Ensure VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are set.");
      return;
    }

    setLoading(true);
    try {
      if (mode === "signin") {
        const { user, error: signinError } = await signInWithEmail(cleanEmail, password);
        if (signinError) {
          setError(signinError);
        } else if (user) {
          setSuccess("Signed in successfully!");
          setTimeout(() => {
            onAuthSuccess?.();
            onClose();
          }, 400);
        }
      } else {
        const { user, error: signupError, confirmationRequired } = await signUpWithEmail(cleanEmail, password);
        if (signupError) {
          setError(signupError);
        } else if (confirmationRequired) {
          setSuccess("Account created! Check your email to confirm your account.");
        } else if (user) {
          setSuccess("Account created and signed in!");
          setTimeout(() => {
            onAuthSuccess?.();
            onClose();
          }, 400);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-[2px] p-4">
      <div className="w-full max-w-sm rounded-2xl border border-[#E5E7EB] bg-white shadow-2xl text-[#111111] animate-in fade-in zoom-in-95 duration-150 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#E5E7EB] px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-neutral-900 text-white font-bold text-xs">
              M
            </div>
            <div>
              <h3 className="text-sm font-bold tracking-tight text-[#111111]">
                {mode === "signin" ? "Sign In to MAARVIS" : "Create Account"}
              </h3>
              <p className="text-[11px] text-[#6B7280]">Supabase Authenticated Session</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-[#9CA3AF] hover:bg-[#F3F4F6] hover:text-[#111111] transition cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>

        {/* Tab switch */}
        <div className="flex border-b border-[#E5E7EB] bg-[#F8F9FA] px-6">
          <button
            type="button"
            onClick={() => {
              setMode("signin");
              setError(null);
              setSuccess(null);
            }}
            className={`py-2.5 px-3 text-xs font-medium border-b-2 transition cursor-pointer ${
              mode === "signin"
                ? "border-neutral-900 text-neutral-900 font-semibold"
                : "border-transparent text-neutral-500 hover:text-neutral-900"
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("signup");
              setError(null);
              setSuccess(null);
            }}
            className={`py-2.5 px-3 text-xs font-medium border-b-2 transition cursor-pointer ${
              mode === "signup"
                ? "border-neutral-900 text-neutral-900 font-semibold"
                : "border-transparent text-neutral-500 hover:text-neutral-900"
            }`}
          >
            Sign Up
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          {error && (
            <div className="flex items-start gap-2 rounded-lg bg-rose-50 border border-rose-200 p-2.5 text-rose-800 text-[11px]">
              <AlertCircle size={14} className="shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="flex items-start gap-2 rounded-lg bg-emerald-50 border border-emerald-200 p-2.5 text-emerald-800 text-[11px]">
              <CheckCircle2 size={14} className="shrink-0 mt-0.5" />
              <span>{success}</span>
            </div>
          )}

          <div>
            <label className="block text-[11px] font-semibold text-neutral-700 mb-1">
              Email Address
            </label>
            <div className="relative">
              <input
                type="email"
                autoComplete="email"
                required
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-[#E5E7EB] bg-white px-3 py-2 text-xs pl-8 focus:border-neutral-900 focus:outline-none"
              />
              <Mail size={13} className="absolute left-2.5 top-2.5 text-neutral-400" />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-neutral-700 mb-1">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                autoComplete={mode === "signin" ? "current-password" : "new-password"}
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-[#E5E7EB] bg-white px-3 py-2 text-xs pl-8 pr-8 focus:border-neutral-900 focus:outline-none"
              />
              <Lock size={13} className="absolute left-2.5 top-2.5 text-neutral-400" />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2.5 top-2.5 text-neutral-400 hover:text-neutral-700"
              >
                {showPassword ? <EyeOff size={13} /> : <Eye size={13} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 inline-flex items-center justify-center gap-1.5 rounded-lg bg-neutral-900 py-2 px-4 text-xs font-medium text-white hover:bg-neutral-800 transition disabled:opacity-50 cursor-pointer shadow-2xs"
          >
            {loading ? (
              <>
                <Loader2 size={13} className="animate-spin" />
                <span>{mode === "signin" ? "Signing In…" : "Creating Account…"}</span>
              </>
            ) : (
              <span>{mode === "signin" ? "Sign In" : "Create Account"}</span>
            )}
          </button>

          <p className="text-[10px] text-neutral-400 text-center pt-1">
            Requests are authenticated via verified Supabase Bearer JWT tokens.
          </p>
        </form>
      </div>
    </div>
  );
}
