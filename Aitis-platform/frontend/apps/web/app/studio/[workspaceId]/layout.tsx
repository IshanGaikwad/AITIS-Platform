"use client";

import Link from "next/link";
import { usePathname, useParams } from "next/navigation";
import { ArrowLeft, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const workspaceNavItems = [
  { label: "Overview", href: "" },
  { label: "Requirements", href: "/requirements" },
  { label: "Test Cases", href: "/test-cases" },
  { label: "Test Generator", href: "/test-generator" },
  { label: "Automation", href: "/automation" },
  { label: "Test Data", href: "/test-data" },
  { label: "Test Suites", href: "/test-suites" },
  { label: "Execution", href: "/execution" },
];

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const pathname = usePathname();
  const workspaceId = params.workspaceId as string;
  const baseHref = `/studio/${workspaceId}`;

  return (
    <div className="flex flex-col min-h-full -mt-4 -mx-4 sm:-mt-6 sm:-mx-6">
      {/* Workspace context bar */}
      <div className="border-b border-slate-200 bg-white px-4 sm:px-6 py-3">
        <div className="flex items-center gap-3">
          <Link
            href="/studio"
            className="text-slate-400 hover:text-slate-600 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Workspace</h2>
          </div>
          <div className="flex-1" />
          <Link
            href={`${baseHref}/settings`}
            className="text-slate-400 hover:text-slate-600 transition-colors"
          >
            <Settings className="h-4 w-4" />
          </Link>
        </div>
      </div>

      {/* Workspace sub-navigation */}
      <div className="border-b border-slate-100 bg-white px-4 sm:px-6">
        <nav className="flex overflow-x-auto">
          {workspaceNavItems.map((item) => {
            const href = `${baseHref}${item.href}`;
            const isActive =
              item.href === ""
                ? pathname === baseHref
                : pathname.startsWith(href);
            return (
              <Link
                key={item.href}
                href={href}
                className={cn(
                  "whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors",
                  isActive
                    ? "border-slate-900 text-slate-900"
                    : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Page content */}
      <div className="flex-1 p-4 sm:p-6">
        {children}
      </div>
    </div>
  );
}
