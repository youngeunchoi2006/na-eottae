"""나와 잘 맞는 국회의원 — 매칭 엔진 (03번 노트북 8번 셀과 같은 코드)
종합 점수 = 0.2 × 프로필 + 0.3 × 관심 분야 + 0.5 × 가치관 (중간보고서 기준)
"""
import numpy as np
import pandas as pd

# 설문 5점 척도 → 점수 (4차 회의록 기준). '모르겠음'은 계산에서 제외
ANSWER_SCORE = {'매우 그렇다': 1.0, '그렇다': 0.5, '보통이다': 0.0,
                '아니다': -0.5, '전혀 아니다': -1.0, '모르겠음': None}

FIELDS = ['경제·재정', '노동·고용', '보건·복지', '교육', '환경·에너지', '국방·외교',
          '과학기술', '농어업', '법·사법', '행정·안전', '주거·교통', '문화·가족']

DEFAULT_WEIGHTS = {'profile': 0.2, 'interest': 0.3, 'value': 0.5}
MIN_COMMON = 3          # 가치관 점수를 내려면 최소 몇 문항이 겹쳐야 하는지
PROFILE_WEIGHTS = {'sido': 0.4, 'job': 0.3, 'gender': 0.15, 'age': 0.15}


class Matcher:
    def __init__(self, members, questions, question_votes, sponsorship):
        """members: MONA_CD가 인덱스인 현직 의원 표
        questions: questions.csv / question_votes: question_votes.parquet
        sponsorship: 의원-법안 발의 관계표 (weight, field 포함)"""
        self.members = members
        self.questions = questions.set_index('qid')

        # 1) 가치관: 의원 × 문항 표결 표 (+1 찬성 / 0 기권 / -1 반대 / NaN 제외)
        bill_to_q = dict(zip(questions['BILL_ID'], questions['qid']))
        qv = question_votes[question_votes['MONA_CD'].isin(members.index)].copy()
        qv['qid'] = qv['BILL_ID'].map(bill_to_q)
        self.vote = (qv.pivot_table(index='MONA_CD', columns='qid', values='vote_A', aggfunc='first')
                       .reindex(index=members.index, columns=self.questions.index))

        # 2) 관심 분야: 의원별 분야 발의 점수 (대표 1.0, 공동 0.2) → 길이 1로 정규화
        sp = sponsorship[sponsorship['MONA_CD'].isin(members.index)]
        counts = (sp.pivot_table(index='MONA_CD', columns='field', values='weight',
                                 aggfunc='sum', fill_value=0)
                    .reindex(index=members.index, columns=FIELDS, fill_value=0))
        norm = np.linalg.norm(counts.values, axis=1, keepdims=True)
        norm[norm == 0] = 1
        self.field_counts = counts
        self.field_profile = pd.DataFrame(counts.values / norm, index=counts.index, columns=FIELDS)

        # 3) 프로필: 시·도, 비례대표 여부, 성별, 출생연도, 주직업군
        orig = members['ORIG_NM'].fillna('')
        self.sido = orig.str.split().str[0]
        self.is_pr = orig.str.contains('비례대표')
        self.gender = members['SEX_GBN_NM'].fillna('').str[:1]
        self.birth_year = (pd.to_datetime(members['BTH_DATE'], errors='coerce').dt.year
                           if 'BTH_DATE' in members.columns else None)
        self.job = members['주직업군'] if '주직업군' in members.columns else None

    # ---------- 가치관 ----------
    def user_stance(self, answers):
        """{qid: 점수} → 법안 기준 입장 (역문항은 부호를 뒤집음)"""
        s = {}
        for qid, a in answers.items():
            if a is None or qid not in self.questions.index:
                continue
            s[qid] = a if self.questions.loc[qid, '방향'] == '정' else -a
        return pd.Series(s, dtype=float)

    def value_scores(self, answers):
        u = self.user_stance(answers)
        if u.empty:
            nan = pd.Series(np.nan, index=self.members.index)
            return nan, nan * 0, nan * 0
        m = self.vote[u.index]
        diff = (m - u).abs()                              # 0(같음) ~ 2(정반대)
        common = diff.notna().sum(axis=1)
        sim = 1 - diff.mean(axis=1) / 2                   # 0 ~ 1
        sim[common < MIN_COMMON] = np.nan
        agree = ((np.sign(m) == np.sign(u)) & (u != 0) & m.notna() & (m != 0)).sum(axis=1)
        return sim, agree, common

    # ---------- 관심 분야 ----------
    def interest_scores(self, top_fields):
        """top_fields: 관심 분야 1~3순위 리스트 → 코사인 유사도"""
        w = np.zeros(len(FIELDS))
        for rank, f in enumerate((top_fields or [])[:3]):
            if f in FIELDS:
                w[FIELDS.index(f)] = 3 - rank                # 1순위 3점, 2순위 2점, 3순위 1점
        if w.sum() == 0:
            return pd.Series(np.nan, index=self.members.index)
        w = w / np.linalg.norm(w)
        return pd.Series(self.field_profile.values @ w, index=self.members.index)

    # ---------- 프로필 ----------
    def profile_scores(self, profile):
        """profile: {'sido': '경북', 'job': '교육·학계', 'gender': '여성', 'birth_year': 2005}"""
        parts, weights = [], []
        if profile.get('sido'):
            s = (self.sido == profile['sido']).astype(float).values   # 비례대표는 지역 일치 없음(0)
            parts.append(s); weights.append(PROFILE_WEIGHTS['sido'])
        if profile.get('job') and profile['job'] != '기타' and self.job is not None:
            parts.append((self.job == profile['job']).astype(float).values); weights.append(PROFILE_WEIGHTS['job'])
        if profile.get('gender'):
            parts.append((self.gender == profile['gender'][:1]).astype(float).values); weights.append(PROFILE_WEIGHTS['gender'])
        if profile.get('birth_year') and self.birth_year is not None:
            gap = (self.birth_year - int(profile['birth_year'])).abs().clip(upper=30)
            parts.append((1 - gap / 30).fillna(0.5).values); weights.append(PROFILE_WEIGHTS['age'])
        if not parts:
            return pd.Series(np.nan, index=self.members.index)
        return pd.Series(np.average(np.vstack(parts), axis=0, weights=weights), index=self.members.index)

    # ---------- 종합 ----------
    def match(self, answers, top_fields=None, profile=None, weights=None):
        w = dict(DEFAULT_WEIGHTS, **(weights or {}))
        value, agree, common = self.value_scores(answers)
        parts = pd.DataFrame({'value': value,
                              'interest': self.interest_scores(top_fields),
                              'profile': self.profile_scores(profile or {})})
        wv = pd.Series(w)[parts.columns]
        avail = parts.notna()
        total = (parts.fillna(0) * wv).sum(axis=1) / (avail * wv).sum(axis=1).replace(0, np.nan)

        res = self.members[['HG_NM', 'POLY_NM', 'ORIG_NM']].join(parts)
        res['total'] = total
        res['agree'] = agree
        res['common'] = common
        if value.notna().any():                          # 가치관 비교가 안 되는 의원은 순위에서 제외
            res = res[res['value'].notna()]
        return res.sort_values(['total', 'value', 'interest'], ascending=False)

    @staticmethod
    def opposite(res, n=1, min_common=5):
        """생각이 가장 다른 의원 (가치관 점수가 가장 낮은 순)"""
        return res[res['common'] >= min_common].sort_values('value').head(n)

    @staticmethod
    def user_position(res, coords, n=5):
        """성향 지도 위 사용자 위치 = TOP n 의원 좌표의 평균"""
        top = res.head(n).index.intersection(coords.index)
        return coords.loc[top, ['x', 'y']].mean()
