import { useEffect, useRef, useCallback } from "react";
import { Client, IMessage, StompSubscription } from "@stomp/stompjs";
import SockJS from "sockjs-client";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "http://localhost:8080";

interface UseWebSocketOptions {
  onTradeUpdate?: (data: unknown) => void;
  onMarketUpdate?: (data: unknown) => void;
  onBacktestResult?: (data: unknown) => void;
  userId?: string;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const clientRef = useRef<Client | null>(null);
  const subsRef = useRef<StompSubscription[]>([]);

  const { onTradeUpdate, onMarketUpdate, onBacktestResult, userId } = options;

  const handleMessage = useCallback(
    (topic: "trade" | "market" | "backtest") =>
      (message: IMessage) => {
        const data = JSON.parse(message.body);
        if (topic === "trade") onTradeUpdate?.(data);
        else if (topic === "market") onMarketUpdate?.(data);
        else if (topic === "backtest") onBacktestResult?.(data);
      },
    [onTradeUpdate, onMarketUpdate, onBacktestResult]
  );

  useEffect(() => {
    const client = new Client({
      webSocketFactory: () => new SockJS(`${WS_URL}/ws`),
      reconnectDelay: 5000,
      onConnect: () => {
        const subs: StompSubscription[] = [];

        subs.push(
          client.subscribe("/topic/market", handleMessage("market"))
        );

        if (userId) {
          subs.push(
            client.subscribe(`/user/${userId}/queue/trades`, handleMessage("trade"))
          );
          subs.push(
            client.subscribe(`/user/${userId}/queue/backtest`, handleMessage("backtest"))
          );
        }

        subsRef.current = subs;
      },
      onDisconnect: () => {
        subsRef.current = [];
      },
    });

    client.activate();
    clientRef.current = client;

    return () => {
      subsRef.current.forEach((sub) => sub.unsubscribe());
      client.deactivate();
    };
  }, [userId, handleMessage]);

  const send = useCallback((destination: string, body: unknown) => {
    clientRef.current?.publish({
      destination,
      body: JSON.stringify(body),
    });
  }, []);

  return { send };
}
