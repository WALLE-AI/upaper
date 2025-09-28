-- schema.sql — Supabase schema & RLS for daily_papers
create extension if not exists pgcrypto;

create table if not exists public.daily_papers (
  id                uuid primary key default gen_random_uuid(),
  paper_id          text,
  title             text not null,
  source_url        text,
  huggingface_url   text,
  date              date,
  month_url         text not null,
  votes             integer,
  ai_keywords       text[] default '{}'::text[],
  ai_summary        text,
  meta              jsonb default '{}'::jsonb,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create unique index if not exists uq_daily_papers_paper_id on public.daily_papers(paper_id);
create unique index if not exists uq_daily_papers_title_source on public.daily_papers(title, source_url);
-- 常用索引（数组包含/重叠查询超好用）
create index if not exists idx_daily_papers_keywords_gin
  on public.daily_papers using gin (ai_keywords);

create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists trg_daily_papers_updated_at on public.daily_papers;
create trigger trg_daily_papers_updated_at
before update on public.daily_papers
for each row execute function public.set_updated_at();

-- 开启 RLS（若已开启可重复执行）
alter table public.daily_papers enable row level security;

-- 读策略：允许所有人读取（如果只想登录后才能读，把 to public 改成 to authenticated）
drop policy if exists "daily_papers_read_all" on public.daily_papers;
create policy "daily_papers_read_all"
on public.daily_papers for select
to public
using (true);

-- （可选）写策略：如果你希望 authenticated 可以插入/更新/删除，就启用下面三条
-- drop policy if exists "daily_papers_insert_auth" on public.daily_papers;
-- create policy "daily_papers_insert_auth"
-- on public.daily_papers for insert
-- to authenticated
-- with check (true);

-- drop policy if exists "daily_papers_update_auth" on public.daily_papers;
-- create policy "daily_papers_update_auth"
-- on public.daily_papers for update
-- to authenticated
-- using (true) with check (true);

-- drop policy if exists "daily_papers_delete_auth" on public.daily_papers;
-- create policy "daily_papers_delete_auth"
-- on public.daily_papers for delete
-- to authenticated
-- using (true);

-- 兜底：防“permission denied for schema public”
grant usage on schema public to anon, authenticated;
grant select on public.daily_papers to anon, authenticated;
