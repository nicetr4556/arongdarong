-- =====================================================================
-- 아롱다롱 프로젝트 · Supabase 준비용 SQL
-- Supabase 대시보드 → SQL Editor → New query 에 전체를 붙여 넣고 [Run]을 누르세요.
-- 여러 번 실행해도 괜찮아요(이미 있으면 그대로 둡니다).
-- =====================================================================

-- 1) 학생 (이름 + 비밀번호 숫자 4개를 암호화해서 저장)
create table if not exists public.students (
  id          bigint generated always as identity primary key,
  class_id    text not null,
  name        text not null,
  pin_hash    text not null,
  created_at  timestamptz default now(),
  unique (class_id, name)
);

-- 2) 실패 기록
create table if not exists public.entries (
  id            bigint generated always as identity primary key,
  class_id      text not null,
  student_name  text not null,
  entry_date    date not null,
  title         text,
  w_who         text,
  w_when        text,
  w_where       text,
  w_what        text,
  w_how         text,
  w_why         text,
  solution      text,
  learned       text,
  felt          text,
  action        text,
  drawing_path  text,
  photo_paths   jsonb default '[]'::jsonb,
  featured      boolean default false,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);
create index if not exists entries_class_idx on public.entries (class_id, entry_date);

-- 3) '좋은 실패' 투표 (한 사람이 한 기록에 한 번만)
create table if not exists public.votes (
  id          bigint generated always as identity primary key,
  entry_id    bigint not null references public.entries(id) on delete cascade,
  class_id    text not null,
  voter_name  text not null,
  created_at  timestamptz default now(),
  unique (entry_id, voter_name)
);
create index if not exists votes_class_idx on public.votes (class_id);

-- 4) 보안: 바깥에서 공개 키로는 아무것도 못 보게 잠그고,
--    Streamlit 앱(서버에 숨겨 둔 secret 키)만 읽고 쓸 수 있게 합니다.
alter table public.students enable row level security;
alter table public.entries  enable row level security;
alter table public.votes    enable row level security;
grant all on table public.students, public.entries, public.votes to service_role;
grant usage, select on all sequences in schema public to service_role;

-- 5) 그림·사진 보관함 (비공개)
insert into storage.buckets (id, name, public)
values ('arongdarong', 'arongdarong', false)
on conflict (id) do nothing;
