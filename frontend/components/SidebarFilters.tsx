"use client";
import { TAXONOMY } from "@/lib/data";
import { Badge } from "./Badge";

export type FilterState = { sources: string[]; tags: string[]; };

export default function SidebarFilters({ state, onChange }:{ state:FilterState; onChange:(next:FilterState)=>void; }){
  const remove = (type: keyof FilterState, value: string) => onChange({ ...state, [type]: state[type].filter(v => v !== value) });
  const toggle = (type: keyof FilterState, value: string) => {
    const set = new Set(state[type]); set.has(value) ? set.delete(value) : set.add(value);
    onChange({ ...state, [type]: Array.from(set) });
  };
  const activeCount = state.sources.length + state.tags.length;

  return (
    <aside className="space-y-4">
      <div className="card p-4">
        <div className="font-semibold mb-3">已选筛选（{activeCount}）</div>
        <div className="flex flex-wrap gap-2">
          {state.sources.map(s => <Badge key={s} variant="outline" onRemove={()=>remove("sources", s)}>{s}</Badge>)}
          {state.tags.map(t => <Badge key={t} variant="outline" onRemove={()=>remove("tags", t)}>{t}</Badge>)}
          {activeCount===0 && <div className="muted text-sm">暂无筛选条件</div>}
        </div>
      </div>
      <div className="card p-4">
        <Section title="论文来源">
          <div className="space-y-2">
            {TAXONOMY.sources.map(src => (
              <label key={src} className="flex items-center gap-2 text-sm">
                <input type="checkbox" className="checkbox" checked={state.sources.includes(src)} onChange={()=>toggle("sources", src)} />
                <span>{src}</span>
              </label>
            ))}
          </div>
        </Section>
      </div>
      <div className="card p-4">
        <Section title="相关性">
          <div className="grid grid-cols-2 gap-2">
            {TAXONOMY.tags.map(tag => (
              <label key={tag} className="flex items-center gap-2 text-sm">
                <input type="checkbox" className="checkbox" checked={state.tags.includes(tag)} onChange={()=>toggle("tags", tag)} />
                <span>{tag}</span>
              </label>
            ))}
          </div>
        </Section>
      </div>
    </aside>
  );
}
function Section({ title, children }:{ title:string; children:React.ReactNode }){
  return (<div className="space-y-3"><div className="text-sm font-semibold text-gray-700">{title}</div>{children}</div>);
}
