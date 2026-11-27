NA는 어때? — 인공지능 프로그래밍 J조 (엄재훈, 오지훈, 최영은)
배포 주소: https://na-eottae.streamlit.app/

[1_데이터_코드] Google Colab 노트북 (01 → 04 순서로 실행)
  01_데이터수집      열린국회정보 Open API로 의원·표결·발의 데이터 수집
  02_전처리          집단 불참 규칙, 표결 행렬, 직업군, 발의 관계표, 분야 매핑
  03_분석_모델       PCA, K-Means, TF-IDF+로지스틱 회귀, 설문 문항, 매칭 엔진·검증
  04_웹사이트_실행   웹용 데이터(app_data) 내보내기, 웹사이트 실행
  ※ API 키는 Colab 보안 비밀(ASSEMBLY_API_KEY)에 넣어야 실행됨

[2_웹_코드] Streamlit 웹사이트
  app.py          화면 전체 (설문, 결과, 국회 둘러보기, 의원 검색, 내 정보)
  src/            matching.py(매칭 엔진), survey.py(설문·예외 처리),
                  records.py(의원 실제 기록), auth.py(회원 기능)
  data/           03·04 노트북이 만든 웹용 데이터
  supabase_setup.sql  회원 기록 테이블과 보안(RLS) 설정
  ※ 보안을 위해 API·DB 키(secrets.toml)는 포함하지 않음
