"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth";
import { getAuditEvents } from "@/lib/api";
import type { AuditEvent } from "@/lib/types";
import { History, Search, User, FileText, Settings, Trash2, Edit3, Plus, LogIn, LogOut } from "lucide-react";

const actionIcons: Record<string, React.ReactNode> = {
  create: <Plus className="h-4 w-4 text-green-600" />,
  update: <Edit3 className="h-4 w-4 text-blue-600" />,
  delete: <Trash2 className="h-4 w-4 text-red-600" />,
  login: <LogIn className="h-4 w-4 text-purple-600" />,
  logout: <LogOut className="h-4 w-4 text-slate-600" />,
  read: <FileText className="h-4 w-4 text-slate-600" />,
};

const actionColors: Record<string, "green" | "blue" | "rose" | "purple" | "slate"> = {
  create: "green",
  update: "blue",
  delete: "rose",
  login: "purple",
  logout: "slate",
  read: "slate",
};

export default function AuditLogPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!isAuthenticated) return;
    getAuditEvents()
      .then(setEvents)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [isAuthenticated]);

  if (authLoading) return null;
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="max-w-md text-center">
          <CardContent className="pt-8 pb-8">
            <History className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-slate-900">Sign in to view audit log</h2>
            <p className="text-sm text-slate-500 mt-1">Connect your account to view audit events.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const filtered = events.filter((e) =>
    e.action?.toLowerCase().includes(search.toLowerCase()) ||
    e.entity_type?.toLowerCase().includes(search.toLowerCase()) ||
    e.entity_id?.toLowerCase().includes(search.toLowerCase())
  );

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Audit Log</h1>
        <p className="text-slate-500 mt-1">Track all actions and changes across the platform.</p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <Input
          placeholder="Search by action, resource type, or resource ID..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900" />
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <History className="h-12 w-12 text-slate-300 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900">No audit events yet</h3>
            <p className="text-sm text-slate-500 mt-1">
              Audit events will appear here as actions are performed.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {filtered.map((event) => (
            <Card key={event.id}>
              <CardContent className="py-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100">
                    {actionIcons[event.action] || <Settings className="h-4 w-4 text-slate-500" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Badge tone={actionColors[event.action] || "slate"}>
                        {event.action}
                      </Badge>
                      <span className="text-sm font-medium text-slate-700">
                        {event.entity_type}
                      </span>
                      {event.entity_id && (
                        <span className="text-xs text-slate-400 font-mono truncate">
                          {event.entity_id.slice(0, 8)}...
                        </span>
                      )}
                    </div>
                    {event.changes && (
                      <p className="text-xs text-slate-500 mt-1 truncate">
                        {typeof event.changes === "string" ? event.changes : JSON.stringify(event.changes)}
                      </p>
                    )}
                  </div>
                  <div className="text-xs text-slate-400 shrink-0 text-right">
                    <div>{formatDate(event.created_at)}</div>
                    {event.user_id && (
                      <div className="flex items-center gap-1 justify-end mt-0.5">
                        <User className="h-3 w-3" />
                        <span className="font-mono">{event.user_id.slice(0, 8)}...</span>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}