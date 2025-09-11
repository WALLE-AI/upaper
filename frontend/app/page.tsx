"use client";

import { useMemo, useState } from "react";
import Header from "@/components/Header";
import SidebarFilters, { type FilterState } from "@/components/SidebarFilters";
import PaperCard from "@/components/PaperCard";
import { PAPERS, type Paper } from "@/lib/data";

export default function Page() {
  const [q, setQ] = useState("");
  const [filters, setFilters] = useState<FilterState>({ sources: [], tags: [] });

  const filtered = useMemo(() => {
    let list: Paper[] = PAPERS;
    if (q.trim()) {
      const x = q.trim().toLowerCase();
      list = list.filter(p => p.title.toLowerCase().includes(x) || p.summary.toLowerCase().includes(x));
    }
    if (filters.sources.length) {
      list = list.filter(p => filters.sources.includes(p.source));
    }
    if (filters.tags.length) {
      list = list.filter(p => p.tags.some(t => filters.tags.includes(t)));
    }
    return list;
  }, [q, filters]);

  return (
    <div className="min-h-screen flex flex-col">
      <Header q={q} onSearch={setQ} />

      <main className="container-pg grid grid-cols-1 lg:grid-cols-[260px,1fr] gap-6 py-6">
        {/* Sidebar */}
        <SidebarFilters state={filters} onChange={setFilters} />

        {/* Content */}
        <section className="space-y-4">
          <div className="flex items-baseline justify-between">
            <div>
              <h2 className="text-xl font-semibold">论文数据库</h2>
              <p className="muted text-sm">发现 {filtered.length} 篇筛选论文</p>
            </div>
          </div>

          <div className="space-y-4">
            {filtered.map(p => <PaperCard key={p.id} p={p} />)}
            {filtered.length === 0 && (
              <div className="card p-10 text-center text-gray-500">未找到结果，请调整筛选条件。</div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
