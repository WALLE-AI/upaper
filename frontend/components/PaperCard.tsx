import { Heart, MessageCircle } from "lucide-react";
import type { Paper } from "@/lib/types";
import { Badge } from "./Badge";

export default function PaperCard({ p }:{ p: Paper }){
  return (
    <article className="card p-5 hover:shadow-lg transition-shadow">
      <div className="flex items-center gap-2 text-xs text-brand-600 mb-1">
        <span className="pill">{p.source}</span>
      </div>
      <h3 className="text-[17px] font-semibold leading-snug mb-2">{p.title}</h3>
      <p className="text-sm text-gray-600 line-clamp-2 mb-4">{p.summary}</p>
      <div className="flex flex-wrap items-center gap-2">
        {p.badges?.map(b => <Badge key={b} variant="default">{b}</Badge>)}
      </div>
      <div className="mt-4 flex items-center gap-4 text-gray-500">
        <div className="inline-flex items-center gap-1"><Heart className="h-4 w-4" /><span className="text-xs">{p.likes}</span></div>
        <div className="inline-flex items-center gap-1"><MessageCircle className="h-4 w-4" /><span className="text-xs">{p.comments}</span></div>
      </div>
    </article>
  );
}
