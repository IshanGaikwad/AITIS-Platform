"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { initiateSso } from "@/lib/api";
import { Eye, EyeOff, Building2, ArrowLeft, Loader2 } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [tab, setTab] = useState<"signin" | "signup">("signin");
  const [authError, setAuthError] = useState<string | null>(null);
  const [pendingProvider, setPendingProvider] = useState<string | null>(null);
  const [ssoMode, setSsoMode] = useState(false);
  const [ssoEmail, setSsoEmail] = useState("");

  async function handleSso(provider: string) {
    setAuthError(null);
    setPendingProvider(provider);
    try {
      await login(provider);
      // On success the browser is redirected to the provider, so this resolves
      // only if the redirect did not occur.
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : "Unable to start sign-in. Please try again.");
      setPendingProvider(null);
    }
  }

  async function handleSsoInitiate(e: React.FormEvent) {
    e.preventDefault();
    setAuthError(null);
    setPendingProvider("sso");
    try {
      const { authorization_url } = await initiateSso(ssoEmail.trim());
      window.location.href = authorization_url;
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : "Unable to start SSO sign-in.");
      setPendingProvider(null);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center px-4">
      {/* Logo */}
      <div className="mb-8 text-center">
        <Link href="/" className="inline-flex items-center gap-2.5 mb-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900 text-sm font-bold text-white">
            AI
          </div>
          <span className="text-2xl font-bold text-slate-900">AITIS</span>
        </Link>
        <p className="text-sm text-slate-500">AI Test Intelligence System</p>
      </div>

      {/* Card */}
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        {/* Tabs */}
        <div className="mb-6 flex rounded-lg border border-slate-200 bg-slate-50 p-0.5">
          <button
            onClick={() => setTab("signin")}
            className={`flex-1 rounded-md py-1.5 text-sm font-medium transition-colors ${
              tab === "signin"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Sign In
          </button>
          <button
            onClick={() => setTab("signup")}
            className={`flex-1 rounded-md py-1.5 text-sm font-medium transition-colors ${
              tab === "signup"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Sign Up
          </button>
        </div>

        {/* SSO */}
        <div className="space-y-2.5 mb-5">
          <button
            onClick={() => handleSso("atlassian")}
            disabled={pendingProvider !== null}
            className="flex w-full items-center justify-center gap-3 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-60"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0" fill="none">
              <path d="M11.53 2.11a.67.67 0 0 0-1.13 0L.19 19.56a.67.67 0 0 0 .57 1h5.75c.24 0 .46-.13.58-.34l4.44-7.79 4.44 7.79c.12.21.34.34.58.34h5.75a.67.67 0 0 0 .57-1L11.53 2.11Z" fill="#0052CC"/>
            </svg>
            Continue with Atlassian
          </button>
          <button
            onClick={() => handleSso("github")}
            disabled={pendingProvider !== null}
            className="flex w-full items-center justify-center gap-3 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-60"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0" fill="#181717" aria-hidden="true">
              <path d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.53-1.34-1.29-1.7-1.29-1.7-1.06-.72.08-.7.08-.7 1.17.08 1.78 1.2 1.78 1.2 1.04 1.78 2.73 1.27 3.4.97.1-.75.4-1.27.73-1.56-2.56-.29-5.25-1.28-5.25-5.7 0-1.26.45-2.29 1.2-3.1-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11.1 11.1 0 0 1 5.8 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.75.81 1.2 1.84 1.2 3.1 0 4.43-2.7 5.41-5.27 5.69.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5Z"/>
            </svg>
            Continue with GitHub
          </button>
          {!ssoMode ? (
            <button
              onClick={() => { setAuthError(null); setSsoMode(true); }}
              disabled={pendingProvider !== null}
              className="flex w-full items-center justify-center gap-3 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-60"
            >
              <Building2 className="h-5 w-5 shrink-0 text-slate-600" />
              Continue with Organization SSO
            </button>
          ) : (
            <form onSubmit={handleSsoInitiate} className="space-y-2 rounded-lg border border-slate-300 bg-slate-50 p-3">
              <label className="flex items-center gap-2 text-xs font-medium text-slate-700">
                <Building2 className="h-4 w-4 text-slate-600" />
                Work email for Organization SSO
              </label>
              <input
                type="email"
                required
                autoFocus
                value={ssoEmail}
                onChange={(e) => setSsoEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-100"
              />
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => { setSsoMode(false); setAuthError(null); }}
                  className="flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
                >
                  <ArrowLeft className="h-3.5 w-3.5" /> Back
                </button>
                <button
                  type="submit"
                  disabled={pendingProvider !== null}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
                >
                  {pendingProvider === "sso" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Continue
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Auth error */}
        {authError && (
          <div className="mb-5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs text-rose-700">
            {authError}
          </div>
        )}

        {/* Divider */}
        <div className="relative mb-5">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-200" />
          </div>
          <div className="relative flex justify-center">
            <span className="bg-white px-3 text-xs text-slate-400">
              {tab === "signin" ? "or sign in with email" : "or create account with email"}
            </span>
          </div>
        </div>

        {/* Form */}
        <form className="space-y-3" onSubmit={(e) => e.preventDefault()}>
          {tab === "signup" && (
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700">Full Name</label>
              <input
                type="text"
                placeholder="Jane Smith"
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-100"
              />
            </div>
          )}
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Email Address</label>
            <input
              type="email"
              placeholder="you@company.com"
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Password</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder={tab === "signup" ? "Create a strong password" : "••••••••"}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 pr-10 text-sm outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-100"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          {tab === "signup" && (
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700">Company / Organization</label>
              <input
                type="text"
                placeholder="Acme Corp"
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-100"
              />
            </div>
          )}
          <button
            type="submit"
            className="mt-1 w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
          >
            {tab === "signin" ? "Sign In" : "Create Account"}
          </button>
        </form>

        {tab === "signin" && (
          <p className="mt-4 text-center text-xs text-slate-500">
            Don&apos;t have an account?{" "}
            <button
              onClick={() => setTab("signup")}
              className="font-medium text-slate-900 underline underline-offset-2"
            >
              Sign up free
            </button>
          </p>
        )}
        {tab === "signup" && (
          <p className="mt-4 text-center text-xs text-slate-500">
            Already have an account?{" "}
            <button
              onClick={() => setTab("signin")}
              className="font-medium text-slate-900 underline underline-offset-2"
            >
              Sign in
            </button>
          </p>
        )}
      </div>

      <Link href="/" className="mt-6 text-sm text-slate-500 hover:text-slate-700">
        ← Back to home
      </Link>
    </div>
  );
}
