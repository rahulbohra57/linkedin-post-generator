import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "https://linkedin-post-generator-api.onrender.com";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(30000),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ status: "unreachable" }, { status: 503 });
  }
}
