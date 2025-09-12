import type { PaperListResp, PaperQuery } from "./types";
function toComma(v?: string[]){ return (v && v.length) ? v.join(",") : ""; }
export async function fetchPapers(q: PaperQuery): Promise<PaperListResp> {
  const origin = typeof window === "undefined" ? "http://localhost" : window.location.origin;
  const url = new URL("/api/papers", origin);
  if (q.search)  url.searchParams.set("search", q.search);
  if (q.sources) url.searchParams.set("sources", toComma(q.sources));
  if (q.tags)    url.searchParams.set("tags", toComma(q.tags));
  url.searchParams.set("page", String(q.page ?? 1));
  url.searchParams.set("pageSize", String(q.pageSize ?? 20));
  const resp = await fetch(url.toString(), { cache: "no-store" });
  if (!resp.ok) throw new Error(await resp.text());
  return await resp.json();
}
