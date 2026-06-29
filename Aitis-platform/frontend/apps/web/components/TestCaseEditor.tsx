"use client";

import React, { useState, useEffect } from "react";
import { 
  Save, 
  History, 
  ChevronLeft, 
  Plus, 
  Trash2, 
  AlertCircle, 
  CheckCircle2, 
  XCircle 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger 
} from "@/components/ui/dropdown-menu";
import { 
  updateTestCase, 
  createTestCase 
} from "@/lib/api";
import type { TestCaseDB, TestCaseVersion } from "@/lib/types";
import { cn } from "@/lib/utils";

interface TestCaseEditorProps {
  suiteId: string;
  testCaseId?: string;
  initialData?: Partial<TestCaseDB>;
  onSave: (updated: TestCaseDB) => void;
  onCancel: () => void;
}

export function TestCaseEditor({ 
  suiteId, 
  testCaseId, 
  initialData, 
  onSave, 
  onCancel 
}: TestCaseEditorProps) {
  const [data, setData] = useState({
    title: initialData?.title || "",
    priority: initialData?.priority || "Medium",
    preconditions: initialData?.preconditions?.join("\n") || "",
    gherkin: initialData?.gherkin || "",
  });
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const payload = {
        ...data,
        preconditions: data.preconditions
          ? data.preconditions.split("\n").filter(Boolean)
          : [],
      };
      const result = testCaseId 
        ? await updateTestCase(suiteId, testCaseId, payload)
        : await createTestCase(suiteId, payload);
      onSave(result);
    } catch (error) {
      console.error("Failed to save test case:", error);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="flex items-center justify-between p-4 border-b bg-slate-50">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={onCancel}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              {testCaseId ? "Edit Test Case" : "New Test Case"}
            </h2>
            <p className="text-xs text-slate-500">Versioned manual test definition</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={onCancel}>Cancel</Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? "Saving..." : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </>
            )}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-2">
            <Label htmlFor="title">Title</Label>
            <Input 
              id="title" 
              value={data.title} 
              onChange={e => setData({...data, title: e.target.value})} 
              placeholder="e.g., Verify User Login with Valid Credentials"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="priority">Priority</Label>
            <select 
              id="priority"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              value={data.priority}
              onChange={e => setData({...data, priority: e.target.value})}
            >
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="preconditions">Preconditions</Label>
          <Textarea 
            id="preconditions" 
            value={data.preconditions} 
            onChange={e => setData({...data, preconditions: e.target.value})}
            placeholder="What needs to be true before starting this test?"
            className="min-h-[100px]"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="gherkin">Test Steps (Gherkin/Structured)</Label>
          <Textarea 
            id="gherkin" 
            value={data.gherkin} 
            onChange={e => setData({...data, gherkin: e.target.value})}
            placeholder="Given... When... Then..."
            className="min-h-[300px] font-mono text-sm"
          />
          <p className="text-xs text-slate-500">
            Note: Steps are automatically versioned and snapshotted upon save.
          </p>
        </div>
      </div>
    </div>
  );
}
