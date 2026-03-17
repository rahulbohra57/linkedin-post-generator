import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "https://linkedin-post-generator-api.onrender.com";
const WAKE_TIMEOUT_MS = 60000; // 60s max to wait for backend to wake
const RETRY_INTERVAL_MS = 3000;

export async function GET() {
  const deadline = Date.now() + WAKE_TIMEOUT_MS;

  while (Date.now() < deadline) {
    try {
      const remaining = deadline - Date.now();
      const res = await fetch(`${BACKEND_URL}/health`, {
        cache: "no-store",
        signal: AbortSignal.timeout(Math.min(remaining, 10000)),
      });
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend sleeping or unreachable — retry
    }

    // Wait before retrying
    await new Promise((r) => setTimeout(r, RETRY_INTERVAL_MS));
  }

  return NextResponse.json({ status: "unreachable" }, { status: 503 });
}
