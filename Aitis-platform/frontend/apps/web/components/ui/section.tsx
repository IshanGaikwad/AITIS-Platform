type SectionProps = {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
};

export function Section({ title, subtitle, action, children }: SectionProps) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
          {subtitle && (
            <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
          )}
        </div>

        {action ? <div>{action}</div> : null}
      </div>

      {/* Body */}
      <div className="px-6 py-5">{children}</div>
    </div>
  );
}