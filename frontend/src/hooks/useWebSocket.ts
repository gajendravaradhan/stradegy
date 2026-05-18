import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

export function useWebSocket() {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    const connect = () => {
      try {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const ws = new WebSocket(`${protocol}//${window.location.host}/api/ws`);

        ws.onopen = () => {
          console.log("[WS] Connected");
          const pingInterval = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send("ping");
            }
          }, 30000);
          (ws as any)._pingInterval = pingInterval;
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "portfolio_update") {
              queryClient.invalidateQueries({ queryKey: ["portfolio"] });
            } else if (data.type === "alerts_update") {
              queryClient.invalidateQueries({ queryKey: ["alerts"] });
            } else if (data.type === "metrics_update") {
              queryClient.invalidateQueries({ queryKey: ["portfolio-metrics"] });
            }
          } catch (_nonJson) {}
        };

        ws.onclose = () => {
          console.log("[WS] Disconnected, reconnecting in 5s...");
          if ((ws as any)._pingInterval) {
            clearInterval((ws as any)._pingInterval);
          }
          reconnectTimeoutRef.current = setTimeout(connect, 5000);
        };

        ws.onerror = (err) => {
          console.error("[WS] Error:", err);
          ws.close();
        };

        wsRef.current = ws;
      } catch (e) {
        console.error("[WS] Failed to connect:", e);
        reconnectTimeoutRef.current = setTimeout(connect, 5000);
      }
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [queryClient]);
}
