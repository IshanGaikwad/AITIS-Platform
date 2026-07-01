"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Plus, Database, Tag } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type DataTab = "Valid" | "Invalid" | "Boundary" | "Synthetic";

type Dataset = {
  id: string;
  name: string;
  type: string;
  records: number;
  environment: string;
  tags: string[];
  usageCount: number;
  lastUpdated: string;
};

const mockDatasets: Record<DataTab, Dataset[]> = {
  Valid: [
    {
      id: "ds-001",
      name: "Standard Users",
      type: "User Profiles",
      records: 50,
      environment: "UAT",
      tags: ["login", "profile", "e2e"],
      usageCount: 24,
      lastUpdated: "2 hours ago",
    },
    {
      id: "ds-002",
      name: "Premium Customers",
      type: "Customer Data",
      records: 20,
      environment: "UAT",
      tags: ["checkout", "subscription"],
      usageCount: 12,
      lastUpdated: "Yesterday",
    },
  ],
  Invalid: [
    {
      id: "ds-003",
      name: "Malformed Emails",
      type: "Negative Inputs",
      records: 30,
      environment: "QA",
      tags: ["validation", "negative"],
      usageCount: 8,
      lastUpdated: "3 days ago",
    },
  ],
  Boundary: [
    {
      id: "ds-004",
      name: "Field Length Extremes",
      type: "Boundary Values",
      records: 15,
      environment: "QA",
      tags: ["boundary", "validation"],
      usageCount: 5,
      lastUpdated: "1 week ago",
    },
  ],
  Synthetic: [
    {
      id: "ds-005",
      name: "AI-Generated Profiles",
      type: "Synthetic",
      records: 200,
      environment: "UAT",
      tags: ["synthetic", "ai", "bulk"],
      usageCount: 3,
      lastUpdated: "Today",
    },
  ],
};

const DATA_TABS: DataTab[] = ["Valid", "Invalid", "Boundary", "Synthetic"];

export default function TestDataPage() {
  const params = useParams();
  const [activeTab, setActiveTab] = useState<DataTab>("Valid");

  const datasets = mockDatasets[activeTab];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-900">Test Data</h2>
        <Button size="sm">
          <Plus className="h-4 w-4" />
          New Dataset
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        {DATA_TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "whitespace-nowrap border-b-2 px-5 py-2.5 text-sm font-medium transition-colors",
              activeTab === tab
                ? "border-slate-900 text-slate-900"
                : "border-transparent text-slate-500 hover:text-slate-700",
            )}
          >
            {tab}
            <span className="ml-1.5 text-xs text-slate-400">
              ({mockDatasets[tab].length})
            </span>
          </button>
        ))}
      </div>

      {/* Dataset cards */}
      {datasets.length === 0 ? (
        <div className="py-16 text-center text-slate-500">
          <Database className="mx-auto mb-3 h-8 w-8 text-slate-300" />
          <p className="text-sm">No datasets in this category yet.</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {datasets.map((ds) => (
            <Card key={ds.id} className="cursor-pointer transition-shadow hover:shadow-sm">
              <CardContent className="space-y-3 p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-slate-900">{ds.name}</p>
                    <p className="mt-0.5 text-xs text-slate-500">{ds.type}</p>
                  </div>
                  <Database className="h-4 w-4 shrink-0 text-slate-300" />
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded bg-slate-50 px-2.5 py-1.5">
                    <span className="text-slate-400">Records </span>
                    <span className="font-medium text-slate-700">{ds.records}</span>
                  </div>
                  <div className="rounded bg-slate-50 px-2.5 py-1.5">
                    <span className="text-slate-400">Env </span>
                    <span className="font-medium text-slate-700">{ds.environment}</span>
                  </div>
                  <div className="rounded bg-slate-50 px-2.5 py-1.5">
                    <span className="text-slate-400">Used </span>
                    <span className="font-medium text-slate-700">{ds.usageCount}x</span>
                  </div>
                  <div className="rounded bg-slate-50 px-2.5 py-1.5">
                    <span className="text-slate-400">Updated </span>
                    <span className="font-medium text-slate-700">{ds.lastUpdated}</span>
                  </div>
                </div>

                <div className="flex flex-wrap gap-1">
                  {ds.tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
                    >
                      <Tag className="h-2.5 w-2.5" />
                      {tag}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
