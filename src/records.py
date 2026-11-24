"""의원 기록 화면 (5차 회의록: TOP 5 의원의 실제 표결·발의 기록을 보여 준다)"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from matching import FIELDS
from survey import SCORE_TO_LABEL

LIKMS = 'https://likms.assembly.go.kr/bill/billDetail.do?billId='
PASSED = ['원안가결', '수정가결']


def vote_label(raw, vote_a):
    """의원 표결 표시: 집단 불참은 '불참(반대로 처리)', 계산 제외 불참은 '불참(계산 제외)'"""
    if raw in ('찬성', '반대', '기권'):
        return raw
    if pd.isna(vote_a):
        return '불참 (계산 제외)'
    return '불참 (정당 집단 불참 → 반대로 처리)'


def same_side(user_stance, member_vote):
    if pd.isna(user_stance) or pd.isna(member_vote) or user_stance == 0 or member_vote == 0:
        return '－'
    return '✅ 같음' if np.sign(user_stance) == np.sign(member_vote) else '❌ 다름'


def question_table(mona, data, matcher, answers=None):
    """설문 15문항에 대한 의원의 실제 표결 (+ 내 답과 비교)"""
    q = data['questions']
    qv = data['question_votes']
    mine = qv[qv['MONA_CD'] == mona].set_index('BILL_ID')
    stance = matcher.user_stance(answers) if answers else pd.Series(dtype=float)

    rows = []
    for _, r in q.iterrows():
        raw = mine['RESULT_VOTE_MOD'].get(r['BILL_ID'], None)
        va = mine['vote_A'].get(r['BILL_ID'], np.nan)
        row = {'문항': f"{int(r['qid'][1:])}. {r['질문문장']}",
               '이 의원의 실제 표결': vote_label(raw, va) if raw is not None else '기록 없음',
               '관련 법안': r['법안명'],
               '원문': LIKMS + r['BILL_ID']}
        if answers is not None:
            a = answers.get(r['qid'])
            row['내 답'] = SCORE_TO_LABEL.get(a, '모르겠음') if a is not None else '모르겠음'
            row['같은 입장?'] = same_side(stance.get(r['qid'], np.nan), va)
        rows.append(row)
    cols = ['문항', '내 답', '이 의원의 실제 표결', '같은 입장?', '관련 법안', '원문'] if answers is not None \
        else ['문항', '이 의원의 실제 표결', '관련 법안', '원문']
    return pd.DataFrame(rows)[cols]


def field_radar(mona, matcher, interests=None):
    counts = matcher.field_counts.loc[mona]
    share = counts / counts.sum() if counts.sum() > 0 else counts
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=list(share.values) + [share.values[0]], theta=FIELDS + [FIELDS[0]],
                                  fill='toself', name='이 의원의 발의 분야 비중', hoverinfo='skip'))
    if interests:
        mine = pd.Series(0.0, index=FIELDS)
        for rank, f in enumerate(interests[:3]):
            mine[f] = (3 - rank) / 3 * share.max()
        fig.add_trace(go.Scatterpolar(r=list(mine.values) + [mine.values[0]], theta=FIELDS + [FIELDS[0]],
                                      fill='toself', opacity=0.5, name='내 관심 분야 (1~3순위)', hoverinfo='skip'))
    fig.update_layout(height=380, margin=dict(l=40, r=40, t=30, b=30),
                      polar=dict(radialaxis=dict(visible=True, tickformat='.0%')),
                      legend=dict(orientation='h', y=-0.15, itemclick=False, itemdoubleclick=False),
                      dragmode=False)
    return fig


def show_member(mona, data, matcher, survey=None, key=''):
    """의원 한 명의 실제 표결·발의 기록. survey가 있으면 내 답과 비교해서 보여 준다."""
    m = data['members'].loc[mona]
    answers = survey.get('answers') if survey else None
    interests = survey.get('interests') if survey else None

    info = [m.get('POLY_NM', ''), m.get('ORIG_NM', '')]
    for col in ('REELE_GBN_NM', '주직업군'):
        if isinstance(m.get(col), str) and m.get(col):
            info.append(m[col])
    st.markdown(f"**{m['HG_NM']}** · " + ' · '.join(x for x in info if x))
    if isinstance(m.get('HOMEPAGE'), str) and m['HOMEPAGE'].startswith('http'):
        st.caption(f"[의원 홈페이지]({m['HOMEPAGE']})")

    # 1) 설문 문항에 대한 실제 표결
    st.markdown('##### 설문 문항에 대한 실제 본회의 표결')
    st.dataframe(question_table(mona, data, matcher, answers), hide_index=True, width='stretch',
                 column_config={'원문': st.column_config.LinkColumn('원문', display_text='보기')})

    # 2) 발의 활동
    st.markdown('##### 법안 발의 활동')
    sp = data['sponsorship']
    mine = sp[sp['MONA_CD'] == mona]
    bills = data['sponsored']
    lead = bills[bills['RST_MONA_CD'] == mona].copy()
    c1, c2, c3 = st.columns(3)
    c1.metric('대표발의', f"{len(lead):,}건")
    c2.metric('그중 가결', f"{lead['PROC_RESULT'].isin(PASSED).sum():,}건" if 'PROC_RESULT' in lead else '-')
    c3.metric('공동발의', f"{(mine['role'] == '공동').sum():,}건")

    left, right = st.columns([1, 1])
    with left:
        # 그래프는 고정 (끌기·확대·범례 클릭 불가). 마우스를 올리면 '전체 화면' 버튼 하나만 보임 (app.py CSS)
        st.plotly_chart(field_radar(mona, matcher, interests), width='stretch', key=f'radar_{key}_{mona}',
                        config={'displayModeBar': True, 'displaylogo': False, 'scrollZoom': False,
                                'doubleClick': False})
    with right:
        if lead.empty:
            st.info('대표발의한 법안이 없습니다.')
        else:
            field_of = data['bill_field']
            lead['분야'] = lead['BILL_ID'].map(field_of).fillna('기타')
            pick = st.selectbox('분야로 거르기', ['전체'] + [f for f in FIELDS if f in set(lead['분야'])],
                                key=f'field_{key}_{mona}')
            if pick != '전체':
                lead = lead[lead['분야'] == pick]
            lead = lead.sort_values('PROPOSE_DT', ascending=False)
            show = lead.rename(columns={'PROPOSE_DT': '발의일', 'BILL_NAME': '법안명',
                                        'PROC_RESULT': '처리 결과', 'DETAIL_LINK': '원문'})
            cols = [c for c in ['발의일', '법안명', '분야', '처리 결과', '원문'] if c in show.columns]
            st.dataframe(show[cols], hide_index=True, width='stretch', height=320,
                         column_config={'원문': st.column_config.LinkColumn('원문', display_text='보기')})
    st.caption('표결·발의 기록 출처: 열린국회정보 Open API. 원문 링크는 국회 의안정보시스템으로 연결됩니다.')
