-- ============================================================
-- NA는 어때? · Supabase 테이블 설정 (2026-11-22 개정)
-- ------------------------------------------------------------
-- 사용법: Supabase 대시보드 > SQL Editor 에 전체를 붙여 넣고 Run (여러 번 실행해도 안전)
-- 만드는 것
--   1) match_history : 로그인한 사용자의 매칭 기록 (내 정보 > 활동 내역)
--   2) scraps        : 스크랩한 의원
--   3) reactions     : TOP 5 의원에 대한 좋아요(+1)·싫어요(-1), 의원당 1인 1표
--   4) reaction_summary() : 홈 화면 '선호도 높은/낮은 의원'용 집계 (누가 눌렀는지는 공개 안 함)
-- 보안
--   모든 테이블에 RLS(행 단위 보안)를 켜서 로그인한 본인 행만 읽기·쓰기·삭제 가능
-- ============================================================

-- 1) 매칭 기록 ---------------------------------------------------
create table if not exists public.match_history (
  id          bigint generated always as identity primary key,
  user_id     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  survey      jsonb not null,            -- 설문 응답(가치관 답, 관심 분야, 프로필)
  top5        jsonb not null,            -- 그때의 TOP 5 요약(의원 코드, 이름, 정당, 점수)
  created_at  timestamptz not null default now()
);
create index if not exists match_history_user_idx on public.match_history (user_id, created_at desc);
alter table public.match_history enable row level security;

drop policy if exists "본인 기록 조회" on public.match_history;
create policy "본인 기록 조회" on public.match_history for select to authenticated using (user_id = auth.uid());
drop policy if exists "본인 기록 저장" on public.match_history;
create policy "본인 기록 저장" on public.match_history for insert to authenticated with check (user_id = auth.uid());
drop policy if exists "본인 기록 삭제" on public.match_history;
create policy "본인 기록 삭제" on public.match_history for delete to authenticated using (user_id = auth.uid());
grant select, insert, delete on public.match_history to authenticated;

-- 2) 스크랩 -----------------------------------------------------
create table if not exists public.scraps (
  user_id     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  mona_cd     text not null,             -- 의원 코드
  created_at  timestamptz not null default now(),
  primary key (user_id, mona_cd)
);
alter table public.scraps enable row level security;

drop policy if exists "본인 스크랩 조회" on public.scraps;
create policy "본인 스크랩 조회" on public.scraps for select to authenticated using (user_id = auth.uid());
drop policy if exists "본인 스크랩 추가" on public.scraps;
create policy "본인 스크랩 추가" on public.scraps for insert to authenticated with check (user_id = auth.uid());
drop policy if exists "본인 스크랩 삭제" on public.scraps;
create policy "본인 스크랩 삭제" on public.scraps for delete to authenticated using (user_id = auth.uid());
grant select, insert, delete on public.scraps to authenticated;

-- 3) 좋아요·싫어요 ------------------------------------------------
create table if not exists public.reactions (
  user_id     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  mona_cd     text not null,
  reaction    smallint not null check (reaction in (-1, 1)),   -- 1 좋아요, -1 싫어요
  updated_at  timestamptz not null default now(),
  primary key (user_id, mona_cd)         -- 한 사람이 한 의원에게 한 표만
);
alter table public.reactions enable row level security;

drop policy if exists "본인 평가 조회" on public.reactions;
create policy "본인 평가 조회" on public.reactions for select to authenticated using (user_id = auth.uid());
drop policy if exists "본인 평가 추가" on public.reactions;
create policy "본인 평가 추가" on public.reactions for insert to authenticated with check (user_id = auth.uid());
drop policy if exists "본인 평가 변경" on public.reactions;
create policy "본인 평가 변경" on public.reactions for update to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "본인 평가 삭제" on public.reactions;
create policy "본인 평가 삭제" on public.reactions for delete to authenticated using (user_id = auth.uid());
grant select, insert, update, delete on public.reactions to authenticated;

-- 4) 홈 화면용 집계: 의원별 좋아요·싫어요 수만 돌려줌 (개인 정보 없음) ------------
create or replace function public.reaction_summary()
returns table (mona_cd text, likes bigint, dislikes bigint)
language sql
security definer
set search_path = public
as $$
  select r.mona_cd,
         count(*) filter (where r.reaction = 1)  as likes,
         count(*) filter (where r.reaction = -1) as dislikes
  from public.reactions r
  group by r.mona_cd
$$;
revoke all on function public.reaction_summary() from public;
grant execute on function public.reaction_summary() to anon, authenticated;

-- 예전 버전이 쓰던 테이블(survey_results, user_results)은 이제 쓰지 않습니다.
-- 확인 후 필요 없으면 아래 줄 앞의 -- 를 지우고 실행해 삭제하세요.
-- drop table if exists public.survey_results;
-- drop table if exists public.user_results;
