"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend
} from "recharts";
import { HargaBerasSchema, StepDetail } from "@/types/api";

interface ForecastChartProps {
  historicalData: HargaBerasSchema[];
  predictions?: StepDetail[];
  height?: number;
}

interface ChartDataPoint {
  date: string;
  price: number | null;
  predicted: number | null;
  prophet: number | null;
}

export function ForecastChart({ historicalData, predictions = [], height = 400 }: ForecastChartProps) {
  // Combine historical and prediction data
  const data: ChartDataPoint[] = [...historicalData].map(d => ({
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
      const match = data.find(d => d.date === lastHist.date);
      if (match) {
        match.predicted = lastHist.price;
        match.prophet = lastHist.price;
      }
    }
  }

  const formatYAxis = (tickItem: number) => {
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
        <LineChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
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
            tickFormatter={formatYAxis}
            stroke="var(--muted-foreground)"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            dx={-10}
          />
          <Tooltip 
            formatter={(value: any) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(value)}
            labelFormatter={(label) => formatDate(label as string)}
            contentStyle={{ backgroundColor: "var(--card)", borderColor: "var(--border)", borderRadius: "8px", color: "var(--card-foreground)" }}
          />
          <Legend wrapperStyle={{ paddingTop: "20px" }} />
          <Line
            type="monotone"
            dataKey="price"
            name="Harga Aktual"
            stroke="var(--chart-5)"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6 }}
          />
          {predictions.length > 0 && (
            <>
              <Line
                type="monotone"
                dataKey="prophet"
                name="Prophet Base"
                stroke="var(--chart-3)"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="predicted"
                name="Hybrid Forecast"
                stroke="var(--primary)"
                strokeWidth={3}
                dot={{ r: 4, strokeWidth: 2 }}
                activeDot={{ r: 8 }}
              />
            </>
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
