"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { Eye, EyeOff } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [tab, setTab] = useState<"signin" | "signup">("signin");

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
            onClick={() => login("atlassian")}
            className="flex w-full items-center justify-center gap-3 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0" fill="none">
              <path d="M11.53 2.11a.67.67 0 0 0-1.13 0L.19 19.56a.67.67 0 0 0 .57 1h5.75c.24 0 .46-.13.58-.34l4.44-7.79 4.44 7.79c.12.21.34.34.58.34h5.75a.67.67 0 0 0 .57-1L11.53 2.11Z" fill="#0052CC"/>
            </svg>
            Continue with Atlassian
          </button>
        </div>

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
