"use client";

type AcceptanceCriteriaEditorProps = {
  items: string[];
  onChange: (items: string[]) => void;
  sourceText?: string;
  onApply?: () => void;
};

export function AcceptanceCriteriaEditor({
  items,
  onChange,
}: AcceptanceCriteriaEditorProps) {
  function updateItem(index: number, value: string) {
    const next = [...items];
    next[index] = value;
    onChange(next);
  }

  function removeItem(index: number) {
    onChange(items.filter((_, i) => i !== index));
  }

  function moveUp(index: number) {
    if (index === 0) return;
    const next = [...items];
    [next[index - 1], next[index]] = [next[index], next[index - 1]];
    onChange(next);
  }

  function moveDown(index: number) {
    if (index === items.length - 1) return;
    const next = [...items];
    [next[index + 1], next[index]] = [next[index], next[index + 1]];
    onChange(next);
  }

  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <div
          key={index}
          className="rounded-xl border border-slate-200 bg-white p-3"
        >
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-slate-700">
              AC-{index + 1}
            </span>

            <div className="flex gap-1">
              <button
                onClick={() => moveUp(index)}
                className="rounded-md border px-2 py-1 text-xs"
              >
                ↑
              </button>
              <button
                onClick={() => moveDown(index)}
                className="rounded-md border px-2 py-1 text-xs"
              >
                ↓
              </button>
              <button
                onClick={() => removeItem(index)}
                className="rounded-md border border-rose-200 px-2 py-1 text-xs text-rose-700"
              >
                Delete
              </button>
            </div>
          </div>

          <textarea
            value={item}
            onChange={(e) => updateItem(index, e.target.value)}
            rows={2}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
        </div>
      ))}
    </div>
  );
}
