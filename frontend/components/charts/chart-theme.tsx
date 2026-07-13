"use client";

export const rupiah = (v: number) =>
  new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(v);

export const rupiahCompact = (v: number) =>
  new Intl.NumberFormat("id-ID", {
    notation: "compact",
    compactDisplay: "short",
  }).format(v);

export const monthShort = (dateStr: string) => {
  const d = new Date(dateStr);
  return new Intl.DateTimeFormat("id-ID", { month: "short", year: "2-digit" }).format(d);
};

export const axisTick = { fill: "var(--muted-foreground)", fontSize: 12 } as const;

export const legendFormatter = (value: string) => (
  <span className="text-sm text-muted-foreground">{value}</span>
);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function ChartTooltip({ active, payload, label, valueFormat = rupiah }: any) {
  if (!active || !payload?.length) return null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const rows = payload.filter((p: any) => p.value !== null && p.value !== undefined);
  if (!rows.length) return null;

  return (
    <div className="rounded-xl border border-border bg-card/95 px-3.5 py-2.5 shadow-lg shadow-foreground/5 backdrop-blur-sm">
      <p className="mb-1.5 text-xs font-semibold text-foreground">{monthShort(label)}</p>
      <ul className="space-y-1">
        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
        {rows.map((p: any) => (
          <li key={p.dataKey} className="flex items-center gap-2 text-xs">
            <span
              className="size-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: p.color }}
            />
            <span className="text-muted-foreground">{p.name}</span>
            <span className="ml-auto pl-3 font-semibold tabular-nums text-foreground">
              {valueFormat(Number(p.value))}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
