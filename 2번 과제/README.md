# 2번 과제 — 나만의 AI 비서 구축

**SpendWise**는 거래를 등록·수정하고 월별 지출과 예산 잔액을 조회하는 가계부다. React와 FastAPI가 같은 Render 주소에서 실행되고 장부와 대화는 Firestore에 저장된다. [공개 가계부](https://spendwise-f6d6d.onrender.com/) · [Swagger API 문서](https://spendwise-f6d6d.onrender.com/docs)

## 채점 순서

1. 공개 가계부에 채점용 비밀번호를 입력하고 **2026년 11월**을 선택한다. 예시 거래 **과제 예시 카페 5,300원**과 대화 탭의 월 요약을 확인한다.
2. [재평가 보고서](spendwise_agent/REVIEW.md)에서 #1·3의 배포 화면, Firestore 수정 전후 캡처, HTTP 요청·응답 원본을 확인한다. 같은 문서에 #8·11·12·13의 설계 결정과 구현 링크가 있다.
3. 전체 요건은 [18개 항목 평가표](spendwise_agent/ASSESSMENT.md), 실행과 테스트 방법은 [프로젝트 README](spendwise_agent/README.md)에서 확인한다.

안드로이드 7.0 이상에서는 [SpendWise APK](https://raw.githubusercontent.com/jamin3874-oss/3rd-Project/main/2%EB%B2%88%20%EA%B3%BC%EC%A0%9C/spendwise_agent/android/SpendWise.apk)를 설치해 같은 온라인 장부를 열 수 있다. 웹 버전의 Claude Tool Use는 모의 호출로 검증했다. [검증 기록](spendwise_agent/evidence/claude-mock.json)
