"use client";

import {
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
  Area,
  ComposedChart
} from "recharts";
import { HargaBerasSchema } from "@/types/api";

interface HistoricalChartProps {
  data: HargaBerasSchema[];
  height?: number;
}

export function HistoricalChart({ data, height = 400 }: HistoricalChartProps) {
  const formatYAxisPrice = (tickItem: number) => {
    return new Intl.NumberFormat("id-ID", {
      notation: "compact",
      compactDisplay: "short",
    }).format(tickItem);
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return new Intl.DateTimeFormat("id-ID", { month: "short", year: "2-digit" }).format(d);
  };

  return (
    <div style={{ width: "100%", height, minHeight: height}}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
          <XAxis 
            dataKey="date" 
            tickFormatter={formatDate}
            stroke="var(--muted-foreground)"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            dy={10}
          />
          <YAxis 
            yAxisId="left"
            tickFormatter={formatYAxisPrice}
            stroke="var(--muted-foreground)"
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <YAxis 
            yAxisId="right" 
            orientation="right"
            stroke="var(--muted-foreground)"
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip 
            labelFormatter={(label) => formatDate(label as string)}
            contentStyle={{ backgroundColor: "var(--card)", borderColor: "var(--border)", borderRadius: "8px", color: "var(--card-foreground)" }}
          />
          <Legend wrapperStyle={{ paddingTop: "20px" }} />
          
          <Area 
            yAxisId="left"
            type="monotone" 
            dataKey="harga_gkg" 
            name="Harga GKG" 
            fill="var(--chart-2)" 
            stroke="var(--chart-2)" 
            fillOpacity={0.2} 
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="price"
            name="Harga Beras"
            stroke="var(--chart-1)"
            strokeWidth={3}
            dot={false}
          />
          <Line
            yAxisId="right"
            type="step"
            dataKey="inflasi_pangan"
            name="Inflasi (%)"
            stroke="var(--chart-3)"
            strokeWidth={2}
            strokeDasharray="4 4"
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
