"use client";
import { useEffect, useRef, useState, useCallback } from "react";

export type ProgressEvent =
  | { event: "pipeline_start"; agents: string[] }
  | { event: "agent_start"; agent: string }
  | { event: "agent_complete"; agent: string; output: string }
  | { event: "pipeline_done"; post_text: string; quality_score: number; hashtags: string }
  | { event: "error"; message: string };

export function useWebSocket(sessionId: string | null, enabled: boolean) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [isDone, setIsDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  // Track whether pipeline_done was received (ref avoids stale closure in onclose)
  const isDoneRef = useRef(false);
  // Track intentional client-side closes so we don't trigger polling on cleanup
  const closedRef = useRef(false);

  const connect = useCallback(() => {
    if (!sessionId || !enabled) return;

    closedRef.current = false;
    isDoneRef.current = false;

    const wsBase = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
    const ws = new WebSocket(`${wsBase}/ws/progress/${sessionId}`);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        const data: ProgressEvent = JSON.parse(e.data);
        setEvents((prev) => [...prev, data]);
        if (data.event === "pipeline_done" || data.event === "error") {
          isDoneRef.current = true;
          setIsDone(true);
          if (data.event === "error") setError(data.message);
        }
      } catch {}
    };

    let didOpen = false;
    ws.onopen = () => { didOpen = true; };
    // Only report errors on connections that actually opened — avoids false
    // positives from React Strict Mode closing the first connection while
    // it's still in CONNECTING state.
    ws.onerror = () => { if (didOpen) setError("WebSocket connection failed."); };
    // If the WS closes without pipeline_done (race condition or proxy timeout),
    // trigger the polling fallback so the UI doesn't hang indefinitely.
    ws.onclose = () => {
      if (!isDoneRef.current && !closedRef.current) {
        setError("WebSocket disconnected");
      }
    };
  }, [sessionId, enabled]);

  useEffect(() => {
    connect();
    return () => {
      closedRef.current = true;
      wsRef.current?.close();
    };
  }, [connect]);

  return { events, isDone, error };
}
