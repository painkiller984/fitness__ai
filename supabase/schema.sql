-- Run this once in the Supabase SQL editor.
-- The browser/server uses a publishable key plus the user's JWT; service_role is not required.

create table if not exists public.profiles (
    user_id uuid primary key references auth.users(id) on delete cascade,
    name text not null check (char_length(name) between 1 and 80),
    surname text check (char_length(surname) between 1 and 80),
    age integer not null check (age between 14 and 100),
    sex text not null check (sex in ('female', 'male')),
    height_cm numeric(5,1) not null check (height_cm between 120 and 230),
    weight_kg numeric(6,1) not null check (weight_kg between 35 and 350),
    goal text not null check (goal in ('weight_loss', 'muscle_gain', 'maintenance', 'wellbeing')),
    activity_level text not null check (activity_level in ('sedentary', 'light', 'moderate', 'high', 'very_high')),
    training_place text check (training_place in ('home', 'gym', 'both', 'outdoors')),
    training_experience text check (training_experience in ('beginner', 'intermediate', 'advanced')),
    training_days_per_week integer check (training_days_per_week between 1 and 7),
    available_equipment text[] not null default '{}',
    equipment_screened boolean not null default false,
    health_screened boolean not null default false,
    dietary_preferences text[] not null default '{}',
    allergies text[] not null default '{}',
    injuries text[] not null default '{}',
    medical_notes text not null default '',
    is_pregnant boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.progress_entries (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    measured_at date not null default current_date,
    weight_kg numeric(6,1) check (weight_kg between 35 and 350),
    waist_cm numeric(5,1) check (waist_cm between 30 and 250),
    sleep_hours numeric(3,1) check (sleep_hours between 0 and 24),
    steps integer check (steps between 0 and 100000),
    notes text not null default '',
    created_at timestamptz not null default now()
);

create table if not exists public.plans (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    kind text not null check (kind in ('nutrition', 'workout', 'combined')),
    status text not null default 'active' check (status in ('draft', 'active', 'archived')),
    payload jsonb not null,
    calculation_version text not null default 'mifflin-v1',
    judge_result jsonb,
    created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.progress_entries enable row level security;
alter table public.plans enable row level security;

revoke all on public.profiles, public.progress_entries, public.plans from anon;
grant select, insert, update, delete on public.profiles, public.progress_entries, public.plans to authenticated;
grant usage, select on all sequences in schema public to authenticated;

drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own" on public.profiles for select to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own" on public.profiles for insert to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own" on public.profiles for update to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "profiles_delete_own" on public.profiles;
create policy "profiles_delete_own" on public.profiles for delete to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "progress_all_own" on public.progress_entries;
create policy "progress_all_own" on public.progress_entries for all to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "plans_all_own" on public.plans;
create policy "plans_all_own" on public.plans for all to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

-- Anonymous profile memory. Enable Anonymous Sign-Ins in Supabase Auth before using it.
create table if not exists public.anonymous_profiles (
    user_id uuid primary key references auth.users(id) on delete cascade,
    name text check (char_length(name) between 1 and 80),
    surname text check (char_length(surname) between 1 and 80),
    age integer check (age between 14 and 100),
    sex text check (sex in ('female', 'male')),
    height_cm numeric(5,1) check (height_cm between 120 and 230),
    weight_kg numeric(6,1) check (weight_kg between 35 and 350),
    goal text check (goal in ('weight_loss', 'muscle_gain', 'maintenance', 'wellbeing')),
    activity_level text check (activity_level in ('sedentary', 'light', 'moderate', 'high', 'very_high')),
    training_place text check (training_place in ('home', 'gym', 'both', 'outdoors')),
    training_experience text check (training_experience in ('beginner', 'intermediate', 'advanced')),
    training_days_per_week integer check (training_days_per_week between 1 and 7),
    available_equipment text[] not null default '{}',
    equipment_screened boolean not null default false,
    health_screened boolean not null default false,
    medical_notes text not null default '',
    is_pregnant boolean not null default false,
    dietary_preferences text[] not null default '{}',
    allergies text[] not null default '{}',
    injuries text[] not null default '{}',
    target_kcal integer check (target_kcal between 800 and 7000),
    protein_g integer check (protein_g between 20 and 500),
    fat_g integer check (fat_g between 10 and 300),
    carbs_g integer check (carbs_g between 20 and 1000),
    last_active_at timestamptz not null default now(),
    expires_at timestamptz not null default now() + interval '30 days',
    deletion_requested_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.anonymous_profiles enable row level security;
alter table public.profiles alter column training_place drop not null;
alter table public.profiles drop constraint if exists profiles_training_place_check;
alter table public.profiles add constraint profiles_training_place_check
    check (training_place in ('home', 'gym', 'both', 'outdoors'));
alter table public.profiles add column if not exists training_experience text
    check (training_experience in ('beginner', 'intermediate', 'advanced'));
alter table public.profiles add column if not exists training_days_per_week integer
    check (training_days_per_week between 1 and 7);
alter table public.profiles add column if not exists available_equipment text[] not null default '{}';
alter table public.profiles add column if not exists equipment_screened boolean not null default false;
alter table public.profiles add column if not exists health_screened boolean not null default false;
alter table public.anonymous_profiles add column if not exists deletion_requested_at timestamptz;
alter table public.profiles add column if not exists surname text check (char_length(surname) between 1 and 80);
alter table public.anonymous_profiles add column if not exists surname text check (char_length(surname) between 1 and 80);
alter table public.anonymous_profiles add column if not exists training_place text
    check (training_place in ('home', 'gym', 'both', 'outdoors'));
alter table public.anonymous_profiles add column if not exists training_experience text
    check (training_experience in ('beginner', 'intermediate', 'advanced'));
alter table public.anonymous_profiles add column if not exists training_days_per_week integer
    check (training_days_per_week between 1 and 7);
alter table public.anonymous_profiles add column if not exists available_equipment text[] not null default '{}';
alter table public.anonymous_profiles add column if not exists equipment_screened boolean not null default false;
alter table public.anonymous_profiles add column if not exists health_screened boolean not null default false;
alter table public.anonymous_profiles add column if not exists medical_notes text not null default '';
alter table public.anonymous_profiles add column if not exists is_pregnant boolean not null default false;
revoke all on public.anonymous_profiles from anon;
grant select, insert, update, delete on public.anonymous_profiles to authenticated;

create or replace function public.touch_anonymous_profile()
returns trigger language plpgsql as $$
begin
    new.last_active_at = now();
    if new.deletion_requested_at is not null then
        new.expires_at = now();
    else
        new.expires_at = now() + interval '30 days';
    end if;
    new.updated_at = now();
    return new;
end;
$$;

revoke all on function public.touch_anonymous_profile() from public, anon, authenticated;

drop trigger if exists anonymous_profiles_touch on public.anonymous_profiles;
create trigger anonymous_profiles_touch before insert or update on public.anonymous_profiles
for each row execute function public.touch_anonymous_profile();

drop policy if exists "anonymous_profiles_own" on public.anonymous_profiles;
drop policy if exists "anonymous_profiles_select_own" on public.anonymous_profiles;
create policy "anonymous_profiles_select_own" on public.anonymous_profiles for select to authenticated
using ((select auth.uid()) is not null and (select auth.uid()) = user_id);

drop policy if exists "anonymous_profiles_insert_own" on public.anonymous_profiles;
create policy "anonymous_profiles_insert_own" on public.anonymous_profiles for insert to authenticated
with check ((select auth.uid()) is not null and (select auth.uid()) = user_id);

drop policy if exists "anonymous_profiles_update_own" on public.anonymous_profiles;
create policy "anonymous_profiles_update_own" on public.anonymous_profiles for update to authenticated
using ((select auth.uid()) is not null and (select auth.uid()) = user_id)
with check ((select auth.uid()) is not null and (select auth.uid()) = user_id);

drop policy if exists "anonymous_profiles_delete_own" on public.anonymous_profiles;
create policy "anonymous_profiles_delete_own" on public.anonymous_profiles for delete to authenticated
using ((select auth.uid()) is not null and (select auth.uid()) = user_id);

-- Idempotent daily cleanup. Anonymous Auth users are removed together with profiles via cascade.
create extension if not exists pg_cron with schema pg_catalog;
select cron.unschedule(jobid) from cron.job where jobname = 'delete-expired-forma-profiles';
select cron.schedule('delete-expired-forma-profiles', '0 3 * * *', $$
  delete from auth.users
  where is_anonymous is true
    and (
      id in (select user_id from public.anonymous_profiles where expires_at <= now())
      or (
        created_at < now() - interval '30 days'
        and not exists (
          select 1 from public.anonymous_profiles where anonymous_profiles.user_id = auth.users.id
        )
      )
    );
$$);
