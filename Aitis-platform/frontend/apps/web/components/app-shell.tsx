"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Menu,
  Search,
} from "lucide-react";
import { OrgProjectSwitcher } from "@/components/org-project-switcher";
import { Breadcrumb, buildBreadcrumbsFromPath } from "@/components/breadcrumb";
import { CommandMenu, useCommandMenu } from "@/components/command-menu";
import { MobileNav } from "@/components/mobile-nav";
import { mainNavItems } from "@/lib/nav-config";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout, isAuthenticated, isLoading } = useAuth();
  const [collapsed, setCollapsed] = React.useState(false);
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false);
  const { open: commandOpen, setOpen: setCommandOpen } = useCommandMenu();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
          <p className="text-sm text-slate-500">Loading AITIS...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <>{children}</>;
  }

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "??";

  const breadcrumbs = buildBreadcrumbsFromPath(pathname);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      {/* ── Desktop Sidebar ── */}
      <aside
        className={cn(
          "hidden lg:flex flex-col border-r border-slate-200 bg-white transition-all duration-300",
          collapsed ? "w-16" : "w-64"
        )}
      >
        {/* Logo */}
        <div className="flex h-14 items-center border-b border-slate-200 px-4">
          {!collapsed && (
            <Link href="/" className="flex items-center gap-2 font-bold text-slate-900">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-900 text-xs font-bold text-white">
                AI
              </div>
              <span className="text-sm">AITIS</span>
            </Link>
          )}
          {collapsed && (
            <Link href="/" className="mx-auto">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-900 text-xs font-bold text-white">
                AI
              </div>
            </Link>
          )}
        </div>

        {/* Org/Project Switcher (sidebar) */}
        {!collapsed && (
          <div className="border-b border-slate-100 px-3 py-2">
            <OrgProjectSwitcher />
          </div>
        )}
        {collapsed && (
          <div className="flex justify-center border-b border-slate-100 py-2">
            <div
              className="flex h-6 w-6 items-center justify-center rounded bg-slate-200 text-[10px] font-bold text-slate-600"
              title={user?.organization_id ? "Switch project" : undefined}
            >
              {user?.organization_id ? "O" : "?"}
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-2">
          <div className="space-y-1">
            {mainNavItems.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-slate-100 text-slate-900"
                      : "text-slate-500 hover:bg-slate-50 hover:text-slate-700",
                    collapsed && "justify-center px-2"
                  )}
                  title={collapsed ? item.label : undefined}
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              );
            })}
          </div>
        </nav>

        {/* User section */}
        <div className="border-t border-slate-200 p-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className={cn(
                  "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-slate-50",
                  collapsed && "justify-center px-2"
                )}
              >
                <Avatar className="h-7 w-7">
                  <AvatarImage src={user?.picture || undefined} />
                  <AvatarFallback className="text-xs">{initials}</AvatarFallback>
                </Avatar>
                {!collapsed && (
                  <div className="flex-1 text-left">
                    <p className="text-sm font-medium text-slate-700 truncate max-w-[140px]">
                      {user?.name || "User"}
                    </p>
                    <p className="text-xs text-slate-400 truncate max-w-[140px]">
                      {user?.email || ""}
                    </p>
                  </div>
                )}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>My Account</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href="/settings">
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout} className="text-red-600">
                <LogOut className="mr-2 h-4 w-4" />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex h-8 items-center justify-center border-t border-slate-200 text-slate-400 hover:text-slate-600"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </aside>

      {/* ── Main area ── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* ── Top header bar ── */}
        <header className="flex h-14 items-center gap-4 border-b border-slate-200 bg-white px-4 lg:px-6">
          {/* Mobile hamburger */}
          <button
            className="lg:hidden rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
            onClick={() => setMobileNavOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* Mobile logo */}
          <Link href="/" className="flex items-center gap-2 font-bold text-slate-900 lg:hidden">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-900 text-xs font-bold text-white">
              AI
            </div>
            <span className="text-sm">AITIS</span>
          </Link>

          {/* Breadcrumbs */}
          <Breadcrumb items={breadcrumbs} className="hidden sm:flex" />

          {/* Spacer */}
          <div className="flex-1" />

          {/* Command menu trigger */}
          <button
            onClick={() => setCommandOpen(true)}
            className="hidden sm:flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
          >
            <Search className="h-4 w-4" />
            <span className="hidden md:inline">Search...</span>
            <kbd className="hidden md:inline-flex items-center rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-mono text-slate-400">
              ⌘K
            </kbd>
          </button>

          {/* Mobile search button */}
          <button
            onClick={() => setCommandOpen(true)}
            className="sm:hidden rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
          >
            <Search className="h-5 w-5" />
          </button>

          {/* Mobile org switcher (compact) */}
          <div className="lg:hidden">
            <OrgProjectSwitcher className="!py-0 !px-1" />
          </div>
        </header>

        {/* ── Page content ── */}
        <main className="flex-1 overflow-auto">
          <div className="mx-auto max-w-7xl p-4 sm:p-6">{children}</div>
        </main>
      </div>

      {/* ── Mobile navigation drawer ── */}
      <MobileNav open={mobileNavOpen} onOpenChange={setMobileNavOpen} />

      {/* ── Command menu dialog ── */}
      <CommandMenu open={commandOpen} onOpenChange={setCommandOpen} />
    </div>
  );
}
