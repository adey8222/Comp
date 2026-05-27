# Compensation Intelligence Platform (CIP)

Internal MVP for compensation planning: spreadsheet import, column auto-mapping, normalization (including Excel dates and “new salary vs increment” fix), USD conversion with configurable stub FX rates, and rule-based bonus / raise **recommendation ranges**. UI includes dashboard aggregates, employee directory, department rollup, and CSV/XLSX export.

## Stack

- **Next.js 15** (App Router) + React 19 + TypeScript  
- **SQLite** locally by default (**Prisma** — `prisma/dev.db`); optional **PostgreSQL** via Docker for prod-like setups  
- **SheetJS (`xlsx`)** for CSV/XLS/XLSX parsing  

## Quick start (SQLite — no Docker)

1. **Configure env**

   ```bash
   cp .env.example .env
   ```

   Default `DATABASE_URL` is `file:./dev.db` (path is relative to the `prisma/` directory).

2. **Install & tables**

   ```bash
   npm install
   npm run db:push
   ```

3. **Dev server**

   ```bash
   npm run dev
   ```

   Open [http://localhost:3000/dashboard](http://localhost:3000/dashboard).

4. **Import data**: **Import → Commit import** with your workbook (e.g. `compensation_employee_dataset_updated.xlsx`).

## Deploy (Vercel — updates with every push)

1. Push this project to **GitHub** (or GitLab / Bitbucket — Vercel supports those too).
2. Import the repo in **[Vercel](https://vercel.com/new)** and connect Git. **Every commit** gets a **Preview** URL; merges to Production update the live site — same behaviour as projects that expose a README “Deploy” badge.
3. **Environment variables on Vercel** (minimum):
   - `DATABASE_URL` — hosted **Postgres** (Neon, Supabase, RDS). SQLite is not suitable on serverless hosts.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new)

After the repo exists: `https://vercel.com/new/clone?repository-url=https://github.com/YOUR_ORG/YOUR_REPO`

## Deploy (Streamlit Community Cloud)

Streamlit runs a **Python** edition of CIP (upload + dashboard in-session). It does **not** replace the Next.js app.

**Push these files to GitHub:**

| File | Required |
|------|----------|
| `streamlit_app.py` | Yes — main file on [share.streamlit.io](https://share.streamlit.io) |
| `requirements.txt` | Yes — Python dependencies |
| `cip_normalize.py` | Yes — import / FX / rules |
| `cip_dashboard.py` | Yes — dashboard stats / tables |
| `data/compensation_employee_dataset_updated.xlsx` | Yes — auto-loaded on startup (no manual import) |
| `.streamlit/config.toml` | Optional — theme |
| `packages.txt` | Optional — only if you need `apt-get` system libs |

Full checklist: [docs/STREAMLIT_GITHUB.md](docs/STREAMLIT_GITHUB.md)

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Optional: PostgreSQL (Docker Desktop)

1. `docker compose up -d`  
2. In `prisma/schema.prisma`, set `provider = "postgresql"` and restore `@db.Decimal(...)` on money fields if you need strict Postgres types.  
3. Set `DATABASE_URL="postgresql://cip:cip@localhost:5432/cip?schema=public"` in `.env`  
4. `npm run db:push` and restart `npm run dev`

## Dev auth / roles (until SSO)

`.env` controls a placeholder session:

- `DEV_ROLE`: `HR_ADMIN` | `MANAGER` | `EXECUTIVE`
- `DEV_MANAGER_DEPARTMENT`: exact department name when role is `MANAGER`

In non-production you can also send header `x-cip-role: MANAGER` on API calls.

## FX rates

By default, **stub** USD-per-unit rates apply (see `src/lib/fx.ts`). Override for testing:

```bash
FX_RATES_STUB="ILS=0.27,EUR=1.09"
```

Production should use a trusted FX API + nightly job (not included in MVP).

## Standard schema & mapping

Target columns match the PRD; headers like `Departments`, `Office Locations`, and `Email` map automatically (`src/lib/normalize.ts`).

Optional column **`Performance band`** (aliases: `Performance score`) drives recommendations: `HIGH`, `AVERAGE`, `LOW` (case-insensitive). If omitted, **`AVERAGE`** is assumed.

**Note:** With SQLite, employee search filters are **case-sensitive**; use Postgres for case-insensitive `contains` if you need it.

## API (JSON unless noted)

| Method | Path | Notes |
|--------|------|--------|
| GET | `/api/stats` | Dashboard aggregates |
| GET | `/api/employees` | Query `q`, `limit` |
| POST | `/api/import/preview` | `multipart/form-data` field `file` |
| POST | `/api/import/commit` | HR_ADMIN only; **merges** by company email (updates/creates rows in file only) |
| GET | `/api/export?format=xlsx` or `csv` | Stream download |

## What's not in MVP

Google Sheets OAuth/scheduled sync UI, S3 storage, full SSO, granular approval workflow, and production-grade FX — all called out in your PRD as next steps.

## Scripts

| Script | Purpose |
|--------|---------|
| `npm run dev` | Dev server |
| `npm run build` | Production build |
| `npm run db:push` | Sync Prisma schema to DB |
| `npm run db:studio` | Prisma Studio |
