"use client";

import Link from "next/link";
import { usePathname, useParams } from "next/navigation";
import { ArrowLeft, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const projectNavItems = [
  { label: "Overview", href: "" },
  { label: "Target", href: "/target" },
  { label: "Requirements", href: "/requirements" },
  { label: "Test Case Generator", href: "/test-cases" },
  { label: "Automation", href: "/automation" },
  { label: "Test Data", href: "/test-data" },
  { label: "Test Suites", href: "/test-suites" },
  { label: "Execution", href: "/execution" },
];

// Chevron geometry — how deep the arrow point / notch cut in (px).
const POINT = 16;
// First step: flat left edge, pointed right.
const CLIP_FIRST = `polygon(0 0, calc(100% - ${POINT}px) 0, 100% 50%, calc(100% - ${POINT}px) 100%, 0 100%)`;
// Middle steps: notched left, pointed right.
const CLIP_MIDDLE = `polygon(0 0, calc(100% - ${POINT}px) 0, 100% 50%, calc(100% - ${POINT}px) 100%, 0 100%, ${POINT}px 50%)`;
// Last step (Execution): notched left, flat right — the destination.
const CLIP_LAST = `polygon(0 0, 100% 0, 100% 100%, 0 100%, ${POINT}px 50%)`;

export default function ProjectLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const pathname = usePathname();
  const workspaceId = params.workspaceId as string;
  const baseHref = `/studio/${workspaceId}`;

  const activeIndex = projectNavItems.findIndex((item) => {
    const href = `${baseHref}${item.href}`;
    return item.href === "" ? pathname === baseHref : pathname.startsWith(href);
  });
  const activeLabel = activeIndex >= 0 ? projectNavItems[activeIndex].label : null;

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
          <h2 className="text-sm font-semibold text-slate-900">Workspace</h2>
          {activeLabel && (
            <span className="text-xs font-medium text-slate-400">· {activeLabel}</span>
          )}
          <div className="flex-1" />
          <Link
            href={`${baseHref}/settings`}
            className="text-slate-400 hover:text-slate-600 transition-colors"
          >
            <Settings className="h-4 w-4" />
          </Link>
        </div>
      </div>

      {/* Workspace activity flow — chevron progression toward Execution.
          Any step is reachable (bi-directional, no gating). Steps reached so far
          render green; untouched steps stay blank. */}
      <div className="border-b border-slate-100 bg-white px-4 sm:px-6 py-4">
        <nav aria-label="Workspace activities" className="flex items-stretch overflow-x-auto">
          {projectNavItems.map((item, idx) => {
            const href = `${baseHref}${item.href}`;
            const isFirst = idx === 0;
            const isLast = idx === projectNavItems.length - 1;
            const reached = activeIndex >= 0 && idx <= activeIndex;
            const isCurrent = idx === activeIndex;
            const clip = isFirst ? CLIP_FIRST : isLast ? CLIP_LAST : CLIP_MIDDLE;

            return (
              <Link
                key={item.href}
                href={href}
                aria-current={isCurrent ? "step" : undefined}
                title={item.label}
                style={{
                  marginLeft: isFirst ? 0 : -POINT,
                  zIndex: projectNavItems.length - idx,
                }}
                className="group relative block h-10 min-w-[112px] flex-1 sm:min-w-[132px]"
              >
                {/* outline / border layer */}
                <span
                  aria-hidden
                  style={{ clipPath: clip }}
                  className={cn(
                    "absolute inset-0 transition-colors",
                    reached
                      ? "bg-emerald-500"
                      : "bg-slate-300 group-hover:bg-slate-400",
                  )}
                />
                {/* fill layer (inset to reveal the outline as a thin border) */}
                <span
                  style={{ clipPath: clip }}
                  className={cn(
                    "absolute inset-[1.5px] flex items-center justify-center transition-colors",
                    reached
                      ? cn("text-white", isCurrent ? "bg-emerald-600" : "bg-emerald-500")
                      : "bg-white text-slate-500 group-hover:text-slate-700",
                  )}
                >
                  <span
                    className={cn(
                      "truncate text-center text-xs",
                      isFirst ? "pl-2 pr-4" : "pl-6 pr-4",
                      isCurrent ? "font-semibold" : "font-medium",
                    )}
                  >
                    {item.label}
                  </span>
                </span>
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
