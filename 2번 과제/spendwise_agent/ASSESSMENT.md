# SpendWise 웹 재개발 평가 점검

기준 소스는 `jamin3874-oss/3rd-Project`의 `47514ef954855767b310764da27bb54a33cfb322` 커밋이다. 아래 표에서 기존 판정은 사용자 제공 사진에 기록된 결과이며, 이번 열은 로컬 재검증 결과다.

| 번호 | 기존 판정 · 기준 | 이번 변경과 증빙 |
|---|---|---|
| 1 | FAIL · 공개 URL | 같은 서비스에 React와 FastAPI를 배포하는 Dockerfile과 [절차](DEPLOY.md)를 작성했다. 공개 배포와 외부 접속 캡처 대기. |
| 2 | FAIL · Swagger | 로컬 브라우저에서 [Swagger 화면](evidence/swagger.png)을 열었다. 실제 앱에서 생성한 [OpenAPI](evidence/openapi.json)에 요청·응답이 있다. |
| 3 | FAIL · Firestore 연동 및 목록 갱신 | 서울 리전의 실제 Firestore에서 콘솔로 예시 지출 [4,500원 등록](evidence/firestore-before.jpg) → [5,200원 수정](evidence/firestore-after.jpg) → 새로고침 후 유지 확인. 웹 목록 갱신은 메모리 모드에서 검증했다. FastAPI를 통한 실서비스 왕복은 검증 대기. |
| 4 | FAIL · 요약 API 및 시스템 프롬프트 | 월 요약 API와 프롬프트가 같은 함수를 사용한다. [API 사례](evidence/local-api.json)와 [Claude 모의 호출 기록](evidence/claude-mock.json)을 확인할 수 있다. 실제 모델 재호출 대기. |
| 5 | FAIL · 대화 불러오기 | 예산 대화를 저장하고 브라우저를 새로고침한 뒤 [대화 탭](evidence/chat-mobile.png)에서 복원 확인. |
| 6 | FAIL · 모바일 | [390px 화면](evidence/overview-mobile.png)에서 가로 넘침 없이 한 열로 표시. [1080px 화면](evidence/overview-desktop.png)은 두 열. |
| 7 | PASS · 역할 분리 | README에 파일별 책임과 데이터 경계를 추가했다. |
| 8 | FAIL · 컬렉션 설계 | README에 data 및 conversations 문서 키, 저장 필드, 조회 순서, 비정규화 이유를 명시했다. |
| 9 | FAIL · Pydantic | Expense, Record, Chat, Turn, Summary를 OpenAPI에 노출했다. 음수 금액이 HTTP 422로 거절되는 테스트 통과. |
| 10 | FAIL · 화면 사이의 상태 | README의 화면 흐름 및 frontend/app.jsx 참조. 예산 200,000원에서 수정한 거래 5,200원을 뺀 194,800원이 개요에 반영됐다. |
| 11 | PASS · 컨텍스트 주입 | README에 비용과 정확도 측면의 장단점 및 범위를 추가했다. |
| 12 | PASS · 요약 재사용 | HTTP 월간 개요, 채팅 요약 도구, 첫 모델 요청이 summary를 공유한다. 실제 GET 응답은 API 사례에 포함했다. |
| 13 | PASS · 대화 로그 | 명령·도구·인자·결과 및 버전을 저장하는 시점과 목적을 README에 명시했다. |
| 14 | PASS · 키 보호 | 배포용 비밀 설정과 실행 계정 권한을 DEPLOY에 명시했다. Docker 빌드에는 소스와 공개 자산만 복사한다. |
| 15 | FAIL · 콜드스타트 | DEPLOY에 첫 요청 지연, 클라이언트 재사용, 예열, 최소 인스턴스 비용, 측정 방법을 명시했다. |
| 16 | PASS · CORS 기본 정책 | 동일 오리진 기본값과 분리 배포의 허용 주소 설정 예시를 README에 명시했다. 허용·미허용 오리진 사전 요청을 테스트한다. |
| 17 | PASS · DB 및 에이전트 입력 검증 | 거래·월·대화·도구 허용 규칙과 거부 예시를 README에 정리했다. 잘못된 요청의 HTTP 422 및 미저장을 테스트한다. |
| 18 | PASS · 집계 기준 변경 | README에 월 경계, 날짜 기준, 수정할 함수 및 검증 사례를 추가했다. |

## 실행 기록

- Windows, Python 3.14. 기존 CLI·Claude 모의·시나리오 테스트 18개와 웹 API 테스트 4개 통과. 웹 API 테스트는 메모리 저장소와 프로세스 내부 HTTP 전송을 사용했다.
- Chrome에서 모바일 입력, 거래 수정, 합계, 예산, 대화 재조회, 모바일 너비, 데스크톱 레이아웃, Swagger 렌더링을 확인했다. 브라우저 요청을 로컬 프로세스 안에서 실제 FastAPI에 전달했다.
- 기존 로컬 HTTP 서버 테스트 5개는 이 환경에서 루프백 TCP 연결이 차단되어 실행 오류가 발생했다. 새 웹 테스트의 통과 수에서 제외했다. Firestore 에뮬레이터 테스트는 준비되어 있으며 실행 환경이 필요하다.
- Firebase 프로젝트 `spendwise-f6d6d`의 Spark 요금제에서 Standard 기본 데이터베이스를 서울(asia-northeast3)에 프로덕션 모드로 생성했다. 검증 문서는 `data/0eea85e2-70ac-4917-a118-de950b170001`이다.
- 기존 results/live_test_results.json은 이전 CLI 버전의 기록이다. FastAPI의 실제 Firestore 접근 및 대화 저장, Claude 실호출, 공개 배포 URL은 별도 검증이 필요하다.
