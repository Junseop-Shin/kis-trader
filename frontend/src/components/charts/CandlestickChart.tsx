"use client";

import {
  createChart,
  ColorType,
  type IChartApi,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

interface CandlestickChartProps {
  data: {
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
  }[];
  overlays?: {
    name: string;
    data: { time: string; value: number }[];
    color: string;
  }[];
  markers?: {
    time: string;
    position: "belowBar" | "aboveBar";
    color: string;
    shape: "arrowUp" | "arrowDown" | "circle";
    text: string;
  }[];
  height?: number;
}

export function CandlestickChart({
  data,
  overlays = [],
  markers = [],
  height = 400,
}: CandlestickChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartRef.current || data.length === 0) return;

    // Clean up previous chart
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
      crosshair: {
        mode: 0,
      },
    });
    chartInstanceRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#ef4444",
      downColor: "#3b82f6",
      borderVisible: false,
      wickUpColor: "#ef4444",
      wickDownColor: "#3b82f6",
    });
    candleSeries.setData(data as any);

    if (markers.length > 0) {
      candleSeries.setMarkers(markers as any);
    }

    overlays.forEach((overlay) => {
      const lineSeries = chart.addLineSeries({
        color: overlay.color,
        lineWidth: 1,
      });
      lineSeries.setData(overlay.data as any);
    });

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
  }, [data, overlays, markers, height]);

  return <div ref={chartRef} />;
}
