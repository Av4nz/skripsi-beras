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
import { HargaBerasSchema, StepDetail } from "@/types/api";
import { cn } from "@/lib/utils";
import {
  axisTick,
  ChartTooltip,
  legendFormatter,
  monthShort,
  rupiahCompact,
} from "@/components/charts/chart-theme";

interface ForecastChartProps {
  historicalData: HargaBerasSchema[];
  predictions?: StepDetail[];
  className?: string;
}

interface ChartDataPoint {
  date: string;
  price: number | null;
  predicted: number | null;
  prophet: number | null;
}

export function ForecastChart({
  historicalData,
  predictions = [],
  className,
}: ForecastChartProps) {
  const data: ChartDataPoint[] = [...historicalData].map((d) => ({
    date: d.date,
    price: d.price,
    predicted: null,
    prophet: null,
  }));

  if (predictions.length > 0) {
    predictions.forEach((p) => {
      data.push({
        date: p.date,
        price: null,
        predicted: p.final_prediction,
        prophet: p.yhat,
      });
    });

    // Connect the line from last historical point to first prediction
    if (historicalData.length > 0) {
      const lastHist = historicalData[historicalData.length - 1];
      const match = data.find((d) => d.date === lastHist.date);
      if (match) {
        match.predicted = lastHist.price;
        match.prophet = lastHist.price;
      }
    }
  }

  return (
    <div className={cn("h-[300px] w-full sm:h-[400px]", className)}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 4, bottom: 8 }}>
          <defs>
            <linearGradient id="forecastActualFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-5)" stopOpacity={0.18} />
              <stop offset="100%" stopColor="var(--chart-5)" stopOpacity={0} />
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
            name="Harga Aktual"
            stroke="var(--chart-5)"
            strokeWidth={2}
            fill="url(#forecastActualFill)"
            dot={false}
            activeDot={{ r: 5, strokeWidth: 0 }}
            connectNulls
          />
          {predictions.length > 0 && (
            <>
              <Line
                type="monotone"
                dataKey="prophet"
                name="Prophet (baseline)"
                stroke="var(--accent)"
                strokeWidth={2}
                strokeDasharray="5 4"
                dot={false}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="predicted"
                name="Prediksi Hybrid"
                stroke="var(--primary)"
                strokeWidth={2.5}
                dot={{ r: 3, strokeWidth: 0, fill: "var(--primary)" }}
                activeDot={{ r: 6, strokeWidth: 0 }}
                connectNulls
              />
            </>
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
