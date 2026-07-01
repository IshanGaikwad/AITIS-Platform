"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { routeLabels } from "@/lib/nav-config";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  className?: string;
}

export function Breadcrumb({ items, className }: BreadcrumbProps) {
  return (
    <nav aria-label="Breadcrumb" className={cn("flex items-center gap-1 text-sm", className)}>
      <ol className="flex items-center gap-1">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <li key={index} className="flex items-center gap-1">
              {index > 0 && (
                <ChevronRight className="h-3.5 w-3.5 text-slate-300" />
              )}
              {isLast || !item.href ? (
                <span
                  className={cn(
                    "truncate max-w-[200px]",
                    isLast
                      ? "font-medium text-slate-900"
                      : "text-slate-400"
                  )}
                >
                  {item.label}
                </span>
              ) : (
                <Link
                  href={item.href}
                  className="text-slate-500 hover:text-slate-700 transition-colors truncate max-w-[200px]"
                >
                  {item.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/** Sub-page labels for routes under /studio/[workspaceId]/ */
const studioSubPages: Record<string, string> = {
  requirements: "Requirements",
  "test-cases": "Test Case Generator",
  "test-generator": "Test Case Generator",
  automation: "Automation",
  "test-data": "Test Data",
  "test-suites": "Test Suites",
  execution: "Execution",
  settings: "Workspace Settings",
};

/**
 * Build breadcrumb items from the current pathname.
 * Maps known routes to human-readable labels via routeLabels.
 * Handles dynamic segments for /studio/[workspaceId]/... and /runs/[runId].
 */
export function buildBreadcrumbsFromPath(pathname: string): BreadcrumbItem[] {
  const items: BreadcrumbItem[] = [{ label: "Home", href: "/dashboard" }];

  if (pathname === "/" || pathname === "/dashboard") {
    items.push({ label: "Dashboard" });
    return items;
  }

  const segments = pathname.split("/").filter(Boolean);

  // Handle /studio/[workspaceId]/... dynamic segments
  if (segments[0] === "studio" && segments.length > 1) {
    items.push({ label: "Studio", href: "/studio" });
    const workspaceId = segments[1];

    if (segments.length === 2) {
      items.push({ label: "Workspace" });
    } else {
      items.push({ label: "Workspace", href: `/studio/${workspaceId}` });
      const subPage = segments[2];
      const subPageLabel = studioSubPages[subPage] ?? decodeURIComponent(subPage);
      items.push({ label: subPageLabel });
    }
    return items;
  }

  // Handle /runs/[runId] dynamic segment
  if (segments[0] === "runs" && segments.length > 1) {
    items.push({ label: "Runs", href: "/runs" });
    items.push({ label: "Run Details" });
    return items;
  }

  // Standard routes: walk segments using routeLabels lookup
  let currentPath = "";
  for (let i = 0; i < segments.length; i++) {
    currentPath += `/${segments[i]}`;
    const isLast = i === segments.length - 1;
    const label = routeLabels[currentPath] ?? decodeURIComponent(segments[i]);
    items.push({
      label,
      href: isLast ? undefined : currentPath,
    });
  }

  return items;
}
