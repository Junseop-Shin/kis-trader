"use client";

import { createChart, ColorType, type IChartApi } from "lightweight-charts";
import { useEffect, useRef } from "react";

interface EquityChartProps {
  data: { time: string; value: number }[];
  benchmarkData?: { time: string; value: number }[];
  height?: number;
}

export function EquityChart({
  data,
  benchmarkData,
  height = 300,
}: EquityChartProps) {
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

    const portfolioSeries = chart.addLineSeries({
      color: "#3b82f6",
      lineWidth: 2,
      title: "Portfolio",
    });
    portfolioSeries.setData(data as any);

    if (benchmarkData && benchmarkData.length > 0) {
      const benchSeries = chart.addLineSeries({
        color: "#6b7280",
        lineWidth: 1,
        lineStyle: 2,
        title: "Benchmark",
      });
      benchSeries.setData(benchmarkData as any);
    }

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
  }, [data, benchmarkData, height]);

  return <div ref={chartRef} />;
}
