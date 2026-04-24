import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Test Intelligence Studio",
  description: "Scaffolded frontend for Jira-to-test intelligence",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
