"use client";
import { useEffect, useMemo, useState } from "react";
import Header from "@/components/Header";
import SidebarFilters, { type FilterState } from "@/components/SidebarFilters";
import PaperCard from "@/components/PaperCard";
import { fetchPapers } from "@/lib/api";
import type { Paper } from "@/lib/types";
import { useDebounce } from "@/lib/useDebounce";

export default function Page() {
  const [q, setQ] = useState("");
  const [filters, setFilters] = useState<FilterState>({ sources: [], tags: [] });
  const [items, setItems] = useState<Paper[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dq = useDebounce(q, 400);
  const query = useMemo(() => ({
    search: dq || undefined,
    sources: filters.sources.length ? filters.sources : undefined,
    tags: filters.tags.length ? filters.tags : undefined,
    page: 1,
    pageSize: 20
  }), [dq, filters]);

  useEffect(() => {
    let aborted = false;
    (async () => {
      setLoading(true); setError(null);
      try {
        const res = await fetchPapers(query);
        if (!aborted) { setItems(res.items); setTotal(res.total); }
      } catch (e:any) {
        if (!aborted) setError(e?.message ?? "请求失败");
      } finally {
        if (!aborted) setLoading(false);
      }
    })();
    return () => { aborted = true; };
  }, [query]);

  return (
    <div className="min-h-screen flex flex-col">
      <Header q={q} onSearch={setQ} />
      <main className="container-pg grid grid-cols-1 lg:grid-cols-[260px,1fr] gap-6 py-6">
        <SidebarFilters state={filters} onChange={setFilters} />
        <section className="space-y-4">
          <div className="flex items-baseline justify-between">
            <div>
              <h2 className="text-xl font-semibold">论文数据库</h2>
              <p className="muted text-sm">发现 {total} 篇筛选论文</p>
            </div>
          </div>
          {error && <div className="card p-4 text-red-600 text-sm">请求出错：{error}</div>}
          {loading && <div className="card p-4 text-sm text-gray-500">加载中…</div>}
          <div className="space-y-4">
            {items.map(p => <PaperCard key={p.id} p={p} />)}
            {!loading && items.length === 0 && !error && (
              <div className="card p-10 text-center text-gray-500">未找到结果，请调整筛选条件。</div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
