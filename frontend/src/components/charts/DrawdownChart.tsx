"use client";

import { createChart, ColorType, type IChartApi } from "lightweight-charts";
import { useEffect, useRef } from "react";

interface DrawdownChartProps {
  data: { time: string; value: number }[];
  height?: number;
}

export function DrawdownChart({ data, height = 200 }: DrawdownChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartRef.current || data.length === 0) return;

    if (chartInstanceRef.current) {
      chartInstanceRef.current.remove();
    }

    const chart = createChart(chartRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#1a1a1a" },
        textColor: "#d1d5db",
      },
      grid: {
        vertLines: { color: "#2d2d2d" },
        horzLines: { color: "#2d2d2d" },
      },
      width: chartRef.current.clientWidth,
      height,
    });
    chartInstanceRef.current = chart;

    const areaSeries = chart.addAreaSeries({
      topColor: "rgba(239, 68, 68, 0.2)",
      bottomColor: "rgba(239, 68, 68, 0.0)",
      lineColor: "#ef4444",
      lineWidth: 1,
    });
    areaSeries.setData(data as any);

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartRef.current) {
        chart.applyOptions({ width: chartRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartInstanceRef.current = null;
    };
  }, [data, height]);

  return <div ref={chartRef} />;
}
