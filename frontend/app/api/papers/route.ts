import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.API_BASE_URL;

export async function GET(req: NextRequest) {
  if (!API_BASE) {
    return NextResponse.json({ error: "Missing API_BASE_URL in env" }, { status: 500 });
  }
  const url = new URL(req.url);
  const search   = url.searchParams.get("search")   ?? "";
  const sources  = url.searchParams.get("sources")  ?? "";
  const tags     = url.searchParams.get("tags")     ?? "";
  const page     = url.searchParams.get("page")     ?? "1";
  const pageSize = url.searchParams.get("pageSize") ?? "20";

  const backendUrl = new URL(API_BASE + "/papers");
  if (search)  backendUrl.searchParams.set("search", search);
  if (sources) backendUrl.searchParams.set("sources", sources);
  if (tags)    backendUrl.searchParams.set("tags", tags);
  backendUrl.searchParams.set("page", page);
  backendUrl.searchParams.set("page_size", pageSize);

  const headers: Record<string, string> = { accept: "application/json" };
  if (process.env.API_TOKEN) headers["authorization"] = `Bearer ${process.env.API_TOKEN}`;

  const resp = await fetch(backendUrl.toString(), { headers });
  if (!resp.ok) {
    const text = await resp.text();
    return NextResponse.json({ error: text || resp.statusText }, { status: resp.status });
  }
  const data = await resp.json();
  return NextResponse.json(data);
}
