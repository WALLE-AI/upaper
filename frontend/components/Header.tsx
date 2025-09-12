"use client";
import { Search, Filter } from "lucide-react";
export default function Header({ q, onSearch }:{ q:string; onSearch:(s:string)=>void }){
  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="container-pg flex items-center gap-4 py-4">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-brand-600 grid place-items-center text-white font-bold">P</div>
          <div className="text-lg font-semibold">uPaper</div>
          <span className="ml-2 text-sm text-gray-500">AI学术论文平台</span>
        </div>
        <div className="ml-auto flex items-center gap-3 w-full sm:w-[520px]">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              value={q}
              onChange={e=>onSearch(e.target.value)}
              placeholder="搜索论文标题、关键字..."
              className="w-full rounded-xl border border-gray-300 bg-white py-2 pl-9 pr-3 text-sm outline-none ring-brand-500 focus:ring-2"
            />
          </div>
          <button className="btn-ghost"><Filter className="h-4 w-4" />筛选</button>
        </div>
      </div>
    </header>
  );
}
