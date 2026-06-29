"use client";

import { useState, useEffect, useCallback } from "react";
import {
  listAutomationScripts,
  createAutomationScript,
  deleteAutomationScript,
} from "@/lib/api";
import type { AutomationScript, AutomationScriptCreate } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Plus,
  Search,
  FileCode2,
  Trash2,
  Play,
  Pencil,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Status badge helper ── */
function statusTone(status: string): "green" | "amber" | "rose" | "slate" | "blue" | "purple" {
  switch (status) {
    case "ready":
      return "green";
    case "draft":
      return "slate";
    case "needs_update":
      return "amber";
    case "deprecated":
      return "rose";
    default:
      return "slate";
  }
}

function frameworkIcon(framework: string) {
  return <FileCode2 className="h-4 w-4 shrink-0 text-muted-foreground" />;
}

interface ScriptListProps {
  selectedId: string | null;
  onSelect: (id: string) => void;
  onScriptCreated?: (script: AutomationScript) => void;
}

export function ScriptList({ selectedId, onSelect, onScriptCreated }: ScriptListProps) {
  const [scripts, setScripts] = useState<AutomationScript[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterFramework, setFilterFramework] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [showCreate, setShowCreate] = useState(false);

  /* ── Fetch scripts ── */
  const fetchScripts = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (filterFramework && filterFramework !== "all") params.framework = filterFramework;
      if (filterStatus && filterStatus !== "all") params.status = filterStatus;
      const data = await listAutomationScripts(params);
      setScripts(data);
    } catch (err) {
      console.error("Failed to load scripts:", err);
    } finally {
      setLoading(false);
    }
  }, [filterFramework, filterStatus]);

  useEffect(() => {
    fetchScripts();
  }, [fetchScripts]);

  /* ── Create script ── */
  const handleCreate = async (data: AutomationScriptCreate) => {
    try {
      const script = await createAutomationScript(data);
      setShowCreate(false);
      fetchScripts();
      onScriptCreated?.(script);
      onSelect(script.id);
    } catch (err) {
      console.error("Failed to create script:", err);
    }
  };

  /* ── Delete script ── */
  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this script?")) return;
    try {
      await deleteAutomationScript(id);
      fetchScripts();
      if (selectedId === id) onSelect("");
    } catch (err) {
      console.error("Failed to delete script:", err);
    }
  };

  /* ── Filter by search ── */
  const filtered = scripts.filter((s) =>
    s.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex h-full flex-col border-r bg-muted/30">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-3 py-2">
        <h2 className="text-sm font-semibold">Scripts</h2>
        <Button size="icon" variant="ghost" onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* Search */}
      <div className="px-3 py-2">
        <div className="relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search scripts…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 pl-8 text-sm"
          />
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 px-3 pb-2">
        <Select value={filterFramework} onValueChange={setFilterFramework}>
          <SelectTrigger className="h-7 w-full text-xs">
            <SelectValue placeholder="Framework" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All frameworks</SelectItem>
            <SelectItem value="playwright">Playwright</SelectItem>
            <SelectItem value="selenium">Selenium</SelectItem>
            <SelectItem value="cypress">Cypress</SelectItem>
            <SelectItem value="pytest">Pytest</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="h-7 w-full text-xs">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="ready">Ready</SelectItem>
            <SelectItem value="needs_update">Needs Update</SelectItem>
            <SelectItem value="deprecated">Deprecated</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Script list */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
            Loading…
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
            No scripts found
          </div>
        ) : (
          <ul className="space-y-0.5 px-1">
            {filtered.map((script) => (
              <li
                key={script.id}
                onClick={() => onSelect(script.id)}
                className={cn(
                  "group flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent",
                  selectedId === script.id && "bg-accent font-medium"
                )}
              >
                {frameworkIcon(script.framework)}
                <span className="flex-1 truncate">{script.name}</span>
                <Badge tone={statusTone(script.status)} className="text-[10px] px-1.5 py-0">
                  {script.status}
                </Badge>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5 opacity-0 group-hover:opacity-100"
                  onClick={(e) => handleDelete(script.id, e)}
                >
                  <Trash2 className="h-3 w-3 text-muted-foreground" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Create dialog */}
      <CreateScriptDialog
        open={showCreate}
        onOpenChange={setShowCreate}
        onSubmit={handleCreate}
      />
    </div>
  );
}

/* ── Create Script Dialog ── */
function CreateScriptDialog({
  open,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onSubmit: (data: AutomationScriptCreate) => void;
}) {
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("typescript");
  const [framework, setFramework] = useState("playwright");

  const handleSubmit = () => {
    if (!name.trim()) return;
    onSubmit({ name: name.trim(), language, framework });
    setName("");
    setLanguage("typescript");
    setFramework("playwright");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New Automation Script</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div>
            <label className="text-sm font-medium">Name</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Login flow test"
              className="mt-1"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Language</label>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="typescript">TypeScript</SelectItem>
                <SelectItem value="javascript">JavaScript</SelectItem>
                <SelectItem value="python">Python</SelectItem>
                <SelectItem value="java">Java</SelectItem>
                <SelectItem value="csharp">C#</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-sm font-medium">Framework</label>
            <Select value={framework} onValueChange={setFramework}>
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="playwright">Playwright</SelectItem>
                <SelectItem value="selenium">Selenium</SelectItem>
                <SelectItem value="cypress">Cypress</SelectItem>
                <SelectItem value="pytest">Pytest</SelectItem>
                <SelectItem value="testng">TestNG</SelectItem>
                <SelectItem value="junit">JUnit</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
          <Button onClick={handleSubmit} disabled={!name.trim()}>
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
