"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth";
import { getOrganizations, getWorkspaces } from "@/lib/api";
import type { Organization, Workspace } from "@/lib/types";
import {
  Building2,
  ChevronsUpDown,
  Check,
  Loader2,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

interface OrgWorkspaceSwitcherProps {
  className?: string;
}

export function OrgWorkspaceSwitcher({ className }: OrgWorkspaceSwitcherProps) {
  const { user, selectWorkspaceAndRefresh } = useAuth();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [switching, setSwitching] = useState(false);

  const currentOrgId = user?.organization_id;
  const currentWorkspaceId = user?.workspace_id;

  const currentOrg = organizations.find((o) => o.id === currentOrgId);
  const currentWorkspace = workspaces.find((w) => w.id === currentWorkspaceId);

  /* Load organizations on mount */
  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    getOrganizations()
      .then((orgs) => {
        if (!cancelled) setOrganizations(orgs);
      })
      .catch(() => {
        // Silently fail — user may not have orgs yet
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  /* Load workspaces when org changes */
  useEffect(() => {
    if (!currentOrgId) {
      setWorkspaces([]);
      return;
    }
    let cancelled = false;
    getWorkspaces(currentOrgId)
      .then((ws) => {
        if (!cancelled) setWorkspaces(ws);
      })
      .catch(() => {
        if (!cancelled) setWorkspaces([]);
      });
    return () => {
      cancelled = true;
    };
  }, [currentOrgId]);

  const handleSwitchWorkspace = useCallback(
    async (workspaceId: string) => {
      if (workspaceId === currentWorkspaceId) return;
      setSwitching(true);
      try {
        await selectWorkspaceAndRefresh(workspaceId);
      } catch {
        // Error handled by auth context
      } finally {
        setSwitching(false);
      }
    },
    [currentWorkspaceId, selectWorkspaceAndRefresh]
  );

  if (isLoading) {
    return (
      <div className={cn("flex items-center gap-2 px-2 py-1.5", className)}>
        <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
        <span className="text-xs text-slate-400">Loading...</span>
      </div>
    );
  }

  if (!currentOrg) {
    return null;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className={cn(
            "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-slate-100",
            className
          )}
          disabled={switching}
        >
          <div className="flex h-5 w-5 items-center justify-center rounded bg-slate-200 text-[10px] font-bold text-slate-600">
            {currentOrg.name.charAt(0).toUpperCase()}
          </div>
          <div className="flex flex-col items-start text-left">
            <span className="text-xs font-medium text-slate-700 leading-tight truncate max-w-[120px]">
              {currentOrg.name}
            </span>
            {currentWorkspace && (
              <span className="text-[10px] text-slate-400 leading-tight truncate max-w-[120px]">
                {currentWorkspace.name}
              </span>
            )}
          </div>
          <ChevronsUpDown className="h-3.5 w-3.5 text-slate-400 ml-auto shrink-0" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuLabel className="text-xs text-slate-400">
          Organization
        </DropdownMenuLabel>
        <DropdownMenuItem
          className={cn("cursor-pointer", currentOrg.id === currentOrgId && "bg-slate-50")}
          disabled
        >
          <Building2 className="mr-2 h-4 w-4 text-slate-500" />
          <span className="flex-1 truncate">{currentOrg.name}</span>
          <Check className={cn("h-4 w-4 text-slate-500", currentOrg.id !== currentOrgId && "invisible")} />
        </DropdownMenuItem>

        {workspaces.length > 0 && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuLabel className="text-xs text-slate-400">
              Workspaces
            </DropdownMenuLabel>
            {workspaces.map((ws) => (
              <DropdownMenuItem
                key={ws.id}
                className={cn(
                  "cursor-pointer",
                  ws.id === currentWorkspaceId && "bg-slate-50"
                )}
                onClick={() => handleSwitchWorkspace(ws.id)}
                disabled={switching}
              >
                <FolderIcon className="mr-2 h-4 w-4 text-slate-500" />
                <span className="flex-1 truncate">{ws.name}</span>
                <Check
                  className={cn(
                    "h-4 w-4 text-slate-500",
                    ws.id !== currentWorkspaceId && "invisible"
                  )}
                />
              </DropdownMenuItem>
            ))}
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** Small folder icon (inline to avoid extra imports) */
function FolderIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
    </svg>
  );
}
