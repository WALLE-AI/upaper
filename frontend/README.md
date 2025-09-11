# PaperScope Next (Demo)

A minimal Next.js 14 + Tailwind CSS project that recreates a paper discovery UI similar to the screenshot you provided.

## Quick Start

```bash
# 1) Install deps
pnpm i   # or: npm i  /  yarn

# 2) Dev
pnpm dev # http://localhost:3000

# 3) Build & Start
pnpm build && pnpm start
```

## Stack

- Next.js 14 (App Router, TypeScript)
- Tailwind CSS
- lucide-react icons

## Structure

```
app/
  layout.tsx     # Global shell
  page.tsx       # Main paper list page (client-side filters/search)
  globals.css
components/
  Header.tsx
  SidebarFilters.tsx
  PaperCard.tsx
  Badge.tsx
lib/
  data.ts        # Mock data & taxonomy
```

This is a static demo without backend; you can wire it to your API later.
