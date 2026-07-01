"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ExecutionJobSummary } from "@/lib/types";

/* ── Status taxonomy (Allure-style buckets) ── */
type BucketKey = "passed" | "failed" | "broken" | "skipped" | "running";

const BUCKETS: { key: BucketKey; label: string; color: string }[] = [
  { key: "passed", label: "Passed", color: "#10b981" },
  { key: "failed", label: "Failed", color: "#f43f5e" },
  { key: "broken", label: "Broken", color: "#f59e0b" },
  { key: "skipped", label: "Skipped", color: "#94a3b8" },
  { key: "running", label: "Running", color: "#3b82f6" },
];

const COLOR: Record<BucketKey, string> = BUCKETS.reduce(
  (acc, b) => ({ ...acc, [b.key]: b.color }),
  {} as Record<BucketKey, string>,
);

function bucketOf(status: string): BucketKey {
  switch (status) {
    case "passed":
      return "passed";
    case "failed":
      return "failed";
    case "infrastructure_error":
    case "timed_out":
    case "error":
      return "broken";
    case "cancelled":
    case "skipped":
    case "blocked":
      return "skipped";
    default:
      return "running"; // running | queued | provisioning | pending
  }
}

export interface StatusCounts {
  passed: number;
  failed: number;
  broken: number;
  skipped: number;
  running: number;
  total: number;
}

function countStatuses(reports: ExecutionJobSummary[]): StatusCounts {
  const c: StatusCounts = { passed: 0, failed: 0, broken: 0, skipped: 0, running: 0, total: 0 };
  for (const r of reports) {
    c[bucketOf(r.status)] += 1;
    c.total += 1;
  }
  return c;
}

/* ── Donut chart ── */
function StatusDonut({ counts }: { counts: StatusCounts }) {
  const RADIUS = 60;
  const STROKE = 22;
  const C = 2 * Math.PI * RADIUS;
  const size = (RADIUS + STROKE / 2) * 2;
  const center = size / 2;

  const segments = BUCKETS.map((b) => ({ ...b, value: counts[b.key] })).filter((s) => s.value > 0);
  const passRate = counts.total ? Math.round((counts.passed / counts.total) * 100) : 0;

  let offset = 0;

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Execution status distribution">
        <g transform={`rotate(-90 ${center} ${center})`}>
          {/* track */}
          <circle cx={center} cy={center} r={RADIUS} fill="none" stroke="#f1f5f9" strokeWidth={STROKE} />
          {counts.total === 0 ? null : segments.map((s) => {
            const len = (s.value / counts.total) * C;
            const el = (
              <circle
                key={s.key}
                cx={center}
                cy={center}
                r={RADIUS}
                fill="none"
                stroke={s.color}
                strokeWidth={STROKE}
                strokeDasharray={`${len} ${C - len}`}
                strokeDashoffset={-offset}
                strokeLinecap="butt"
              />
            );
            offset += len;
            return el;
          })}
        </g>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold text-slate-900 leading-none">{counts.total}</span>
        <span className="text-[11px] uppercase tracking-wide text-slate-400 mt-1">runs</span>
        <span className="mt-1 text-xs font-semibold text-emerald-600">{passRate}% pass</span>
      </div>
    </div>
  );
}

/* ── Donut legend ── */
function DonutLegend({ counts }: { counts: StatusCounts }) {
  return (
    <ul className="flex-1 space-y-2 min-w-[160px]">
      {BUCKETS.map((b) => {
        const value = counts[b.key];
        const pct = counts.total ? Math.round((value / counts.total) * 100) : 0;
        return (
          <li key={b.key} className="flex items-center gap-2.5 text-sm">
            <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: b.color }} />
            <span className="text-slate-600 flex-1">{b.label}</span>
            <span className="font-semibold text-slate-900 tabular-nums">{value}</span>
            <span className="text-xs text-slate-400 w-9 text-right tabular-nums">{pct}%</span>
          </li>
        );
      })}
    </ul>
  );
}

/* ── Horizontal status bar chart ── */
function StatusBarChart({ counts }: { counts: StatusCounts }) {
  const max = Math.max(1, ...BUCKETS.map((b) => counts[b.key]));
  return (
    <div className="space-y-3">
      {BUCKETS.map((b) => {
        const value = counts[b.key];
        const w = (value / max) * 100;
        return (
          <div key={b.key} className="flex items-center gap-3">
            <span className="text-xs text-slate-500 w-16 shrink-0">{b.label}</span>
            <div className="flex-1 h-5 bg-slate-100 rounded-md overflow-hidden">
              <div
                className="h-full rounded-md transition-all"
                style={{ width: `${w}%`, backgroundColor: b.color, minWidth: value > 0 ? 6 : 0 }}
              />
            </div>
            <span className="text-xs font-semibold text-slate-700 w-7 text-right tabular-nums">{value}</span>
          </div>
        );
      })}
    </div>
  );
}

/* ── Summary stat tile ── */
function StatTile({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <Card>
      <CardContent className="py-4">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
        <p className="mt-1 text-2xl font-bold" style={{ color: accent ?? "#0f172a" }}>{value}</p>
      </CardContent>
    </Card>
  );
}

/* ── Pass-rate trend area chart ── */
type TrendPoint = { date: string; passed: number; failed: number; pass_rate: number };

function TrendAreaChart({ trends }: { trends: TrendPoint[] }) {
  const W = 640;
  const H = 180;
  const PAD = 28;

  if (trends.length === 0) {
    return <p className="py-8 text-center text-sm text-slate-500">No trend data available yet.</p>;
  }

  const n = trends.length;
  const innerW = W - PAD * 2;
  const innerH = H - PAD * 2;
  const x = (i: number) => (n === 1 ? W / 2 : PAD + (i / (n - 1)) * innerW);
  const y = (rate: number) => PAD + innerH - (Math.min(Math.max(rate, 0), 100) / 100) * innerH;

  const linePoints = trends.map((t, i) => `${x(i)},${y(t.pass_rate)}`).join(" ");
  const areaPath = `M ${x(0)},${H - PAD} L ${linePoints.split(" ").join(" L ")} L ${x(n - 1)},${H - PAD} Z`;

  return (
    <div className="w-full overflow-x-auto">
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label="Pass rate trend" className="min-w-[480px]">
        {/* gridlines at 0/50/100% */}
        {[0, 50, 100].map((g) => (
          <g key={g}>
            <line x1={PAD} y1={y(g)} x2={W - PAD} y2={y(g)} stroke="#f1f5f9" strokeWidth={1} />
            <text x={4} y={y(g) + 3} fontSize={9} fill="#94a3b8">{g}%</text>
          </g>
        ))}
        <defs>
          <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill="url(#trendFill)" />
        <polyline points={linePoints} fill="none" stroke="#10b981" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        {trends.map((t, i) => (
          <circle key={i} cx={x(i)} cy={y(t.pass_rate)} r={3} fill="#10b981" stroke="#fff" strokeWidth={1.5}>
            <title>{`${t.date}: ${Math.round(t.pass_rate)}% (${t.passed}P / ${t.failed}F)`}</title>
          </circle>
        ))}
      </svg>
    </div>
  );
}

/* ── Browser / environment breakdown ── */
function BrowserBreakdown({ reports }: { reports: ExecutionJobSummary[] }) {
  const byBrowser = new Map<string, { passed: number; total: number }>();
  for (const r of reports) {
    const key = r.browser || "unknown";
    const cur = byBrowser.get(key) ?? { passed: 0, total: 0 };
    cur.total += 1;
    if (bucketOf(r.status) === "passed") cur.passed += 1;
    byBrowser.set(key, cur);
  }
  const rows = [...byBrowser.entries()];
  if (rows.length === 0) {
    return <p className="py-6 text-center text-sm text-slate-500">No environment data.</p>;
  }
  return (
    <div className="space-y-3">
      {rows.map(([name, v]) => {
        const pct = v.total ? Math.round((v.passed / v.total) * 100) : 0;
        return (
          <div key={name} className="flex items-center gap-3">
            <span className="text-xs font-medium text-slate-600 w-20 shrink-0 capitalize truncate">{name}</span>
            <div className="flex-1 h-5 bg-slate-100 rounded-md overflow-hidden">
              <div className="h-full rounded-md bg-emerald-500 transition-all" style={{ width: `${pct}%`, minWidth: v.passed ? 6 : 0 }} />
            </div>
            <span className="text-xs text-slate-500 w-20 text-right tabular-nums">{v.passed}/{v.total} · {pct}%</span>
          </div>
        );
      })}
    </div>
  );
}

/* ── Dashboard composition ── */
export function ReportsDashboard({
  reports,
  trends,
}: {
  reports: ExecutionJobSummary[];
  trends: TrendPoint[];
}) {
  const counts = countStatuses(reports);
  const passRate = counts.total ? Math.round((counts.passed / counts.total) * 100) : 0;
  const durations = reports.map((r) => r.duration_seconds ?? 0).filter((d) => d > 0);
  const avgDur = durations.length ? durations.reduce((a, b) => a + b, 0) / durations.length : 0;
  const avgLabel = avgDur === 0 ? "—" : avgDur < 60 ? `${Math.round(avgDur)}s` : `${Math.floor(avgDur / 60)}m ${Math.round(avgDur % 60)}s`;

  return (
    <div className="space-y-4">
      {/* Summary tiles */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Total Runs" value={counts.total} />
        <StatTile label="Passed" value={counts.passed} accent={COLOR.passed} />
        <StatTile label="Failed" value={counts.failed + counts.broken} accent={COLOR.failed} />
        <StatTile label="Pass Rate" value={`${passRate}%`} accent={passRate >= 80 ? COLOR.passed : passRate >= 50 ? COLOR.broken : COLOR.failed} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Donut + legend */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-700">Status Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {counts.total === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">No executions to chart yet.</p>
            ) : (
              <div className="flex items-center gap-6 flex-wrap">
                <StatusDonut counts={counts} />
                <DonutLegend counts={counts} />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Status bar chart */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-700">Results by Status</CardTitle>
          </CardHeader>
          <CardContent className="pt-2">
            <StatusBarChart counts={counts} />
            <div className="mt-4 pt-4 border-t border-slate-100">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400 mb-3">Avg Duration</p>
              <p className="text-lg font-semibold text-slate-900">{avgLabel}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Trend */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-700">Pass Rate Trend (30 days)</CardTitle>
          </CardHeader>
          <CardContent>
            <TrendAreaChart trends={trends} />
          </CardContent>
        </Card>

        {/* Browser / environment */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-700">Pass Rate by Browser</CardTitle>
          </CardHeader>
          <CardContent className="pt-2">
            <BrowserBreakdown reports={reports} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
