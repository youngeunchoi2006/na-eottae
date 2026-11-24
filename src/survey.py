"""설문 선택지와 입력 검사 (중간보고서의 '예외 처리' 기준)
- 입력 단계에서 차단: 성별·지역·직업·가치관 척도는 모두 선택형
- 누락·무효 응답: '모르겠음'은 계산 제외, 유효 응답 5개 미만이면 추가 응답 요청
- 잘못된 가중치: 모두 0이면 기본값으로 복원
"""
from matching import ANSWER_SCORE, DEFAULT_WEIGHTS

NOT_SELECTED = '선택 안 함'

SIDO = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '경기',
        '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']

# 의원 약력에서 분류한 주직업군(02번 노트북)과 같은 이름 + 사용자용 선택지
JOBS = ['학생', '법조', '의료·보건', '교육·학계', '언론·방송', '노동·시민사회',
        '경제·기업', '군·경찰·소방', '행정·공직', '정치(지방의회·정당)', '기타']

GENDERS = ['남성', '여성']

ANSWER_LABELS = list(ANSWER_SCORE.keys())          # 매우 그렇다 ~ 모르겠음
SCORE_TO_LABEL = {v: k for k, v in ANSWER_SCORE.items() if v is not None}

MIN_VALID_ANSWERS = 5


def clean_profile(gender, birth_year, sido, job):
    """선택 안 함은 빼고 매칭 엔진 형식으로 정리"""
    profile = {}
    if gender in GENDERS:
        profile['gender'] = gender
    if isinstance(birth_year, int):
        profile['birth_year'] = birth_year
    if sido in SIDO:
        profile['sido'] = sido
    # '학생'·'기타'는 의원 직업군에 대응하는 값이 없어 비교에서 뺀다 (모든 의원 0점이 되어 순위만 흔들림)
    if job in JOBS and job not in ('학생', '기타'):
        profile['job'] = job
    return profile


def clean_interests(picks):
    """1~3순위 선택에서 '선택 안 함'과 중복을 빼고 순서 유지"""
    out = []
    for p in picks:
        if p and p != NOT_SELECTED and p not in out:
            out.append(p)
    return out


def clean_weights(profile_w, interest_w, value_w):
    """슬라이더 값(0~100) → 합이 1인 가중치. 모두 0이면 기본값"""
    raw = {'profile': profile_w, 'interest': interest_w, 'value': value_w}
    total = sum(max(v, 0) for v in raw.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS), '가중치가 모두 0이라 기본값(0.2 / 0.3 / 0.5)으로 계산했습니다.'
    return {k: max(v, 0) / total for k, v in raw.items()}, None


def validate(answers, interests):
    """answers: {qid: 점수 또는 None}
    반환: (errors, warnings) — errors가 있으면 매칭하지 않음"""
    errors, warnings = [], []
    valid = [v for v in answers.values() if v is not None]
    if len(valid) < MIN_VALID_ANSWERS:
        errors.append(f"가치관 문항에 '모르겠음' 외의 답을 최소 {MIN_VALID_ANSWERS}개 이상 골라 주세요. "
                      f"(지금 {len(valid)}개)")
    elif len(set(valid)) == 1:
        warnings.append('모든 문항에 같은 답을 하셨어요. 결과가 정확하지 않을 수 있습니다.')
    if not interests:
        warnings.append('관심 분야를 고르지 않아 관심 분야 점수는 계산에서 제외했습니다.')
    return errors, warnings
