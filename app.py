"""NA는 어때? — 나와 가치관이 잘 맞는 국회의원은 누구일까
J조 (엄재훈, 오지훈, 최영은) · 인공지능 프로그래밍 팀 프로젝트

실행: streamlit run app.py
데이터: data/ 폴더 (03번 노트북 14번 셀이 만든 app_data 폴더의 파일들)

2026-11-22 개정 내용
 1. AI 분야 추천 삭제          2. Part 4(가중치 슬라이더) 삭제 → 보고서의 0.2 / 0.3 / 0.5 고정
 3. 12번 문항 교체(데이터 쪽)   4. 문항마다 쉬운 설명 + ⓘ 도움말
 5. 결과 화면 의원 스크랩        6. 매칭 기록을 [내 정보] > 활동 내역에 저장
 7. [내 정보] 메뉴는 로그인했을 때만 보임
 8. TOP 5 의원 좋아요·싫어요 → 홈 맨 아래 선호도 높은/낮은 의원 TOP 3
 9. 사이트 이름 'NA는 어때?'    10. 로그인은 오른쪽 위 버튼 → 팝업 창
"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE = Path(__file__).parent
sys.path.append(str(BASE / 'src'))

import auth                                   # noqa: E402
import records                                # noqa: E402
from records import PASSED                    # noqa: E402
import survey as sv                           # noqa: E402
from matching import ANSWER_SCORE, DEFAULT_WEIGHTS, FIELDS, Matcher   # noqa: E402

SITE_TITLE = 'NA는 어때?'
LOCKED_CHART = {'displayModeBar': False, 'scrollZoom': False, 'doubleClick': False, 'showAxisDragHandles': False}
SITE_SUBTITLE = '나와 가치관이 잘 맞는 국회의원은 누구일까'
st.set_page_config(page_title=f'{SITE_TITLE} · {SITE_SUBTITLE}', page_icon='🏛️', layout='wide')
DATA = BASE / 'data'

# 화면 꾸미기 (CSS) — 글자 크기 순서: 제목 > 부제목 > 본문 > 도움말·참고
st.markdown('''<style>
/* 기본 글자 크기 */
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {font-size: 1.12rem; line-height: 1.7;}
[data-testid="stWidgetLabel"] p {font-size: 1.08rem !important;}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {font-size: 1rem !important; line-height: 1.6;}
h2 {font-size: 2.1rem !important;}   /* 페이지 제목 (st.header) */
h3 {font-size: 1.65rem !important;}  /* 부제목 (st.subheader) */
h4 {font-size: 1.35rem !important;}
/* 결과 요약 칸: 한 칸 안에 이어지는 느낌 */
.st-key-summary_box {background: #f5f8ff; border-color: #c9d6f2 !important;}
.st-key-summary_box [data-testid="stVerticalBlock"] {gap: 0.35rem;}
.sum-title {font-size: 1.65rem; font-weight: 800; margin-bottom: 4px;}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] p {font-size: 2rem !important; font-weight: 700;}

/* 사이트 제목 칸 */
.hero {background: linear-gradient(135deg, #fff4f4 0%, #eef3ff 100%); border: 1px solid #e3e6ef;
       border-radius: 18px; padding: 22px 30px; margin-bottom: 14px;}
.hero-title {font-size: 2.9rem; font-weight: 800; line-height: 1.2;}
.hero-sub {font-size: 1.45rem; font-weight: 600; color: #444; margin-top: 6px;}

/* 설문 Part 제목 */
.part-title {font-size: 1.9rem; font-weight: 800; border-left: 7px solid #e0414f; background: #fafafa;
             padding: 8px 16px; border-radius: 6px; margin: 6px 0 4px 0;}

/* 가치관 문항: 크고 진하게 + 마우스를 올리면 도움말 */
.q-text {font-size: 1.32rem; font-weight: 800; position: relative; cursor: help; display: inline-block; margin-top: 10px;}
.q-i {font-size: 0.95rem; color: #e0414f; margin-left: 6px;}
.q-tip {display: none; position: absolute; left: 0; top: 105%; z-index: 9999; width: min(620px, 85vw);
        background: #fffdf3; color: #222; border: 1px solid #e5d9a8; border-radius: 10px; padding: 14px 16px;
        font-size: 1rem; font-weight: 400; line-height: 1.65; box-shadow: 0 6px 18px rgba(0,0,0,.15);}
.q-text:hover .q-tip {display: block;}
[data-testid="stCheckbox"] label p {font-size: 1.05rem;}

/* 제목 옆 링크(🔗) 숨기기, 아이디·비밀번호 칸의 'Press Enter' 안내 숨기기 */
[data-testid="stHeaderActionElements"] {display: none;}
[data-testid="InputInstructions"] {display: none;}

/* 왼쪽 메뉴: 넓게, 아이콘 + 큰 글자 버튼 */
section[data-testid="stSidebar"] {min-width: 300px; max-width: 360px;}
[class*="st-key-nav_"] button {justify-content: flex-start; min-height: 3.1rem; padding-left: 1rem;}
[class*="st-key-nav_"] button > div {justify-content: flex-start; width: 100%;}
[class*="st-key-nav_"] button p {font-size: 1.2rem !important; font-weight: 700;}
[class*="st-key-nav_"] button span[data-testid="stIconMaterial"] {font-size: 1.5rem;}

/* 결과 탭 글자 크게 */
[data-testid="stTab"] {padding: 10px 18px !important;}
[data-testid="stTab"] p {font-size: 1.25rem !important; font-weight: 700;}

/* 설문 다시 하기 버튼 크게 */
.st-key-reset_top button {min-height: 3.2rem;}
.st-key-reset_top button p {font-size: 1.2rem !important; font-weight: 700;}

/* TOP 5 카드: 순위별 색 */
</style>''', unsafe_allow_html=True)


# ---------------------------------------------------------------- 디자인: DESIGN.md 기반 (남색 기본색 · 흰 본문 · Pretendard 글꼴)
st.markdown('''<style>
@font-face {font-family: "Pretendard Variable"; font-weight: 45 920; font-display: swap;
  src: url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/woff2/PretendardVariable.woff2") format("woff2"),
       url("app/static/PretendardVariable.woff2") format("woff2");}
html, body, [class*="st-"], [data-testid="stMarkdownContainer"], button, input, textarea, select
  {font-family: "Pretendard Variable", system-ui, -apple-system, "Segoe UI", sans-serif !important;}
[data-testid="stIconMaterial"] {font-family: "Material Symbols Rounded" !important;}
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {color: #292827; font-weight: 460;}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {color: #73706d !important;}
h2, h3, h4 {color: #292827; font-weight: 600 !important; letter-spacing: -0.6px;}

/* 제목 칸: 예전 밝은 그라데이션 색, 글씨는 남색 */
.hero {background: linear-gradient(135deg, #fff4f4 0%, #eef3ff 100%); border: 1px solid #e3e6ef;
       border-radius: 16px; padding: 30px 40px; margin-bottom: 20px;}
.hero-title {color: #1b1938; font-size: 3.2rem; font-weight: 600; line-height: 1.05; letter-spacing: -1px;}
.hero-sub {color: #4a4766; font-size: 1.4rem; font-weight: 500; margin-top: 10px;}

/* 2. 로그인: 화면 맨 오른쪽 위에 고정 (Streamlit 'Deploy' 버튼은 숨김) */
[data-testid="stAppDeployButton"] {display: none;}
.st-key-login_area {position: fixed; top: 10px; right: 64px; z-index: 999991; width: auto !important;}
.st-key-login_area button {border-radius: 9999px; padding: 6px 18px; min-height: 2.4rem;}

/* 3. 설문 다시 하기: 칸 없이 버튼만, 가운데 */

/* 4. 스크랩 버튼: 카드 제목 줄 오른쪽 끝에 겹쳐 놓기 */
[class*="st-key-top5_r"], [class*="st-key-opp_r"] {position: relative;}
[class*="st-key-hdrscrap_"] {position: absolute; top: 7px; right: 12px; z-index: 5; width: auto !important;}
[class*="st-key-hdrscrap_"] button {min-height: 2.2rem; padding: 2px 14px;}
[class*="st-key-top5_r"] summary, [class*="st-key-opp_r"] summary {padding-right: 150px;}

/* 5. 좋아요·싫어요: 상세 칸 오른쪽 맨 아래 */
[class*="st-key-react_"] {display: flex; flex-direction: row; justify-content: flex-end; gap: 8px; margin-top: 10px;}
[class*="st-key-react_"] > div {width: auto !important;}

/* 왼쪽 메뉴: 사이트 제목과 첫 메뉴 사이 여백 */
.st-key-nav_0 {margin-top: 1.1rem;}

/* 첫 화면 안내 한 문장 */
.lead {font-size: 1.3rem; font-weight: 600; color: #1b1938; margin: 4px 0 18px 4px;}

/* 7. 응답 문항 숫자 색 = 메뉴 칸 색 */
.sum-num {color: #1b1938;}

/* 8. 6~10위 표: 머리줄 연한 남색 */
table.rank-table {width: 100%; border-collapse: collapse; font-size: 1.05rem;}
table.rank-table th {background: #4b4889; color: #fff; font-weight: 600; padding: 10px 12px; text-align: left;}
table.rank-table td {padding: 9px 12px; border-bottom: 1px solid #e8e4dd;}
table.rank-table tr:nth-child(even) td {background: #fafaf8;}

/* 사이드바: 오프화이트, 메뉴는 인디고 */
section[data-testid="stSidebar"] {background: #fafaf8; border-right: 1px solid #e8e4dd;}
[class*="st-key-nav_"] button[kind="tertiary"] p {color: #292827;}
button[kind="primary"] p, button[kind="primaryFormSubmit"] p, button[kind="primary"] [data-testid="stIconMaterial"] {color: #fff !important;}

/* 로그인 버튼: 연보라 알약 */
.st-key-open_login button, .st-key-login_area [data-testid="stPopover"] button
  {background: #1b1938 !important; border: none !important; font-weight: 700;}
.st-key-login_area button p, .st-key-login_area button [data-testid="stIconMaterial"] {color: #fff !important;}
.st-key-login_area button [data-testid="stIconMaterial"] {font-size: 1.45rem;}

/* 설문 Part 제목: 빨간 줄 대신 작은 라벨 + 큰 제목 */
.part-title {border-left: none; background: none; padding: 0; font-weight: 600; letter-spacing: -0.6px; color: #1b1938;}
.q-i {color: #6d63c9;}
.q-tip {background: #1b1938; color: #f2f0fa; border: none;}

/* 카드·칸: 얇은 따뜻한 회색 테두리 */
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stExpander"] details {border-color: #e8e4dd !important; border-radius: 12px !important;}
.st-key-summary_box {background: #fafaf8; border-color: #e8e4dd !important;}

/* TOP 5: 1위만 인디고로 뒤집어 강조 (요금제 '추천' 카드 방식), 나머지는 흰 카드 */


/* 6·7. 순위 카드(TOP 5 · 생각이 다른 의원): 순위가 내려갈수록 연해지는 남색, 마우스·클릭과 상관없이 고정 */
[class*="st-key-top5_r"] details, [class*="st-key-opp_r"] details
  {background: #fff !important; border: 1px solid #e8e4dd !important; border-radius: 12px !important; overflow: hidden;}
[class*="st-key-top5_r"] summary p, [class*="st-key-opp_r"] summary p {font-size: 1.28rem !important; font-weight: 700;}
.st-key-top5_r1 summary, .st-key-opp_r1 summary {--rk: linear-gradient(90deg, #1b1938, #2c2963); --rk-ink: #ffffff;}
.st-key-top5_r2 summary, .st-key-opp_r2 summary {--rk: linear-gradient(90deg, #393673, #4a4789); --rk-ink: #ffffff;}
.st-key-top5_r3 summary, .st-key-opp_r3 summary {--rk: linear-gradient(90deg, #5b589d, #6c69ae); --rk-ink: #ffffff;}
.st-key-top5_r4 summary {--rk: linear-gradient(90deg, #8f8cc8, #a19ed3); --rk-ink: #1b1938;}
.st-key-top5_r5 summary {--rk: linear-gradient(90deg, #c4c2e8, #d4d2ef); --rk-ink: #1b1938;}
[class*="st-key-top5_r"] summary, [class*="st-key-opp_r"] summary,
[class*="st-key-top5_r"] summary:hover, [class*="st-key-opp_r"] summary:hover,
[class*="st-key-top5_r"] summary:focus, [class*="st-key-opp_r"] summary:focus,
[class*="st-key-top5_r"] summary:active, [class*="st-key-opp_r"] summary:active
  {background: var(--rk) !important; color: var(--rk-ink) !important; border-radius: 0 !important;}
[class*="st-key-top5_r"] summary *, [class*="st-key-opp_r"] summary *,
[class*="st-key-top5_r"] summary:hover *, [class*="st-key-opp_r"] summary:hover *
  {color: var(--rk-ink) !important;}

/* 8. 스크랩 버튼: 눌러도·마우스를 올려도 색 그대로 (스크랩하면 노란 별 ⭐) */
[class*="st-key-scrap_"] button, [class*="st-key-scrap_"] button:hover, [class*="st-key-scrap_"] button:focus,
[class*="st-key-scrap_"] button:focus-visible, [class*="st-key-scrap_"] button:active
  {background: #ffffff !important; color: #292827 !important; border: 1px solid #d9d5cc !important; box-shadow: none !important;}
[class*="st-key-scrap_"] button p {color: #292827 !important;}

/* 3. 설문 이전·다음: 글씨 크기만큼 작은 버튼, 마지막 단계의 찾기 버튼은 양옆을 조금 줄인 큰 버튼 */
[class*="st-key-step_"] button {min-height: 2.4rem; padding: 4px 18px;}
[class*="st-key-step_"] button p {font-size: 1.05rem !important;}
.st-key-step_submit {padding: 6px 3% 0 3%;}
.st-key-step_submit button {min-height: 3.2rem;}
.st-key-step_submit button p {font-size: 1.25rem !important; font-weight: 700;}

/* 1. 문항 도움말 말고는 마우스를 올려도 아무것도 뜨지 않게 (표·차트 위 도구 아이콘 숨김) */
[data-testid="stElementToolbar"] {display: none !important;}
.modebar-container {display: none !important;}
.q-text.no-tip {cursor: default;}

/* 차트 도구 줄은 모두 숨기되, 의원 기록의 분야 그래프만 '전체 화면' 버튼을 남김 */
[class*="st-key-radar_"] .modebar-container {display: block !important;}
[class*="st-key-radar_"] .modebar-btn:not([data-title*="ullscreen"]) {display: none !important;}

/* 설문 답 선택칸: 동그라미 대신 네모, 고르면 남색 네모 안에 ✓ (6칸을 같은 간격으로) */
.st-key-survey_box [data-testid="stElementContainer"]:has([data-testid="stRadio"]),
.st-key-survey_box [data-testid="stRadio"] {width: 100% !important;}
.st-key-survey_box [role="radiogroup"] {display: grid !important; grid-template-columns: repeat(6, 1fr); gap: 4px; width: 100%;}
.st-key-survey_box [data-testid="stRadioOption"] > div > div:first-child
  {border-radius: 4px !important; width: 18px !important; height: 18px !important; background: #fff !important;
   border: 1.5px solid #b9b5ad !important; display: flex; align-items: center; justify-content: center;}
.st-key-survey_box [data-testid="stRadioOption"] > div > div:first-child > div {display: none !important;}
.st-key-survey_box [data-testid="stRadioOption"][data-selected="true"] > div > div:first-child
  {background: #1b1938 !important; border-color: #1b1938 !important;}
.st-key-survey_box [data-testid="stRadioOption"][data-selected="true"] > div > div:first-child::after
  {content: '✓'; color: #fff; font-size: 13px; font-weight: 800; line-height: 1;}
.st-key-survey_box [data-testid="stRadioOption"] p {font-size: 1.05rem !important;}

/* 페이지를 옮길 때 이전 페이지의 흐릿한 요소가 남아 보이지 않게 (아래 스크립트가 잠깐 켜는 표시) */
body.page-switching [data-stale="true"] {display: none !important;}

/* 9. 국회 둘러보기 설명 칸 */
.st-key-map_explain {background: #fafaf8;}
</style>''', unsafe_allow_html=True)

HOME, EXPLORE, SEARCH, MYPAGE = '나와 맞는 의원 찾기', '국회 둘러보기', '의원 검색', '내 정보'

LEAD = '프로필과 관심분야, 15개 질문에 답하면, 실제 표결 기록으로 나와 생각이 닮은 국회의원을 찾아드려요.'
ABOUT = ('이 사이트의 목적은 방대하고 어려운 국회의원의 실제 의정활동 기록(표결·발의안)을 일반 사용자가 '
         '편리하고 흥미롭게 확인할 수 있도록 돕는 것입니다. 설문을 통해 나와 생각이 같은 활동은 물론, '
         '다른 활동까지 함께 보여주어, 스스로 판단할 수 있는 참고 정보를 제공합니다.')
TEAM = '팀 J조 · 오지훈, 최영은, 엄재훈  \n충북대학교 소프트웨어학부'
NEUTRAL = ('이 서비스는 특정 정당이나 의원의 지지를 권하지 않으며, '
           '결과는 공개된 국회 기록에 근거한 참고 정보입니다.')


# ---------------------------------------------------------------- 데이터
@st.cache_data(show_spinner='데이터를 불러오는 중…')
def load_data():
    def by_member(df):
        return df.set_index('MONA_CD') if 'MONA_CD' in df.columns else df

    d = {
        'members': by_member(pd.read_parquet(DATA / 'members.parquet')),
        'questions': pd.read_csv(DATA / 'questions.csv'),
        'question_votes': pd.read_parquet(DATA / 'question_votes.parquet'),
        'coords': by_member(pd.read_parquet(DATA / 'coords.parquet')),
        'sponsorship': pd.read_parquet(DATA / 'sponsorship.parquet'),
        'sponsored': pd.read_parquet(DATA / 'sponsored_bills.parquet'),
        'meta': json.loads((DATA / '_meta.json').read_text(encoding='utf-8')) if (DATA / '_meta.json').exists() else {},
    }
    q = d['questions']
    for col in ('도움말', '쉬운설명'):          # 예전 questions.csv에 없는 열이어도 동작하도록
        q[col] = q[col].fillna('') if col in q.columns else ''
    d['bill_field'] = d['sponsorship'].drop_duplicates('BILL_ID').set_index('BILL_ID')['field']
    return d


@st.cache_resource(show_spinner='매칭 엔진 준비 중…')
def get_matcher():
    d = load_data()
    return Matcher(d['members'], d['questions'], d['question_votes'], d['sponsorship'])


data = load_data()
matcher = get_matcher()
members, coords, questions = data['members'], data['coords'], data['questions']
ss = st.session_state


def pct(x):
    return '-' if pd.isna(x) else f'{x * 100:.0f}점'


def member_label(mona):
    if mona not in members.index:
        return mona
    m = members.loc[mona]
    return f"{m['HG_NM']} ({m['POLY_NM']} · {m['ORIG_NM']})"


def data_basis():
    meta = data['meta']
    if not meta:
        return '제22대 국회 기록 기준'
    return (f"제22대 국회 · 본회의 처리 {meta.get('본회의_처리일_최근', '')}까지, "
            f"법안 발의 {meta.get('발의일_최근', '')}까지 반영 (수집 {meta.get('수집기간', '')})")


def survey_key(s):
    """같은 설문 결과를 두 번 저장하지 않도록 설문 내용으로 만든 지문"""
    return hashlib.md5(json.dumps(s, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def footer():
    st.divider()
    st.caption(f'{NEUTRAL}  \n데이터: 열린국회정보 Open API · {data_basis()}')


def show_flash():
    """버튼 콜백에서 남긴 안내 메시지를 한 번만 보여 준다"""
    msg = ss.pop('flash', None)
    if msg:
        getattr(st, msg[0])(msg[1])


# ---------------------------------------------------------------- 10. 로그인 (오른쪽 위 버튼 → 팝업)
def after_login():
    """로그인 직후: 최근 매칭 기록이 있으면 결과를 바로 보여 준다 (재방문 시 바로 확인)"""
    if ss.get('survey'):
        ss['flash'] = ('success', f"{auth.current_user()['name']} 님, 반갑습니다!")
        return
    hist = auth.list_history(limit=1)
    if hist:
        ss['survey'] = hist[0]['survey']
        ss.setdefault('saved_keys', set()).add(survey_key(hist[0]['survey']))
        ss['pending_menu'] = HOME
        ss['flash'] = ('success', '가장 최근 매칭 결과를 불러왔습니다. 지난 기록은 [내 정보]에서 볼 수 있어요.')
    else:
        ss['flash'] = ('info', '로그인했습니다. 설문을 마치면 결과가 [내 정보] > 활동 내역에 저장됩니다.')


def _open_login():
    ss['show_login'] = True


def _close_login():
    ss.pop('show_login', None)


# 팝업은 show_login 표시가 있는 동안 계속 열려 있고, X를 누르거나 로그인에 성공하면 닫힌다
@st.dialog('로그인 / 회원가입', on_dismiss=_close_login)
def login_dialog():
    t1, t2 = st.tabs(['로그인', '회원가입'])
    with t1:
        with st.form('login_form'):
            uid = st.text_input('아이디')
            pw = st.text_input('비밀번호', type='password')
            go_login = st.form_submit_button('로그인', type='primary', width='stretch')
        if go_login:
            ok, msg = auth.sign_in(uid, pw)
            if ok:
                after_login()
                _close_login()
                st.rerun()                     # 전체 화면을 다시 그리면서 팝업이 닫힌다
            st.error(msg)
    with t2:
        with st.form('signup_form'):
            new_id = st.text_input('새 아이디 (영문·숫자·밑줄 4~20자)')
            new_pw = st.text_input('새 비밀번호 (6자 이상)', type='password')
            go_signup = st.form_submit_button('회원가입', width='stretch')
        if go_signup:
            ok, msg = auth.sign_up(new_id, new_pw)
            (st.success if ok else st.error)(msg)
        st.caption('아이디와 비밀번호만 받습니다. 이메일·실명은 받지 않아요.')


def _go_mypage():
    ss['pending_menu'] = MYPAGE


def _do_logout():
    auth.sign_out()
    ss['pending_menu'] = HOME
    ss['flash'] = ('info', '로그아웃했습니다.')


def header():
    st.markdown(f'<div class="hero"><div class="hero-title">🏛️ {SITE_TITLE}</div>'
                f'<div class="hero-sub">{SITE_SUBTITLE}</div></div>', unsafe_allow_html=True)
    with st.container(key='login_area'):         # CSS로 화면 맨 오른쪽 위에 고정
        if not auth.enabled():
            st.caption('회원 기능 꺼짐')
        elif auth.current_user() is None:
            st.button('로그인', icon=':material/account_circle:', key='open_login', on_click=_open_login)
        else:
            with st.popover(f"{auth.current_user()['name']} 님", icon=':material/account_circle:'):
                st.button('내 정보', on_click=_go_mypage, width='stretch', key='pop_mypage')
                st.button('로그아웃', on_click=_do_logout, width='stretch', key='pop_logout')
    if auth.enabled() and auth.current_user() is None and ss.get('show_login'):
        login_dialog()
    show_flash()


# ---------------------------------------------------------------- 7. 메뉴 (아이콘 버튼, 내 정보는 로그인했을 때만)
NAV = [(HOME, ':material/how_to_vote:'), (EXPLORE, ':material/account_balance:'),
       (SEARCH, ':material/person_search:'), (MYPAGE, ':material/account_circle:')]


def _go(page):
    ss['menu'] = page


def sidebar():
    options = [HOME, EXPLORE, SEARCH] + ([MYPAGE] if auth.current_user() else [])
    if 'pending_menu' in ss:                  # 버튼으로 다른 메뉴로 보내야 할 때
        ss['menu'] = ss.pop('pending_menu')
    if ss.get('menu') not in options:         # 로그아웃 등으로 메뉴가 사라졌으면 홈으로
        ss['menu'] = HOME
    with st.sidebar:
        st.markdown(f'## 🏛️ {SITE_TITLE}')
        for i, (name, icon) in enumerate(NAV):
            if name in options:
                st.button(name, icon=icon, key=f'nav_{i}', width='stretch', on_click=_go, args=(name,),
                          type='primary' if ss['menu'] == name else 'tertiary')
        st.divider()
        st.caption('**웹사이트 소개**  \n' + ABOUT)
        st.caption('**만든 사람**  \n' + TEAM)
        if auth.enabled() and auth.current_user() is None:
            st.divider()
            st.caption('오른쪽 위 [로그인]을 하면 [내 정보] 메뉴가 생기고, 매칭 기록·스크랩·좋아요를 남길 수 있어요.')


# ---------------------------------------------------------------- 5·8. 스크랩 / 좋아요·싫어요 버튼
def action_row(mona, key, reactions=False):
    """의원 카드 위에 붙는 버튼 줄. reactions=True면 좋아요·싫어요도 (TOP 5 전용)"""
    if not auth.enabled():
        return
    cols = st.columns([1, 1, 1, 3] if reactions else [1, 5])
    on = mona in auth.my_scraps()
    cols[0].button('⭐ 스크랩' if on else '☆ 스크랩', key=f'scrap_{key}_{mona}', width='stretch',
                   on_click=auth.toggle_scrap, args=(mona,))
    if reactions:
        mine = auth.my_reactions().get(mona)
        cols[1].button('👍 좋아요', key=f'like_{key}_{mona}', width='stretch',
                       type='primary' if mine == 1 else 'secondary', on_click=auth.set_reaction, args=(mona, 1))
        cols[2].button('👎 싫어요', key=f'dislike_{key}_{mona}', width='stretch',
                       type='primary' if mine == -1 else 'secondary', on_click=auth.set_reaction, args=(mona, -1))
    if auth.current_user() is None:
        cols[-1].caption('로그인하면 사용할 수 있어요.')


def header_scrap(mona, key):
    """4. 카드 제목 줄 오른쪽 끝의 스크랩 버튼 (CSS로 위치 고정)"""
    if not auth.enabled():
        return
    on = mona in auth.my_scraps()
    with st.container(key=f'hdrscrap_{key}'):
        st.button('⭐ 스크랩' if on else '☆ 스크랩', key=f'scrap_{key}_{mona}',
                  on_click=auth.toggle_scrap, args=(mona,))


def reaction_row(mona, key):
    """5. 상세 칸 오른쪽 맨 아래 좋아요·싫어요"""
    if not auth.enabled():
        return
    mine = auth.my_reactions().get(mona)
    with st.container(key=f'react_{key}', horizontal=True):
        if auth.current_user() is None:
            st.caption('로그인하면 평가를 남길 수 있어요.')
        st.button('👍 좋아요', key=f'like_{key}_{mona}', type='primary' if mine == 1 else 'secondary',
                  on_click=auth.set_reaction, args=(mona, 1))
        st.button('👎 싫어요', key=f'dislike_{key}_{mona}', type='primary' if mine == -1 else 'secondary',
                  on_click=auth.set_reaction, args=(mona, -1))


# ---------------------------------------------------------------- 설문 (단계별: 1단계 Part 1·2 → Part 3 분야별)
HELP_FIELD = '언론·정치제도'                # 도움말을 보여 줄 분야
# questions.csv에 도움말이 비어 있을 때(03번 셀5 교체 전 데이터) 대신 쓰는 도움말
FALLBACK_HELP = {
    'Q12': ('방송법 개정: 공영방송 이사 수를 늘리고, 이사 추천을 국회 밖(학계·시청자·방송 종사자 등)으로 넓히는 내용\n\n'
            '개정 찬성 측: 정권이 바뀔 때마다 공영방송이 흔들리는 것을 막고 독립성을 높인다.\n\n'
            '개정 반대 측: 추천 단체가 특정 성향에 치우칠 수 있어 오히려 중립성이 약해질 수 있다.'),
    'Q13': ('국회법 개정: 필리버스터(무제한 토론)를 이어 가는 조건을 더 엄격하게 하는 내용\n\n'
            '찬성 측: 소수 의원만 남아 토론을 끄는 것은 국회 운영을 막는 수단이 되므로 최소한의 요건이 필요하다.\n\n'
            '반대 측: 필리버스터는 소수당이 다수당의 일방적인 처리에 맞서는 거의 유일한 수단이다.'),
}
UNKNOWN = sv.ANSWER_LABELS[-1]                # '모르겠음'
PROFILE_KEYS = ['p_gender', 'p_birth', 'p_sido', 'p_job', 'int_1', 'int_2', 'int_3']


def survey_steps():
    """[('Part 1·2 …', None), ('Part 3-1 경제·노동·복지', 해당 문항 표), …]"""
    steps = [('Part 1 · 2  기본 프로필과 관심 분야', None)]
    fields = list(dict.fromkeys(questions['분야']))
    for i, f in enumerate(fields, start=1):
        steps.append((f'Part 3-{i}  가치관 · {f}', questions[questions['분야'] == f]))
    return steps


def keep(key, default):
    """단계를 넘어가면 화면에 없는 입력칸 값이 지워지므로, 따로 보관해 두었다가 되살린다"""
    if key not in ss:
        ss[key] = ss.get(f'keep_{key}', default)


def _save(key):
    ss[f'keep_{key}'] = ss[key]


def kept(key):
    return ss.get(f'keep_{key}', ss.get(key, sv.NOT_SELECTED))


def _collect_step():
    """지금 단계 화면의 값을 따로 보관 (단계를 넘기면 화면에 없는 입력칸 값은 지워지므로)"""
    for key in PROFILE_KEYS:
        if key in ss:
            ss[f'keep_{key}'] = ss[key]
    draft = ss.setdefault('draft', {})
    for qid in questions['qid']:
        if f'q_{qid}' in ss:
            draft[qid] = ss[f'q_{qid}']


def _step_button(action):
    """이전·다음·찾기 버튼 (설문 폼 제출 시 실행)"""
    _collect_step()
    if action == 'submit':
        ss['do_submit'] = True
    else:
        ss['survey_step'] = ss.get('survey_step', 0) + action


def part_title(text):
    st.markdown(f'<div class="part-title">{text}</div>', unsafe_allow_html=True)


def question_block(q):
    """문항 글씨(크고 진하게, 언론·정치제도만 마우스를 올리면 도움말) + 네모 선택칸 6개"""
    import html
    num = int(q['qid'][1:])
    # 도움말은 '언론·정치제도' 분야 문항에만 보여 준다 (나머지는 문장만으로 충분)
    help_text = str(q['도움말'] or '').strip() or FALLBACK_HELP.get(q['qid'], '')
    show_tip = str(q['분야']).strip() == HELP_FIELD and bool(help_text)
    tip = html.escape(help_text).replace('\n', '<br>') if show_tip else ''
    st.markdown(f'<span class="q-text{"" if tip else " no-tip"}">{num}. {html.escape(q["질문문장"])}'
                + (f'<span class="q-i">ⓘ 도움말</span><span class="q-tip">{tip}</span>' if tip else '')
                + '</span>', unsafe_allow_html=True)
    current = ss.setdefault('draft', {}).get(q['qid'], UNKNOWN)
    # 폼 안의 선택칸: 누를 때 서버를 거치지 않아 바로 체크됨 (CSS로 네모 + ✓ 모양)
    st.radio(f"{num}번 답", sv.ANSWER_LABELS, index=sv.ANSWER_LABELS.index(current), horizontal=True,
             key=f"q_{q['qid']}", label_visibility='collapsed')
    st.write('')


def submit_survey():
    draft = ss.get('draft', {})
    answers = {q: ANSWER_SCORE[draft.get(q, UNKNOWN)] for q in questions['qid']}
    interests = sv.clean_interests([kept('int_1'), kept('int_2'), kept('int_3')])
    profile = sv.clean_profile(kept('p_gender'), kept('p_birth'), kept('p_sido'), kept('p_job'))
    errors, warnings = sv.validate(answers, interests)
    if errors:                                # 오류는 한 번에 보여 주고, 지금까지 고른 답은 그대로 둔다
        for e in errors:
            st.error(e)
        return
    ss['survey'] = {'answers': answers, 'interests': interests, 'profile': profile,
                    'weights': dict(DEFAULT_WEIGHTS)}
    ss['survey_warnings'] = warnings
    st.rerun()                                # 화면 전체를 다시 그려 결과 화면으로


def survey_page():
    st.markdown(f'<div class="lead">{LEAD}</div>', unsafe_allow_html=True)
    survey_body()


def survey_body():
    """설문 한 단계 = 폼 하나. 폼 안에서 답을 고를 때는 서버를 거치지 않아 바로 반응하고,
    [이전]·[다음]·[찾기]를 누를 때만 한 번 서버에 보낸다 (체크할 때마다 느려지던 문제 해결)"""
    steps = survey_steps()
    step = min(max(ss.get('survey_step', 0), 0), len(steps) - 1)
    title, qs = steps[step]
    answered = sum(v != UNKNOWN for v in ss.get('draft', {}).values())

    with st.form('survey_form', border=False):
        with st.container(border=True, key='survey_box'):
            if qs is None:
                part_title('Part 1. 기본 프로필')
                st.caption('모두 선택 사항입니다. 고르지 않은 항목은 계산에서 빠집니다. '
                           "직업에서 '학생'·'기타'는 직업 비교에서, 비례대표 의원은 지역 비교에서 빠집니다.")
                for key in PROFILE_KEYS:
                    keep(key, sv.NOT_SELECTED)
                c1, c2, c3, c4 = st.columns(4)
                c1.selectbox('성별', [sv.NOT_SELECTED] + sv.GENDERS, key='p_gender')
                c2.selectbox('출생연도', [sv.NOT_SELECTED] + list(range(2010, 1939, -1)), key='p_birth')
                c3.selectbox('거주 지역 (시·도)', [sv.NOT_SELECTED] + sv.SIDO, key='p_sido')
                c4.selectbox('직업 분야', [sv.NOT_SELECTED] + sv.JOBS, key='p_job')
                st.divider()
                part_title('Part 2. 관심 분야 (1~3순위)')
                st.caption('관심 있는 분야의 법안을 많이 낸 의원일수록 점수가 높아집니다.')
                c1, c2, c3 = st.columns(3)
                for col, i in zip((c1, c2, c3), (1, 2, 3)):
                    col.selectbox(f'{i}순위', [sv.NOT_SELECTED] + FIELDS, key=f'int_{i}')
            else:
                if step == 1:
                    part_title('Part 3. 가치관 (15문항)')
                    st.caption("잘 모르는 문항은 '모르겠음'으로 두면 계산에서 빠집니다. "
                               "'모르겠음' 외의 답이 5개 이상 필요합니다.")
                st.markdown(f"#### 📌 {qs['분야'].iloc[0]}  ({step} / {len(steps) - 1} 분야)")
                if qs['분야'].iloc[0] == HELP_FIELD:
                    st.caption('문항 글씨에 마우스를 올리면 법의 내용과 찬성·반대 주장이 나와요.')
                for _, q in qs.iterrows():
                    question_block(q)

        if qs is not None:                    # 진행 막대는 Part 3(가치관)부터
            st.progress(step / (len(steps) - 1),
                        text=f'**Part 3 · {step} / {len(steps) - 1} 분야** · 지금까지 답한 가치관 문항 '
                             f'{answered} / {len(questions)}')
        with st.container(horizontal=True, horizontal_alignment='distribute', key='step_nav'):
            st.form_submit_button('◀ 이전', key='step_prev', disabled=step == 0,
                                  on_click=_step_button, args=(-1,))
            if step < len(steps) - 1:
                st.form_submit_button('다음 ▶', key='step_next', type='primary', on_click=_step_button, args=(1,))
        if step == len(steps) - 1:
            st.caption(f"종합 점수 = 프로필 {DEFAULT_WEIGHTS['profile']:.0%} + 관심 분야 "
                       f"{DEFAULT_WEIGHTS['interest']:.0%} + 가치관 {DEFAULT_WEIGHTS['value']:.0%} "
                       "(실제 표결과 비교하는 가치관에 가장 큰 비중)")
            st.form_submit_button('🔍 나와 맞는 국회의원 찾기', key='step_submit', type='primary', width='stretch',
                                  on_click=_step_button, args=('submit',))

    if ss.pop('do_submit', False):
        submit_survey()


def reset_survey():
    """설문 다시 하기: 결과와 지난 응답을 지우고 1단계로"""
    for k in ['survey', 'draft', 'survey_step'] + [f'keep_{k}' for k in PROFILE_KEYS] + PROFILE_KEYS:
        ss.pop(k, None)
    for k in [k for k in ss.keys() if str(k).startswith('exp_')] + ['result_tabs', 'local_pick', 'open_cards']:
        ss.pop(k, None)                       # 다음 결과는 다시 1위 카드만 펼친 첫 탭에서 시작


# ---------------------------------------------------------------- 결과
MEDAL = {1: '🥇 ', 2: '🥈 ', 3: '🥉 '}


def member_title(rank, row, score_name='종합', score_col='total', medal=True):
    icon = MEDAL.get(rank, '') if medal else ''
    return (f"{icon}**{rank}위** · **{row['HG_NM']}** ({row['POLY_NM']} · {row['ORIG_NM']})"
            f" — {score_name} **{pct(row[score_col])}**")


def _remember_card(k):
    ss.setdefault('open_cards', {})[k] = ss[k]


@st.fragment
def rank_card(kind, rank, mona, row, s):
    """순위 카드 하나. fragment라서 스크랩·좋아요를 눌러도 이 카드만 다시 그림 (스크롤·탭 유지)"""
    with st.container(key=f'{kind}_r{rank}'):
        if kind == 'top5':
            title = member_title(rank, row)
        else:
            title = member_title(rank, row, '가치관', 'value', medal=False)
        # 최적화: 카드가 펼쳐졌을 때만 기록(표·차트)을 그림
        # 펼침 상태를 따로 기억해 두어, 다른 탭에 다녀와도 펼쳐 둔 카드가 그대로 유지되게 함
        k = f'exp_{kind}{rank}'
        opened = ss.setdefault('open_cards', {})
        exp = st.expander(title, expanded=opened.get(k, rank == 1), key=k,
                          on_change=_remember_card, args=(k,))
        with exp:
            if exp.open:
                score_row(row)
                records.show_member(mona, data, matcher, s, key=f'{kind}{rank}')
                if kind == 'top5':
                    reaction_row(mona, f'top{rank}')
        header_scrap(mona, f'{kind}{rank}')


def score_row(row):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('종합 점수', pct(row['total']))
    c2.metric('가치관 (실제 표결)', pct(row['value']))
    c3.metric('관심 분야 (발의)', pct(row['interest']))
    c4.metric('프로필 (배경)', pct(row['profile']))
    st.caption(f"응답한 문항 중 이 의원과 비교할 수 있었던 {int(row['common'])}문항에서 "
               f"**{int(row['agree'])}문항이 같은 입장**이었습니다.")


def map_figure(user_xy=None, highlight=None, color_by='group'):
    df = coords.reset_index()
    label = {'group': '성향 그룹', 'POLY_NM': '정당'}[color_by]
    fig = px.scatter(df, x='x', y='y', color=color_by, hover_data=['HG_NM', 'POLY_NM', 'ORIG_NM'],
                     labels={'x': '제1 성향축', 'y': '제2 성향축', color_by: label}, height=560)
    if highlight is not None and len(highlight):
        top = coords.loc[coords.index.intersection(highlight)]
        fig.add_trace(go.Scatter(x=top['x'], y=top['y'], mode='markers+text', text=top['HG_NM'],
                                 textposition='top center', name='찾은 의원',
                                 marker=dict(size=20, symbol='star', color='gold', line=dict(width=2, color='black'))))
    if user_xy is not None and user_xy.notna().all():
        fig.add_trace(go.Scatter(x=[user_xy['x']], y=[user_xy['y']], mode='markers+text', text=['나'],
                                 textposition='top center', name='내 위치 (TOP 5의 평균)',
                                 marker=dict(size=22, symbol='star', color='gold', line=dict(width=2, color='black'))))
    fig.update_layout(legend=dict(orientation='h', y=-0.15, itemclick=False, itemdoubleclick=False),
                      dragmode=False)                       # 확대·이동·범례 클릭 막기 (점 위 이름 표시는 유지)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


@st.cache_data(show_spinner=False, max_entries=300)
def cached_match(survey_json):
    """10. 같은 설문이면 매칭을 다시 계산하지 않음 (버튼을 누를 때마다 느려지던 문제)"""
    s = json.loads(survey_json)
    return matcher.match(s['answers'], s.get('interests'), s.get('profile'), DEFAULT_WEIGHTS)


def top5_payload(top5):
    return [{'mona': m, 'name': r['HG_NM'], 'party': r['POLY_NM'], 'total': round(float(r['total']), 3)}
            for m, r in top5.iterrows()]


def history_box(s, top5):
    """6. 로그인한 사용자의 매칭 결과를 활동 내역에 저장 (접속마다 한 번 동의 → 이후 자동 저장)
    결과 요약 칸 안에 한 줄로 들어가도록 칸·색 상자 없이 글로만 표시한다."""
    if not auth.enabled():
        return
    if auth.current_user() is None:
        st.markdown('오른쪽 위 [로그인]을 하면 이 결과가 [내 정보] > 활동 내역에 저장되고, '
                    '의원 스크랩과 좋아요·싫어요도 남길 수 있어요.')
        return
    key = survey_key(s)
    saved = ss.setdefault('saved_keys', set())
    if key in saved:
        st.markdown('이 결과는 **[내 정보] > 활동 내역**에 저장되어 있어요.')
        return
    if ss.get('history_consent'):
        ok, msg = auth.save_history(s, top5_payload(top5))
        if ok:
            saved.add(key)
            st.toast(msg, icon='💾')
            st.markdown('이 결과는 **[내 정보] > 활동 내역**에 저장되어 있어요.')
        else:
            ss['history_consent'] = False
            st.error(msg)
        return
    text, btn = st.columns([4, 1], vertical_alignment='center')
    text.markdown('**이 결과를 내 활동 내역에 저장할까요?** 설문 응답과 TOP 5가 내 계정에만 저장되고, '
                  '[내 정보]에서 언제든 삭제할 수 있어요.')
    if btn.button('동의하고 저장', type='primary', key='consent_save', width='stretch'):
        ss['history_consent'] = True
        st.rerun()


def summary_box(s, top5):
    """결과 맨 위 요약 칸: 응답 문항 수(부제목 크기) + 안내 + 저장 안내를 한 칸에 이어서"""
    answered = sum(v is not None for v in s['answers'].values())
    _, warnings = sv.validate(s['answers'], s.get('interests'))
    with st.container(border=True, key='summary_box'):
        st.markdown(f'<div class="sum-title">응답 문항 <span class="sum-num">{answered} / {len(s["answers"])}</span></div>',
                    unsafe_allow_html=True)
        for w in warnings:
            st.markdown(w)
        history_box(s, top5)


def result_page():
    s = ss['survey']
    res = cached_match(json.dumps(s, sort_keys=True, ensure_ascii=False, default=str))
    top5, next5 = res.head(5), res.iloc[5:10]

    head, btn = st.columns([4, 1], vertical_alignment='center')
    head.header('나와 생각이 비슷한 국회의원')
    btn.button('🔄 설문 다시 하기', key='reset_top', type='primary', width='stretch', on_click=reset_survey)
    ss.pop('survey_warnings', None)
    summary_box(s, top5)

    # 최적화: 열려 있는 탭만 내용을 그림 (예전에는 탭 3개를 매번 모두 그려서 느렸음)
    t1, t2, t4 = st.tabs(['🏆 TOP 5 & 6~10위', '🙅 생각이 가장 다른 의원', '📍 우리 지역 의원'],
                         key='result_tabs', on_change='rerun')

    with t1:
        if t1.open:
            tab_top(s, top5, next5)
    with t2:
        if t2.open:
            tab_opp(s, res)
    with t4:
        if t4.open:
            tab_local(s, res)

    preference_ranking()


def tab_top(s, top5, next5):
    st.subheader('나와 가장 잘 맞는 국회의원 TOP 5')
    st.caption('카드를 펼치면 설문 문항에 대한 실제 표결과 법안 발의 기록을 볼 수 있습니다. '
               '기록을 보고 👍·👎를 남기면 홈 화면의 선호도 순위에 반영됩니다.')
    for rank, (mona, row) in enumerate(top5.iterrows(), start=1):
        rank_card('top5', rank, mona, row, s)

    st.subheader('6위 ~ 10위')
    table = pd.DataFrame({
        '순위': range(6, 6 + len(next5)),
        '의원': next5['HG_NM'], '정당': next5['POLY_NM'], '지역구': next5['ORIG_NM'],
        '종합 점수': (next5['total'] * 100).round(0).astype(int),
        '같은 입장 문항': [f"{int(a)} / {int(c)}" for a, c in zip(next5['agree'], next5['common'])],
    })
    st.markdown(table.to_html(index=False, classes='rank-table', border=0, escape=True), unsafe_allow_html=True)
    st.caption('6~10위 의원의 기록은 왼쪽 메뉴의 [의원 검색]에서 볼 수 있습니다.')


def tab_opp(s, res):
    st.subheader('나와 생각이 가장 다른 의원')
    st.caption('가치관 점수가 가장 낮은 의원입니다 (비교 가능한 문항이 5개 이상인 의원 중). '
               '생각이 다른 의원이 실제로 어떻게 투표했는지도 함께 살펴보세요.')
    opp = Matcher.opposite(res, n=3)
    for i, (mona, row) in enumerate(opp.iterrows(), start=1):
        rank_card('opp', i, mona, row, s)


def tab_local(s, res):
    sido = (s.get('profile') or {}).get('sido')
    if not sido:
        st.info('Part 1에서 거주 지역을 고르면 우리 지역 의원과 비교해 드립니다.')
    else:
        st.subheader(f'📍 {sido} 지역구 의원과 나')
        local = res[matcher.sido.reindex(res.index).eq(sido) & ~matcher.is_pr.reindex(res.index).fillna(False)]
        if local.empty:
            st.info('비교할 수 있는 지역구 의원이 없습니다.')
        else:
            rank_of = pd.Series(range(1, len(res) + 1), index=res.index)
            table = pd.DataFrame({
                '전체 순위': rank_of[local.index], '의원': local['HG_NM'], '정당': local['POLY_NM'],
                '지역구': local['ORIG_NM'], '가치관 점수': (local['value'] * 100).round(0),
                '같은 입장 문항': [f"{int(a)} / {int(c)}" for a, c in zip(local['agree'], local['common'])],
            })
            table['가치관 점수'] = table['가치관 점수'].astype(int)
            st.markdown(table.to_html(index=False, classes='rank-table', border=0, escape=True),
                        unsafe_allow_html=True)
            local_detail(list(local.index), s)


@st.fragment
def local_detail(options, s):
    """우리 지역 의원 고르기 + 기록 (fragment: 고를 때 이 부분만 다시 그림)"""
    pick = st.selectbox('기록을 볼 의원', options, format_func=member_label, key='local_pick')
    action_row(pick, 'local')
    records.show_member(pick, data, matcher, s, key='local')


# ---------------------------------------------------------------- 8. 홈 맨 아래: 선호도 순위
def preference_ranking():
    st.divider()
    st.subheader('👍👎 사용자 선호도 순위')
    st.caption('로그인한 사용자들이 매칭 결과 TOP 5에서 누른 좋아요·싫어요를 합친 결과입니다 '
               '(좋아요 수 − 싫어요 수, 의원 한 명당 1인 1표, 1분마다 갱신). '
               '이 서비스나 제작자의 평가가 아니며, 참고용입니다.')
    if not auth.enabled():
        st.caption('회원 기능이 켜져 있을 때 표시됩니다.')
        return
    df = auth.reaction_summary()
    df = df[df['mona_cd'].isin(members.index)].copy() if not df.empty else df
    if df.empty:
        st.info('아직 평가가 없어요. 매칭 결과에서 첫 번째 👍·👎를 남겨 보세요!')
        return
    df[['likes', 'dislikes']] = df[['likes', 'dislikes']].fillna(0).astype(int)
    df['net'] = df['likes'] - df['dislikes']
    high = df[df['net'] > 0].sort_values(['net', 'likes'], ascending=[False, False]).head(3)
    low = df[df['net'] < 0].sort_values(['net', 'dislikes'], ascending=[True, False]).head(3)

    def show(col, title, part, empty_msg):
        with col.container(border=True):
            st.markdown(f'**{title}**')
            if part.empty:
                st.caption(empty_msg)
            for rank, r in enumerate(part.itertuples(), start=1):
                st.markdown(f"**{rank}위** · {member_label(r.mona_cd)}  \n"
                            f"👍 {r.likes} · 👎 {r.dislikes} (합계 {r.net:+d})")

    c1, c2 = st.columns(2)
    show(c1, '😊 선호도가 높은 의원 TOP 3', high, '좋아요가 더 많은 의원이 아직 없어요.')
    show(c2, '😐 선호도가 낮은 의원 TOP 3', low, '싫어요가 더 많은 의원이 아직 없어요.')


# ---------------------------------------------------------------- 국회 둘러보기
def party_outliers():
    """정당 의원 대부분이 속한 성향 그룹과 다른 그룹에 있는 의원 (5명 이상 정당만)"""
    if 'group' not in coords.columns:
        return pd.DataFrame(), 0.0
    rows, total, same = [], 0, 0
    for party, g in coords.groupby('POLY_NM'):
        if len(g) < 5:
            continue
        main = g['group'].mode().iloc[0]
        total += len(g)
        same += int((g['group'] == main).sum())
        for mona, r in g[g['group'] != main].iterrows():
            rows.append({'의원': r['HG_NM'], '정당': party, '지역구': r.get('ORIG_NM', ''),
                         '당 다수가 있는 그룹': main, '이 의원의 그룹': r['group']})
    return pd.DataFrame(rows), (same / total if total else 0.0)


def explore_page():
    st.header('국회 둘러보기')
    st.subheader('의원 표결 성향 지도')

    n = len(coords)
    with st.container(border=True, key='map_explain'):
        st.markdown('**이 지도는 무엇을 보여 주나요?**')
        st.markdown(f'- 점 하나가 국회의원 한 명이에요 (표결 참여가 충분한 의원 {n}명).\n'
                    '- 찬반이 갈린 **쟁점 법안**에 각 의원이 찬성·반대·기권한 기록을 모아, '
                    '**투표가 비슷한 의원끼리 가까이** 놓이도록 평면에 펼쳤어요 (PCA).\n'
                    '- 가로·세로 축 자체는 진보·보수 같은 뜻이 없어요. **점 사이의 거리**만 보면 돼요.')
        st.markdown('**왜 보여 주나요?**')
        st.markdown('- 정당 이름이나 뉴스 이미지가 아니라 **실제 투표**로 보면 국회가 어떻게 나뉘는지 확인할 수 있어요.\n'
                    '- 같은 정당인데 멀리 떨어진 의원, 다른 정당인데 가까운 의원을 찾아보면 '
                    '"말이 아닌 기록"으로 의원을 볼 수 있어요.')

    outliers, same_rate = party_outliers()
    if 'group' in coords.columns:
        comp = pd.crosstab(coords['group'], coords['POLY_NM'])
        lines = []
        for grp, row in comp.iterrows():
            top = row[row > 0].sort_values(ascending=False)
            parts = ', '.join(f'{p} {c}명' for p, c in top.head(3).items())
            lines.append(f'<b>{grp}</b> ({int(row.sum())}명): {parts}' + (' 등' if len(top) > 3 else ''))
        st.markdown('**지도에서 읽을 수 있는 것**')
        items = [f'의원들은 투표 패턴에 따라 크게 <b>{len(comp)}개 무리(성향 그룹)</b>로 나뉘어요.'] + lines + [
            f'정당별로 보면 의원의 <b>{same_rate:.0%}</b>가 자기 당 대부분과 같은 무리에 있어요. '
            '즉, 쟁점 법안에서는 <b>대부분 소속 정당과 같은 방향으로 투표</b>한다는 뜻이에요.',
            f'자기 당 대부분과 <b>다른 무리</b>에 있는 의원은 <b>{len(outliers)}명</b>이에요'
            + (' (아래 표).' if len(outliers) else '.')]
        st.markdown('<ul>' + ''.join(f'<li>{t}</li>' for t in items) + '</ul>', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 2])
    color = c1.radio('색 구분', ['정당', '성향 그룹'], horizontal=True, key='map_color_explore')
    order = coords.sort_values('HG_NM').index
    pick = c2.selectbox('지도에서 의원 찾기', [None] + list(order), key='map_pick',
                        format_func=lambda m: '선택 안 함' if m is None else member_label(m))
    st.plotly_chart(map_figure(highlight=[pick] if pick else None,
                               color_by='group' if color == '성향 그룹' and 'group' in coords.columns else 'POLY_NM'),
                    width='stretch', key='map_explore', config=LOCKED_CHART)
    st.caption('점 위에 마우스를 올리면 의원 이름이 나와요. 성향 그룹은 K-Means로 나눈 것이며, '
               '실루엣 점수가 가장 높은 개수를 사용했습니다.')
    if not outliers.empty:
        st.markdown('**자기 당 대부분과 다른 무리에 있는 의원**')
        st.markdown(outliers.to_html(index=False, classes='rank-table', border=0, escape=True),
                    unsafe_allow_html=True)
        st.caption('이 의원들은 쟁점 법안에서 소속 정당 다수와 다르게 투표한 경우가 많다는 뜻이에요. '
                   '[의원 검색]에서 실제 표결 기록을 확인해 보세요.')

    st.divider()
    st.subheader('정당별 관심 분야 (법안 발의 비중)')
    sp = data['sponsorship'].merge(members[['POLY_NM']], left_on='MONA_CD', right_index=True)
    heat = sp.pivot_table(index='POLY_NM', columns='field', values='weight', aggfunc='sum', fill_value=0)
    heat = heat.reindex(columns=[f for f in FIELDS if f in heat.columns])
    heat = heat.div(heat.sum(axis=1), axis=0)
    size = members['POLY_NM'].value_counts()
    heat = heat.loc[size.index.intersection(heat.index)]
    heat.index = [f'{p} ({size[p]}명)' for p in heat.index]
    fig = px.imshow(heat, text_auto='.0%', color_continuous_scale='Blues', aspect='auto',
                    labels=dict(x='분야', y='정당', color='비중'))
    st.plotly_chart(fig, width='stretch', key='party_field', config={'staticPlot': True})   # 그림처럼 고정
    st.caption('색이 진할수록 그 정당이 그 분야 법안을 많이 냈다는 뜻이에요 (대표발의 1.0, 공동발의 0.2로 '
               '가중한 발의 점수를 정당별 합계 대비 비율로 나타냄). 정당마다 어떤 분야에 힘을 쏟는지 비교해 보세요.')


# ---------------------------------------------------------------- 의원 검색
def search_page():
    st.header('의원 검색')
    st.caption('설문 없이도 아무 의원의 실제 표결·발의 기록을 볼 수 있습니다. '
               '설문을 마쳤다면 내 답과 비교해서 보여 드립니다.')
    search_detail()


@st.fragment
def search_detail():
    """의원 고르기 + 기록 (fragment: 다른 의원을 골라도 이 부분만 다시 그림)"""
    order = members.sort_values('HG_NM').index
    pick = st.selectbox('의원 선택 (이름으로 검색)', order, format_func=member_label, key='search_pick')
    action_row(pick, 'search')
    records.show_member(pick, data, matcher, ss.get('survey'), key='search')


# ---------------------------------------------------------------- 6·7. 내 정보 (로그인 전용)
def _open_history(h):
    ss['survey'] = h['survey']
    ss.setdefault('saved_keys', set()).add(survey_key(h['survey']))
    ss['pending_menu'] = HOME


def _delete_history(history_id):
    ok, msg = auth.delete_history(history_id)
    ss['flash'] = ('success' if ok else 'error', msg)


def _delete_all():
    ok, msg = auth.delete_all_my_data()
    ss['saved_keys'] = set()
    ss['history_consent'] = False
    ss['flash'] = ('success' if ok else 'error', msg)


def kst(ts):
    try:
        return pd.Timestamp(ts).tz_convert('Asia/Seoul').strftime('%Y-%m-%d %H:%M')
    except Exception:
        return str(ts)[:16].replace('T', ' ')


def _open_scrap(mona):
    ss['scrap_open'] = mona


def _close_scrap():
    ss.pop('scrap_open', None)


def _unscrap(mona):
    auth.toggle_scrap(mona)
    if ss.get('scrap_open') == mona:
        _close_scrap()


def scrap_cards():
    """4. 스크랩한 의원을 한눈에 보는 카드 (한 줄에 3장). [기록 보기]를 누르면 카드 아래에 자세한 기록"""
    scraps = sorted((m for m in auth.my_scraps() if m in members.index), key=lambda m: members.loc[m, 'HG_NM'])
    if not scraps:
        st.info('스크랩한 의원이 없어요. 결과 화면이나 [의원 검색]에서 ☆ 스크랩을 눌러 보세요.')
        return
    st.caption(f'스크랩한 의원 {len(scraps)}명 · 카드의 [기록 보기]를 누르면 아래에 실제 표결·발의 기록이 열립니다.')

    s = ss.get('survey')
    res = cached_match(json.dumps(s, sort_keys=True, ensure_ascii=False, default=str)) if s else None
    bills = data['sponsored']

    for start in range(0, len(scraps), 3):
        cols = st.columns(3)
        for col, mona in zip(cols, scraps[start:start + 3]):
            m = members.loc[mona]
            lead = bills[bills['RST_MONA_CD'] == mona]
            passed = int(lead['PROC_RESULT'].isin(PASSED).sum()) if 'PROC_RESULT' in lead else 0
            fields = matcher.field_counts.loc[mona] if mona in matcher.field_counts.index else pd.Series(dtype=float)
            top_fields = [f for f, v in fields.sort_values(ascending=False).head(2).items() if v > 0]
            with col.container(border=True):
                st.markdown(f"### {m['HG_NM']}")
                st.markdown(f"**{m['POLY_NM']}** · {m['ORIG_NM']}")
                st.caption(f"주로 낸 법안 분야: {', '.join(top_fields) or '-'}  \n"
                           f"대표발의 {len(lead):,}건 (가결 {passed:,}건)")
                if res is not None and mona in res.index:
                    r = res.loc[mona]
                    rank = int(res.index.get_loc(mona)) + 1
                    st.markdown(f"🧭 나와 **{int(r['agree'])} / {int(r['common'])}문항** 같은 입장 · "
                                f"종합 {pct(r['total'])} ({rank}위)")
                else:
                    st.caption('설문을 마치면 나와 얼마나 맞는지도 보여 드려요.')
                b1, b2 = st.columns(2)
                b1.button('📄 기록 보기', key=f'open_{mona}', on_click=_open_scrap, args=(mona,), width='stretch',
                          type='primary' if ss.get('scrap_open') == mona else 'secondary')
                b2.button('스크랩 해제', key=f'unscrap_{mona}', on_click=_unscrap, args=(mona,), width='stretch')

    pick = ss.get('scrap_open')
    if pick in scraps:
        with st.container(border=True):
            head, close = st.columns([5, 1], vertical_alignment='center')
            head.markdown(f"#### 📄 {members.loc[pick, 'HG_NM']} 의원의 기록")
            close.button('닫기 ✕', key='close_scrap', on_click=_close_scrap, width='stretch')
            records.show_member(pick, data, matcher, s, key=f'my_{pick}')


def my_page():
    user = auth.current_user()
    if user is None:                          # 메뉴에 안 보이지만 혹시 모를 접근 차단
        st.info('로그인하면 볼 수 있습니다.')
        return
    st.header('내 정보')
    st.caption(f"👤 {user['name']} 님의 활동 내역입니다. 이 정보는 본인만 볼 수 있습니다.")
    t1, t2, t3 = st.tabs(['🗂️ 활동 내역 (매칭 기록)', '⭐ 스크랩한 의원', '👍 내가 남긴 평가'])

    with t1:
        hist = auth.list_history()
        if not hist:
            st.info('아직 저장된 매칭 기록이 없어요. 설문을 마치고 결과 화면에서 [동의하고 저장]을 눌러 주세요.')
        for h in hist:
            with st.container(border=True):
                sv_ = h.get('survey') or {}
                top = h.get('top5') or []
                answered = sum(v is not None for v in (sv_.get('answers') or {}).values())
                st.markdown(f"**{kst(h['created_at'])}** · 가치관 {answered}문항 응답 · "
                            f"관심 분야 {', '.join(sv_.get('interests') or []) or '없음'}")
                st.caption('TOP 5: ' + ', '.join(f"{t.get('name')}({t.get('party')})" for t in top))
                c1, c2, _ = st.columns([1, 1, 3])
                c1.button('결과 다시 보기', key=f"hv_{h['id']}", on_click=_open_history, args=(h,), width='stretch')
                c2.button('삭제', key=f"hd_{h['id']}", on_click=_delete_history, args=(h['id'],), width='stretch')

    with t2:
        scrap_cards()

    with t3:
        mine = auth.my_reactions()
        likes = [m for m, v in mine.items() if v == 1 and m in members.index]
        dislikes = [m for m, v in mine.items() if v == -1 and m in members.index]
        c1, c2 = st.columns(2)
        with c1.container(border=True):
            st.markdown('**👍 좋아요한 의원**')
            for m in likes:
                st.write('· ' + member_label(m))
            if not likes:
                st.caption('없음')
        with c2.container(border=True):
            st.markdown('**👎 싫어요한 의원**')
            for m in dislikes:
                st.write('· ' + member_label(m))
            if not dislikes:
                st.caption('없음')
        st.caption('평가를 바꾸거나 취소하려면 결과 화면에서 같은 버튼을 다시 누르세요.')

    st.divider()
    with st.expander('🗑️ 내 데이터 모두 삭제'):
        st.caption('활동 내역, 스크랩, 좋아요·싫어요를 모두 지웁니다. 되돌릴 수 없어요. (계정은 남습니다)')
        sure = st.checkbox('네, 모두 삭제합니다.', key='confirm_delete_all')
        st.button('모두 삭제', disabled=not sure, on_click=_delete_all, key='delete_all')


# ---------------------------------------------------------------- 1. 화면이 바뀌면 맨 위로
def scroll_to_top_if_page_changed(menu):
    """메뉴를 바꾸거나 설문 → 결과처럼 화면이 바뀌었을 때만 스크롤을 맨 위로 올린다.
    Streamlit은 화면 내용이 바뀌어도 스크롤 위치를 그대로 두기 때문에, 작은 자바스크립트로 올려 준다."""
    page = (f"{menu}|{'result' if menu == HOME and ss.get('survey') else 'survey'}|"
            f"{ss.get('survey_step', 0)}|{survey_key(ss.get('survey'))}")
    if ss.get('last_page') == page:
        return
    ss['last_page'] = page
    ss['scroll_count'] = ss.get('scroll_count', 0) + 1     # 내용이 매번 달라야 스크립트가 다시 실행됨
    st.html(f"""<script>
      // {ss['scroll_count']}
      (function () {{
        function up() {{
          document.querySelectorAll('[data-testid="stMain"], [data-testid="stAppViewContainer"], section.main')
            .forEach(el => el.scrollTo({{top: 0, behavior: 'instant'}}));
          window.scrollTo(0, 0);
        }}
        up(); setTimeout(up, 150); setTimeout(up, 400);
        // 이전 페이지 요소 숨기기: 새 페이지를 그리는 동안만 켰다가 끔
        document.body.classList.add('page-switching');
        setTimeout(() => document.body.classList.remove('page-switching'), 2500);
      }})();
    </script>""", unsafe_allow_javascript=True)


# ---------------------------------------------------------------- 화면 구성
sidebar()
menu = ss.get('menu', HOME)
scroll_to_top_if_page_changed(menu)
header()
if menu == EXPLORE:
    explore_page()
elif menu == SEARCH:
    search_page()
elif menu == MYPAGE:
    my_page()
else:
    if ss.get('survey'):
        result_page()
    else:
        survey_page()
footer()
