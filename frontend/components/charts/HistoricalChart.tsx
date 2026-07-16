"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { HargaBerasSchema } from "@/types/api";
import { cn } from "@/lib/utils";
import {
  axisTick,
  ChartTooltip,
  legendFormatter,
  monthShort,
  rupiahCompact,
} from "@/components/charts/chart-theme";

interface HistoricalChartProps {
  data: HargaBerasSchema[];
  className?: string;
}

export function HistoricalChart({ data, className }: HistoricalChartProps) {
  return (
    <div className={cn("h-[300px] w-full sm:h-[400px]", className)}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 4, bottom: 8 }}>
          <defs>
            <linearGradient id="histPriceFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.22} />
              <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="4 4"
            vertical={false}
            stroke="var(--border)"
            strokeOpacity={0.6}
          />
          <XAxis
            dataKey="date"
            tickFormatter={monthShort}
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            dy={8}
            minTickGap={24}
          />
          <YAxis
            tickFormatter={rupiahCompact}
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            width={44}
          />
          <Tooltip
            content={<ChartTooltip />}
            cursor={{ stroke: "var(--muted-foreground)", strokeOpacity: 0.3, strokeWidth: 1 }}
          />
          <Legend
            iconType="circle"
            iconSize={9}
            formatter={legendFormatter}
            wrapperStyle={{ paddingTop: 16 }}
          />
          <Area
            type="monotone"
            dataKey="price"
            name="Harga Beras"
            stroke="var(--chart-1)"
            strokeWidth={2.5}
            fill="url(#histPriceFill)"
            dot={false}
            activeDot={{ r: 5, strokeWidth: 0 }}
          />
          <Line
            type="monotone"
            dataKey="harga_gkg"
            name="Harga Gabah (GKG)"
            stroke="var(--accent)"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
