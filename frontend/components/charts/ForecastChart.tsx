"use client";

import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { HargaJenisPoint, StepDetail } from "@/types/api";
import { cn } from "@/lib/utils";
import {
  axisTick,
  ChartTooltip,
  domainHarga,
  legendFormatter,
  monthShort,
  rupiahAxis,
} from "@/components/charts/chart-theme";

// Biru sedang, terbaca pada tema terang dan gelap. Prophet memakai aksen cokelat, jadi ARIMA tidak boleh sama.
const WARNA_ARIMA = "#4F8BB5";

export interface ComparisonPoint {
  date: string;
  naive: number;
  arima: number;
}

interface ForecastChartProps {
  historicalData: HargaJenisPoint[];
  predictions?: StepDetail[];
  /** Pembanding sederhana (opsional): harga bulan ini dipertahankan dan ARIMA. */
  comparison?: ComparisonPoint[];
  className?: string;
}

interface ChartDataPoint {
  date: string;
  price: number | null;
  predicted: number | null;
  prophet: number | null;
  naive: number | null;
  arima: number | null;
}

export function ForecastChart({
  historicalData,
  predictions = [],
  comparison = [],
  className,
}: ForecastChartProps) {
  const data: ChartDataPoint[] = [...historicalData].map((d) => ({
    date: d.date,
    price: d.price,
    predicted: null,
    prophet: null,
    naive: null,
    arima: null,
  }));

  if (predictions.length > 0) {
    const cmp = new Map(comparison.map((c) => [c.date, c]));
    predictions.forEach((p) => {
      const c = cmp.get(p.date);
      data.push({
        date: p.date,
        price: null,
        predicted: p.final_prediction,
        prophet: p.yhat,
        naive: c ? c.naive : null,
        arima: c ? c.arima : null,
      });
    });

    // Connect the line from last historical point to first prediction
    if (historicalData.length > 0) {
      const lastHist = historicalData[historicalData.length - 1];
      const match = data.find((d) => d.date === lastHist.date);
      if (match) {
        match.predicted = lastHist.price;
        match.prophet = lastHist.price;
        if (comparison.length > 0) {
          match.naive = lastHist.price;
          match.arima = lastHist.price;
        }
      }
    }
  }

  return (
    <div className={cn("h-[300px] w-full min-w-0 overflow-hidden sm:h-[400px]", className)}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 4, bottom: 8 }}>
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
            domain={domainHarga}
            allowDecimals={false}
            tickFormatter={rupiahAxis}
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            width={56}
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
          <Line
            type="monotone"
            dataKey="price"
            name="Harga Aktual"
            stroke="var(--chart-5)"
            strokeWidth={2.5}
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
              {comparison.length > 0 && (
                <>
                  <Line
                    type="monotone"
                    dataKey="naive"
                    name="Harga bulan ini dipertahankan"
                    stroke="var(--muted-foreground)"
                    strokeWidth={2}
                    strokeDasharray="2 4"
                    dot={{ r: 4, strokeWidth: 0, fill: "var(--muted-foreground)" }}
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="arima"
                    name="ARIMA"
                    stroke={WARNA_ARIMA}
                    strokeWidth={2}
                    strokeDasharray="8 3"
                    dot={{ r: 4, strokeWidth: 0, fill: WARNA_ARIMA }}
                    connectNulls
                  />
                </>
              )}
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
