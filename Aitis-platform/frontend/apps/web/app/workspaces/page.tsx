"use client";

import { WorkspacesList } from "@/components/workspaces-list";
import { useAuth } from "@/lib/auth";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function WorkspacesPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [projectId, setProjectId] = useState<string>("");

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/auth/login");
      return;
    }

    // Get project ID from user context or local storage
    const ws = user?.project_id || localStorage.getItem("project_id");
    if (ws) {
      setProjectId(ws);
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="h-8 w-8 border-4 border-slate-200 border-t-slate-900 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {projectId && <WorkspacesList projectId={projectId} />}
      </div>
    </div>
  );
}
