"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Command } from "cmdk";
import {
  Search,
  LayoutDashboard,
  FlaskConical,
  PlayCircle,
  BarChart3,
  ShieldCheck,
  Settings,
  LogOut,
} from "lucide-react";

interface CommandMenuProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface CommandItem {
  id: string;
  label: string;
  icon: React.ElementType;
  href?: string;
  action?: () => void;
  group: string;
}

export function CommandMenu({ open, onOpenChange }: CommandMenuProps) {
  const router = useRouter();
  const { logout } = useAuth();

  const items: CommandItem[] = [
    { id: "dashboard", label: "Go to Dashboard", icon: LayoutDashboard, href: "/dashboard", group: "Navigation" },
    { id: "studio", label: "Go to Studio", icon: FlaskConical, href: "/studio", group: "Navigation" },
    { id: "runs", label: "Go to Runs", icon: PlayCircle, href: "/runs", group: "Navigation" },
    { id: "insights", label: "Go to Insights", icon: BarChart3, href: "/insights", group: "Navigation" },
    { id: "administration", label: "Go to Administration", icon: ShieldCheck, href: "/administration", group: "Navigation" },
    { id: "settings", label: "Go to Settings", icon: Settings, href: "/settings", group: "Account" },
    { id: "sign-out", label: "Sign out", icon: LogOut, action: logout, group: "Account" },
  ];

  const runItem = (item: CommandItem) => {
    onOpenChange(false);
    if (item.href) {
      router.push(item.href);
    } else if (item.action) {
      item.action();
    }
  };

  // Group items by group
  const groups = items.reduce<Record<string, CommandItem[]>>((acc, item) => {
    if (!acc[item.group]) acc[item.group] = [];
    acc[item.group].push(item);
    return acc;
  }, {});

  return (
    <Command.Dialog
      open={open}
      onOpenChange={onOpenChange}
      label="Command menu"
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]"
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50" onClick={() => onOpenChange(false)} />

      {/* Dialog */}
      <div className="relative z-50 w-full max-w-lg rounded-xl border border-slate-200 bg-white shadow-2xl overflow-hidden">
        {/* Search input */}
        <div className="flex items-center border-b border-slate-200 px-4">
          <Search className="mr-2 h-4 w-4 shrink-0 text-slate-400" />
          <Command.Input
            placeholder="Type a command or search..."
            className="flex-1 border-0 bg-transparent py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-0"
          />
        </div>

        {/* Results */}
        <Command.List className="max-h-[300px] overflow-y-auto p-2">
          <Command.Empty className="py-6 text-center text-sm text-slate-400">
            No results found.
          </Command.Empty>

          {Object.entries(groups).map(([group, groupItems]) => (
            <Command.Group
              key={group}
              heading={group}
              className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-slate-400"
            >
              {groupItems.map((item) => (
                <Command.Item
                  key={item.id}
                  onSelect={() => runItem(item)}
                  className="flex cursor-pointer items-center gap-3 rounded-lg px-2 py-2 text-sm text-slate-700 transition-colors aria-selected:bg-slate-100 aria-selected:text-slate-900 hover:bg-slate-50 data-[disabled]:opacity-50"
                >
                  <item.icon className="h-4 w-4 shrink-0 text-slate-400" />
                  <span>{item.label}</span>
                </Command.Item>
              ))}
            </Command.Group>
          ))}
        </Command.List>

        {/* Footer */}
        <div className="border-t border-slate-100 px-4 py-2">
          <p className="text-[10px] text-slate-400">
            <kbd className="rounded border border-slate-200 bg-slate-50 px-1 py-0.5 text-[10px] font-mono">↑↓</kbd> navigate{" "}
            <kbd className="rounded border border-slate-200 bg-slate-50 px-1 py-0.5 text-[10px] font-mono">↵</kbd> select{" "}
            <kbd className="rounded border border-slate-200 bg-slate-50 px-1 py-0.5 text-[10px] font-mono">esc</kbd> close
          </p>
        </div>
      </div>
    </Command.Dialog>
  );
}

/**
 * Hook to manage command menu open state with keyboard shortcut.
 */
export function useCommandMenu() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  return { open, setOpen };
}
