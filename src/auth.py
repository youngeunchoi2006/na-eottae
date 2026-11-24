"""Supabase 회원 기능 (2026-11-22 개정)

기능
- 회원가입 · 로그인 · 로그아웃 (아이디를 '아이디@votematch.com' 형식의 이메일로 바꿔 Supabase Auth 사용)
- 활동 내역: 매칭 기록 저장·목록·다시 보기·삭제 (5차 회의록: 재방문 시 바로 결과 확인)
- 스크랩: 의원 스크랩 추가·해제·목록
- 좋아요·싫어요: TOP 5 의원 평가 (의원당 1인 1표), 홈 화면용 집계

보안 원칙
- Supabase 연결은 접속자마다 따로 만든다 (st.session_state). st.cache_resource로 공유하면
  한 사람의 로그인 상태가 다른 접속자에게 섞일 수 있다.
- 주소창(query params)에 사용자 ID를 넣지 않는다. 새로고침하면 다시 로그인한다.
- 모든 테이블은 RLS로 본인 행만 접근 가능 (supabase_setup.sql)
"""
import re

import pandas as pd
import streamlit as st

ID_DOMAIN = 'votematch.com'        # 아이디를 Supabase 이메일 형식으로 바꿀 때 쓰는 가짜 도메인
ID_PATTERN = re.compile(r'^[A-Za-z0-9_]{4,20}$')


# ---------------------------------------------------------------- 연결
def enabled():
    """secrets에 Supabase 정보가 있을 때만 회원 기능을 켠다 (없으면 로그인 없이 동작)"""
    try:
        return bool(st.secrets['SUPABASE_URL']) and bool(st.secrets['SUPABASE_KEY'])
    except Exception:
        return False


def _client():
    if 'sb_client' not in st.session_state:
        from supabase import create_client
        st.session_state['sb_client'] = create_client(st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_KEY'])
    return st.session_state['sb_client']


def current_user():
    """로그인했으면 {'id': ..., 'name': ...}, 아니면 None"""
    return st.session_state.get('auth_user')


def _friendly(e):
    msg = str(e)
    if 'Invalid login credentials' in msg:
        return '아이디 또는 비밀번호가 맞지 않습니다.'
    if 'already registered' in msg or 'already been registered' in msg:
        return '이미 사용 중인 아이디입니다.'
    if 'Email not confirmed' in msg:
        return "Supabase에서 이메일 확인이 켜져 있습니다. 대시보드에서 'Confirm email'을 꺼 주세요."
    if 'Password should be' in msg:
        return '비밀번호는 6자 이상이어야 합니다.'
    return f'처리 중 오류가 발생했습니다: {msg}'


# ---------------------------------------------------------------- 회원가입 · 로그인
def sign_up(user_id, password):
    user_id = user_id.strip()
    if not ID_PATTERN.match(user_id):
        return False, '아이디는 영문·숫자·밑줄 4~20자로 입력해 주세요.'
    if len(password) < 6:
        return False, '비밀번호는 6자 이상이어야 합니다.'
    try:
        _client().auth.sign_up({'email': f'{user_id}@{ID_DOMAIN}', 'password': password})
        return True, '가입이 완료되었습니다. [로그인] 탭에서 로그인해 주세요.'
    except Exception as e:
        return False, _friendly(e)


def sign_in(user_id, password):
    user_id = user_id.strip()
    if not user_id or not password:
        return False, '아이디와 비밀번호를 입력해 주세요.'
    try:
        res = _client().auth.sign_in_with_password({'email': f'{user_id}@{ID_DOMAIN}', 'password': password})
        st.session_state['auth_user'] = {'id': str(res.user.id), 'name': user_id}
        _load_my_marks()
        return True, None
    except Exception as e:
        return False, _friendly(e)


def sign_out():
    try:
        _client().auth.sign_out()
    except Exception:
        pass
    for key in ('auth_user', 'sb_client', 'survey', 'my_scraps', 'my_reactions',
                'history_consent', 'saved_keys'):
        st.session_state.pop(key, None)


# ---------------------------------------------------------------- 활동 내역 (매칭 기록)
def save_history(survey, top5):
    """매칭 기록 1건 저장. top5: [{'mona': ..., 'name': ..., 'party': ..., 'total': ...}, ...]"""
    user = current_user()
    if not user:
        return False, '로그인이 필요합니다.'
    try:
        res = _client().table('match_history').insert(
            {'user_id': user['id'], 'survey': survey, 'top5': top5}).execute()
        if not res.data:
            return False, '저장 응답이 비어 있습니다. Supabase의 RLS 정책을 확인해 주세요.'
        return True, '내 활동 내역에 저장했습니다.'
    except Exception as e:
        return False, _friendly(e)


def list_history(limit=30):
    user = current_user()
    if not user:
        return []
    try:
        res = (_client().table('match_history').select('id, survey, top5, created_at')
               .eq('user_id', user['id']).order('created_at', desc=True).limit(limit).execute())
        return res.data or []
    except Exception:
        return []


def delete_history(history_id=None):
    """history_id가 있으면 1건, 없으면 내 기록 전체 삭제"""
    user = current_user()
    if not user:
        return False, '로그인이 필요합니다.'
    try:
        q = _client().table('match_history').delete().eq('user_id', user['id'])
        if history_id is not None:
            q = q.eq('id', history_id)
        q.execute()
        return True, '삭제했습니다.'
    except Exception as e:
        return False, _friendly(e)


# ---------------------------------------------------------------- 스크랩 · 좋아요/싫어요
def _load_my_marks():
    """로그인 직후 내 스크랩·평가를 한 번 불러와 화면에서 바로 쓰도록 보관"""
    user = current_user()
    st.session_state['my_scraps'] = set()
    st.session_state['my_reactions'] = {}
    if not user:
        return
    try:
        res = _client().table('scraps').select('mona_cd').eq('user_id', user['id']).execute()
        st.session_state['my_scraps'] = {r['mona_cd'] for r in res.data or []}
        res = _client().table('reactions').select('mona_cd, reaction').eq('user_id', user['id']).execute()
        st.session_state['my_reactions'] = {r['mona_cd']: r['reaction'] for r in res.data or []}
    except Exception:
        pass


def my_scraps():
    return st.session_state.get('my_scraps', set())


def my_reactions():
    return st.session_state.get('my_reactions', {})


def toggle_scrap(mona):
    """스크랩되어 있으면 해제, 아니면 추가"""
    user = current_user()
    if not user:
        st.toast('오른쪽 위 [로그인]을 하면 의원을 스크랩할 수 있어요.')   # 화면을 다시 그리지 않고 잠깐 안내
        return
    scraps = set(my_scraps())
    try:
        table = _client().table('scraps')
        if mona in scraps:
            table.delete().eq('user_id', user['id']).eq('mona_cd', mona).execute()
            scraps.discard(mona)
        else:
            table.insert({'user_id': user['id'], 'mona_cd': mona}).execute()
            scraps.add(mona)
        st.session_state['my_scraps'] = scraps
    except Exception as e:
        st.toast(_friendly(e))


def set_reaction(mona, value):
    """value: 1(좋아요) 또는 -1(싫어요). 같은 버튼을 다시 누르면 취소"""
    user = current_user()
    if not user:
        st.toast('오른쪽 위 [로그인]을 하면 좋아요·싫어요를 남길 수 있어요.')
        return
    mine = dict(my_reactions())
    try:
        table = _client().table('reactions')
        if mine.get(mona) == value:
            table.delete().eq('user_id', user['id']).eq('mona_cd', mona).execute()
            mine.pop(mona, None)
        else:
            table.upsert({'user_id': user['id'], 'mona_cd': mona, 'reaction': value},
                         on_conflict='user_id,mona_cd').execute()
            mine[mona] = value
        st.session_state['my_reactions'] = mine
        reaction_summary.clear()          # 홈 화면 집계를 새로 계산하도록
    except Exception as e:
        st.toast(_friendly(e))


@st.cache_data(ttl=60, show_spinner=False)
def reaction_summary():
    """모든 사용자의 의원별 좋아요·싫어요 수 (1분마다 새로 계산). 실패하면 빈 표"""
    empty = pd.DataFrame(columns=['mona_cd', 'likes', 'dislikes'])
    if not enabled():
        return empty
    try:
        from supabase import create_client
        client = create_client(st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_KEY'])
        res = client.rpc('reaction_summary').execute()
        return pd.DataFrame(res.data or [], columns=['mona_cd', 'likes', 'dislikes'])
    except Exception:
        return empty


def delete_all_my_data():
    """내 활동 내역·스크랩·평가를 모두 삭제 (계정은 남음)"""
    user = current_user()
    if not user:
        return False, '로그인이 필요합니다.'
    try:
        for table in ('match_history', 'scraps', 'reactions'):
            _client().table(table).delete().eq('user_id', user['id']).execute()
        st.session_state['my_scraps'] = set()
        st.session_state['my_reactions'] = {}
        reaction_summary.clear()
        return True, '내 활동 내역, 스크랩, 평가를 모두 삭제했습니다.'
    except Exception as e:
        return False, _friendly(e)
