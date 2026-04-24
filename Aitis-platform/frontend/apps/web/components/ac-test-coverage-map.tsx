"use client";

import { Badge } from "@/components/ui/badge";
import type { TestCase } from "@/lib/types";

type CoverageMapProps = {
  acceptanceCriteria: string[];
  tests: TestCase[];
};

export function ACTestCoverageMap({
  acceptanceCriteria,
  tests,
}: CoverageMapProps) {
  if (!acceptanceCriteria.length) {
    return (
      <div className="rounded-2xl bg-slate-50 p-6 text-sm text-slate-500">
        No acceptance criteria defined.
      </div>
    );
  }

  function testsCoveringAc(acIndex: number): TestCase[] {
    const acId = `AC-${acIndex + 1}`;
    return tests.filter((test) =>
      test.coversAcceptanceCriteria?.includes(acId),
    );
  }

  return (
    <div className="space-y-4">
      {acceptanceCriteria.map((ac, index) => {
        const coveringTests = testsCoveringAc(index);

        return (
          <div
            key={index}
            className="rounded-3xl border border-slate-200 bg-white p-5"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <Badge tone={coveringTests.length ? "green" : "rose"}>
                    AC-{index + 1}
                  </Badge>
                  <span className="text-sm font-medium text-slate-900">
                    {ac}
                  </span>
                </div>
              </div>

              <Badge tone={coveringTests.length ? "green" : "rose"}>
                {coveringTests.length
                  ? `${coveringTests.length} test(s)`
                  : "Uncovered"}
              </Badge>
            </div>

            <div className="mt-4">
              {coveringTests.length ? (
                <div className="flex flex-wrap gap-2">
                  {coveringTests.map((test) => (
                    <Badge key={test.id} tone="slate">
                      {test.id}: {test.title}
                    </Badge>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-rose-600">
                  ⚠️ This acceptance criterion is not covered by any test.
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
``