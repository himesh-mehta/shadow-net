"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { WS_URL } from "./api";

export type WebSocketStatus = "OPEN" | "CONNECTING" | "DISCONNECTED" | "UNAVAILABLE";

export function useDetectionWebSocket(sessionId: string | null) {
  const socket = useRef<WebSocket | null>(null);
  const [generation, setGeneration] = useState(0);
  const [status, setStatus] = useState<WebSocketStatus>("CONNECTING");
  const [lastMessage, setLastMessage] = useState<any>(null);
  const [connectionError, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    let alive = true;
    setStatus("CONNECTING");

    const ws = new WebSocket(`${WS_URL}/ws/detection/${encodeURIComponent(sessionId)}`);
    socket.current = ws;

    ws.onopen = () => {
      if (alive) {
        setStatus("OPEN");
        setError(null);
      }
    };

    ws.onmessage = (event) => {
      if (alive) {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type !== "pong") setLastMessage(msg);
          if (msg.type === "error") setError(msg.message);
        } catch {
          setError("Invalid telemetry packet");
        }
      }
    };

    ws.onerror = () => {
      if (alive) {
        setStatus("UNAVAILABLE");
        setError("Telemetry connection failed. Check the backend.");
      }
    };

    ws.onclose = () => {
      if (alive) setStatus("DISCONNECTED");
    };

    const ping = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 15000);

    return () => {
      alive = false;
      clearInterval(ping);
      ws.close();
      socket.current = null;
    };
  }, [sessionId, generation]);

  const sendAudioChunk = useCallback((audio_base64: string) => {
    if (socket.current?.readyState === WebSocket.OPEN) {
      socket.current.send(JSON.stringify({ type: "audio_chunk", audio_base64 }));
    }
  }, []);

  return {
    status,
    lastMessage,
    connectionError,
    reconnect: () => setGeneration((n) => n + 1),
    sendAudioChunk,
  };
}
