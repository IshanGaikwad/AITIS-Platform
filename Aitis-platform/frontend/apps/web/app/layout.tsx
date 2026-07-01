import "./globals.css";
import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth";
import { QueryProvider } from "@/components/query-provider";
import { AppShell } from "@/components/app-shell";
import { Toaster } from "@/components/ui/toaster";

export const metadata: Metadata = {
  title: "AITIS — AI Test Intelligence System",
  description: "AI-powered test intelligence platform for Jira-to-test automation",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <AuthProvider>
            <AppShell>{children}</AppShell>
            <Toaster />
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
