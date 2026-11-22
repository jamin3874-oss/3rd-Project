# 8번 과제 제출 파일·형식 점검표

이하 목록은 기존 CLI 버전용이다. 이번 웹 제출은 [평가 항목별 상태](ASSESSMENT.md)를 기준으로 점검한다.

재제출 시 [실서비스 증거와 여섯 항목 설계 보고서](REVIEW.md), [공개 웹 앱](https://spendwise-f6d6d.onrender.com/), [API 문서](https://spendwise-f6d6d.onrender.com/docs)를 함께 확인한다. 가계부 비밀번호는 채점자 전용 제출란에서 별도로 전달한다.

## 프로젝트와 보고서

- [x] **`README.md`**: 프로젝트 소개, 설치, 환경변수, 실행·테스트 방법
- [x] **`REPORT.md`**: Q1~Q3, 기능·아키텍처, 실사용 API 테스트 결과 6/6, 검증 한계
- [x] **`.py` 소스**: main.py, agent.py, backend.py, config.py, storage.py, tools.py, test_runner.py
- [x] **`requirements.txt`**: 실행에 필요한 라이브러리
- [x] **`.env.example`**: 비밀키를 넣지 않은 환경변수 예시
- [x] **`.gitignore`**: 실제 .env, SQLite, 임시 결과 등 비공개 파일 제외
- [x] **`tests/*.py`**: 오프라인 단위·통합 테스트
- [x] **`results/live_test_results.json`**: 사용자가 실제 코디세이 Claude 환경에서 실행한 6개 시나리오 전부 PASS 기록
- [x] **`sample_data/*.csv`**: 가상 테스트 데이터
- [ ] **GitHub 저장소에 이 최종 버전 업로드·링크 확인**: 현재 이 ZIP만 준비됨

## 제출 안내

1. GitHub `jamin3874-oss/3rd-Project`의 `2번 과제/spendwise_agent/`에 이 프로젝트 내용물을 업로드한다.
2. 소스 파일, README, REPORT, 실사용 JSON 증빙이 폴더에 그대로 존재해야 한다.
3. 제출 양식에서 GitHub Repository URL을 요구하면 **폴더 링크**를 제출한다.
4. ZIP 자체는 백업·전달용이며, GitHub 제출 지침과 구별한다.
5. `.env`, API 키, 개인 SQLite 데이터베이스 파일은 절대 업로드하지 않는다.

## 검증 범위

- 모의/단위 테스트: 최신 패키지에서 Python unittest 23개 PASS
- 실제 Claude Tool Use: 사용자가 제공한 `live_test_results.json`에 총 6개 PASS, FAIL 0, SKIP 0
- 원본과 테스트는 합성 거래이며 실제 개인 금융정보는 포함되지 않는다.
- 실제 API 응답 전문(전체 모델 content block)까지 별도 수집한 로그는 없고, 검증에 필요한 도구·결과와 입력이 JSON에 보존되어 있다.
