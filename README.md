# NA는 어때? · 나와 가치관이 잘 맞는 국회의원은 누구일까

말이 아닌 기록으로 확인하기 — 설문에 답하면 제22대 국회의원의 **실제 본회의 표결·법안 발의 기록**과 비교해
생각이 비슷한 의원과 다른 의원을 찾아 주고, 그 의원들의 실제 기록을 보여 주는 웹 서비스입니다.

J조 · 엄재훈(조장), 오지훈, 최영은 · 인공지능 프로그래밍 팀 프로젝트

## 폴더 구성

```
assembly-web/
├── app.py                   웹 화면 (설문 → 결과 → 국회 둘러보기 → 의원 검색)
├── src/
│   ├── matching.py          매칭 엔진 (03번 노트북 8번 셀과 같은 코드)
│   ├── records.py           의원의 실제 표결·발의 기록 화면
│   ├── survey.py            설문 선택지와 입력 예외 처리
│   └── auth.py              Supabase 회원가입·로그인·활동 내역·스크랩·좋아요/싫어요
├── data/                    ← 03번 노트북 14번 셀이 만든 app_data 폴더의 파일 8개를 넣는 곳
├── requirements.txt
├── static/                  Pretendard 글꼴 (SIL OFL 라이선스)
├── supabase_setup.sql       Supabase 테이블 + RLS (한 번만 실행)
└── .streamlit/
    ├── config.toml          디자인 색(테마)과 글꼴 파일 사용 설정 ← 꼭 함께 올리기
    └── secrets.toml.example
```

`data/`에 들어갈 파일: `members.parquet`, `questions.csv`, `question_votes.parquet`, `coords.parquet`,
`sponsorship.parquet`, `sponsored_bills.parquet`, `field_classifier.joblib`, `_meta.json`

## 1. Supabase 준비 (한 번만)

1. Supabase 대시보드 → **SQL Editor** → `supabase_setup.sql` 내용을 붙여 넣고 Run
2. **Authentication → Sign In / Providers → Email** 에서 **Confirm email 끄기**
   (아이디를 `아이디@votematch.com` 형식으로 가입시키므로 확인 메일을 받을 수 없음)
3. `.streamlit/secrets.toml.example`을 복사해 `.streamlit/secrets.toml`로 저장하고 URL과 publishable 키 입력

secrets.toml이 없으면 회원 기능만 꺼지고 나머지는 그대로 동작합니다.

## 2. Colab에서 실행해 보기 (개발·확인용)

```python
# 셀 1: 코드 가져오기 + 데이터 복사
from google.colab import drive
drive.mount('/content/drive')
!rm -rf /content/assembly-web && cp -r /content/drive/MyDrive/assembly-match/assembly-web /content/assembly-web
!cp /content/drive/MyDrive/assembly-match/app_data/* /content/assembly-web/data/
%cd /content/assembly-web
!pip install -q -r requirements.txt
```

```python
# 셀 2: secrets.toml 만들기 (키는 Colab 보안 비밀에 SUPABASE_URL, SUPABASE_KEY로 등록해 두고 읽기)
from google.colab import userdata
import os
os.makedirs('.streamlit', exist_ok=True)
with open('.streamlit/secrets.toml', 'w') as f:
    f.write(f'SUPABASE_URL = "{userdata.get("SUPABASE_URL")}"\n')
    f.write(f'SUPABASE_KEY = "{userdata.get("SUPABASE_KEY")}"\n')
```

```python
# 셀 3: 실행 + 임시 외부 주소 (Colab을 끄면 주소도 사라짐)
!wget -q -O cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
!dpkg -i cloudflared.deb > /dev/null 2>&1
import subprocess, time, re
subprocess.Popen(['streamlit', 'run', 'app.py', '--server.port', '8501', '--server.headless', 'true'])
time.sleep(5)
tunnel = subprocess.Popen(['cloudflared', 'tunnel', '--url', 'http://localhost:8501'],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
for line in tunnel.stdout:
    m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
    if m:
        print('접속 주소:', m.group(0)); break
```

## 3. 제출·발표용 배포 (Streamlit Community Cloud)

1. GitHub에 새 저장소를 만들고 이 폴더 전체를 올립니다 (`data/` 포함, `secrets.toml`은 자동 제외).
2. share.streamlit.io → GitHub로 로그인 → **Create app** → 저장소 선택, Main file `app.py`, Advanced settings에서 Python 3.12 → Deploy
3. 앱 설정 → **Secrets**에 secrets.toml 내용을 붙여 넣기
4. 발표 전날 주소에 한 번 접속해 앱을 깨워 두기 (12시간 접속이 없으면 잠듦).
   Supabase 무료 프로젝트도 7일 동안 사용이 없으면 일시 정지되니 대시보드에서 확인.

## 설계 메모

- **매칭 점수** = 0.2 × 프로필 + 0.3 × 관심 분야 + 0.5 × 가치관 (보고서에서 정한 값으로 고정)
- **가치관**: 15문항 응답(+1 ~ −1)과 의원의 실제 표결(찬성 +1, 기권 0, 반대 −1)을 비교.
  역문항(1·5·7·11·12번)은 부호를 뒤집어 계산. 집단 불참은 반대로 처리하되, 14번(SMR)은 본회의 보이콧이라 계산에서 제외.
- **관심 분야**: 의원별 12개 분야 발의 점수(대표 1.0, 공동 0.2)와 1~3순위 관심 분야의 코사인 유사도.
- **프로필**: 거주 시·도(지역구 일치), 직업군(약력 기반 주직업군), 성별, 출생연도.
- **분야 분류 모델**: 법안명 TF-IDF + 로지스틱 회귀로 위원회 정보가 없는 발의 법안('기타')의 분야를 채움 (03번 13번 셀).
- **문항 도움말**: 15문항마다 💬 쉬운 설명과 ⓘ 도움말(법 내용 + 찬성·반대 주장)을 표시.
- **회원 기능** (오른쪽 위 [로그인] → 팝업): 로그인하면 [내 정보] 메뉴가 생김.
  - 활동 내역: 결과 화면에서 한 번 동의하면 매칭 결과(설문 응답 + TOP 5)가 저장되고, 다시 보기·삭제 가능.
  - 스크랩: 결과·검색 화면의 ☆ 버튼. [내 정보]에서 모아 보기.
  - 좋아요·싫어요: TOP 5 의원에게 1인 1표. 홈 맨 아래에 (좋아요 − 싫어요) 기준 높은/낮은 의원 TOP 3 표시.
- **처음 설정**: Supabase SQL Editor에서 `supabase_setup.sql`을 한 번 실행 (테이블 3개 + 집계 함수).
  Supabase 연결은 접속자마다 따로 만들고, 주소창에 사용자 정보를 넣지 않음.
