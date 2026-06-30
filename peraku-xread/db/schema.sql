-- Run this in your Supabase SQL editor to initialise the schema.

create extension if not exists "pgcrypto";

-- ── Cases ──────────────────────────────────────────────────────────────────
create table if not exists cases (
  id            uuid primary key default gen_random_uuid(),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),

  user_type     text not null check (user_type in ('Employee','Businessman','Hybrid')),
  status        text not null default 'draft'
                  check (status in ('draft','docs_uploaded','reviewed','profiled','report_ready','paid')),

  -- Customer KYC snapshot (non-sensitive summary only)
  customer_age        int,
  customer_profession text,
  customer_location   text,
  declared_income     numeric(12,2),

  -- Pipeline outputs (JSONB for flexibility)
  doc_results     jsonb default '[]',
  review_result   jsonb default '{}',
  credit_result   jsonb default '{}',
  report_summary  jsonb default '{}',

  -- Payment
  stripe_session_id   text,
  paid_at             timestamptz,

  -- Report delivery
  report_storage_path text   -- path in Supabase Storage bucket "reports"
);

-- ── Auto-update updated_at ─────────────────────────────────────────────────
create or replace function update_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger cases_updated_at
  before update on cases
  for each row execute function update_updated_at();

-- ── RLS (enable and lock down to service role for now) ─────────────────────
alter table cases enable row level security;

-- Service-role key bypasses RLS automatically; no policies needed for backend-only access.
-- Add user-scoped policies here once auth is wired up.
