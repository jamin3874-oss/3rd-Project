# SpendWise · 월간 가계부

거래를 기록하고 월별 지출과 예산 잔액을 확인하는 한국어 가계부다. 웹에서는 React → FastAPI → Firestore 순서로 데이터를 처리한다. 브라우저에서 Claude 사용을 선택하면 백엔드가 월별 요약과 최근 대화 6건을 모델에 전달한다. 단일 채점용 장부이므로 가상의 거래로 시연한다.

[설치·로컬 실행·배포](DEPLOY.md) · [18개 평가 항목과 증빙](ASSESSMENT.md) · [모바일 실행 화면](evidence/overview-mobile.png)

## 채점용 공개 서비스

[SpendWise 가계부](https://spendwise-f6d6d.onrender.com/) · [Swagger UI](https://spendwise-f6d6d.onrender.com/docs) · [OpenAPI JSON](https://spendwise-f6d6d.onrender.com/openapi.json) · [서버 상태](https://spendwise-f6d6d.onrender.com/health)

로그인 사용자명은 `spendwise`다. 운영자는 Render 대시보드의 해당 서비스 → Environment → `SPENDWISE_PASSWORD`에서 비밀번호를 확인해 채점자에게 비공개로 전달한다. 2026년 11월 장부에서 **과제 예시 카페 5,300원**과 **월 요약 대화**를 확인할 수 있다. Swagger는 로그인 없이 열리며 보호된 API를 호출할 때는 Authorize에서 같은 장부 계정을 사용한다.

## 모듈 경계

| 파일 | 담당 |
|---|---|
| frontend/app.jsx, public/ | 거래 폼, 월 선택, 채팅, 새로고침, 반응형 레이아웃과 브라우저용 배포 파일 |
| web_api.py | HTTP Basic 로그인, Pydantic 검증, 거래·대화·월간 집계 API, 월 요약을 포함하는 모델 요청 |
| web_store.py | Firestore 클라이언트 재사용, 문서 조회, 거래·대화 배치 저장, 테스트용 메모리 저장소 |
| agent.py | 명령 해석, Claude 호출, 허용 도구 검증 및 결과 전달 |
| tools.py, storage.py | CLI의 SQLite 집계·예산·CSV·감사 로그. 상호 분류와 월 유효성 검사는 웹에서도 사용 |
| main.py, backend.py | 기존 대화형 CLI와 로컬 HTTP 버전의 진입점 |

## API 및 화면 흐름

| 요청 | 입력 및 동작 |
|---|---|
| GET /health | 프로세스 가동 상태 |
| GET /docs, /openapi.json | Swagger UI와 요청·응답 스키마 |
| POST /api/data | txn_date, merchant, 양의 정수 amount를 검증하고 분류한 지출을 저장. 생성 결과 201 |
| PUT /api/data/{id} | 거래 날짜, 상호, 금액을 함께 교체. 날짜를 다른 달로 옮기면 해당 월 집계로 이동 |
| GET /api/data?month=2026-11 | 해당 월 거래를 날짜 내림차순으로 조회 |
| GET /api/data/summary?month=2026-11 | 합계, 건수, 분류별 합계, 예산과 잔액 |
| POST /api/chat | message, month, 선택적 request_id. 응답에는 대화 ID, 시각, 답변, 사용 도구 포함 |
| GET /api/conversations?limit=50 | 최근 대화부터 반환. 1~100건 선택 가능 |

화면 흐름은 **거래 등록·수정 또는 채팅 전송 → 서버 저장 성공 → 선택 월 목록·요약·대화 다시 조회 → 개요와 대화에 반영** 순서다. React의 공통 부모가 탭과 월을 관리한다. 월을 빠르게 바꿔도 이전 월 조회가 새 화면을 덮지 않는다. 브라우저를 새로 열면 서버에서 대화를 다시 불러온다.

## Firestore 모델

| 컬렉션 | 문서 키 및 주요 필드 | 설계 이유와 조회 패턴 |
|---|---|---|
| data (지출) | UUID, kind=expense, txn_date, month, merchant, amount, category | 개별 거래를 편집한다. month를 함께 저장해 날짜 전체 스캔 없이 해당 월만 조회한다. |
| data (예산) | budget-{월}-{분류}, kind=budget, month, category, amount | 같은 월·분류는 같은 문서를 갱신한다. 월 조회 한 번으로 지출·예산을 읽고 잔액을 산출한다. |
| conversations | 요청 UUID, created_at(UTC), month, message, reply, tool, audit, schema_version | 최근 시각 내림차순 조회. audit의 인자·도구 결과를 구조화해 저장해 도구별 필드를 보존한다. 단일 장부이며 여러 사용자로 확장할 때는 인증된 사용자 ID로 읽기·쓰기를 분리해야 한다. |

웹 도구는 변경을 준비한 후 한 대화의 거래·예산과 대화 기록을 Firestore 배치로 함께 커밋한다. 요청 ID가 같으면 이전 응답을 반환한다. 같은 ID로 다른 메시지를 보내면 409를 반환한다. 기존 SQLite 데이터와 웹 저장소는 별도 장부다.

## 브라우저 접근 정책과 입력 검증

React와 API를 같은 주소에서 제공하는 기본 설정에서는 별도 오리진을 허용하지 않는다. 다른 프론트엔드에서 API를 호출해야 하면 서버의 `SPENDWISE_ALLOWED_ORIGINS`에 실제 프론트엔드 주소를 쉼표로 구분해 설정한 뒤 서버를 재시작한다. 예를 들어 `https://ledger.example.org,http://localhost:5173`처럼 프로토콜과 포트까지 맞춰 지정한다. 경로와 와일드카드는 허용하지 않는다. 분리 배포 시 프론트엔드 요청 주소도 실제 API로 지정해야 한다. 허용 오리진에서도 장부 인증은 필요하다.

| 입력 | 허용 범위 | 거부 예시 |
|---|---|---|
| 거래 | 실제 거래일, 공백을 제거한 상호 1~80자, 금액 1~1조 원의 정수 값 | 2월 30일, 공백 상호, 음수·소수 금액, 정의되지 않은 필드 |
| 월·대화 | 유효한 YYYY-MM, 공백 제거 후 메시지 1~2,000자 | 2026-13, 빈 메시지. 잘못된 스키마는 HTTP 422이며 저장 전 종료 |
| 도구 | 등록된 지출·예산·요약·상호 순위·월 비교만 실행 | 미등록 도구나 명시적 요청 없는 AI 쓰기 거부. CLI 전용 CSV 파일 호출은 웹에서 차단 |

브라우저의 허용·거부 오리진과 잘못된 거래·대화가 장부에 남지 않는 동작은 `tests/test_web.py`에서 검증한다.

## 요약 주입과 도구 호출

`summary(store, month)`를 개요 API, 채팅의 summarize 도구, 시스템 프롬프트가 공유한다. 예를 들어 4,500원짜리 거래 한 건이 있는 월에 “이번 달 지출 요약”을 보내면 첫 시스템 메시지에 해당 월의 count=1, total=4500이 들어간다. 모델이 summarize를 요청하면 서버가 다시 계산해 tool_result를 전달한다. [모의 요청에서 관찰한 값](evidence/claude-mock.json)

| 방식 | 장점 | 비용·한계 |
|---|---|---|
| 선택 월 요약을 시스템 메시지에 포함 | 사용자가 “이번 달”이라고만 해도 화면과 같은 월·금액을 참조 | 매 AI 요청마다 조회와 입력 토큰이 필요하다. 읽은 시점의 값이다. |
| 필요한 도구를 호출해 계산 | 다른 월 조회, 비교, 예산 변경을 검증된 함수로 실행 | 도구 결과를 자연어로 설명하는 두 번째 모델 호출이 추가될 수 있다. |

지출 월은 사용자가 입력한 거래일을 기준으로 한다. 대화 저장 시각은 UTC이며 지출 월 산출에는 쓰지 않는다. 결산일을 변경하려면 web_api.py의 expense_row에서 month 키를 만드는 규칙을 바꾸고 이미 저장한 거래의 month도 다시 계산한다. monthly와 summary의 집계, CLI tools.py의 summarize, top_merchants, 월 경계 테스트도 함께 조정한다. 월말·다음 달 첫날 두 거래가 서로 올바른 기간에 포함되는지 검증한다.

---

## 이전 CLI 버전 안내


**Python 3.10+ / VS Code / SQLite / Anthropic Messages Tool Use**

## 빠른 실행

1. `python -m pip install -r requirements.txt`
2. `.env.example`을 복사해 `.env`를 생성하고 **본인의 키**를 로컬에서만 입력하세요.
3. `python backend.py` — 로컬 서버 `127.0.0.1:8765` (선택)
4. **다른 터미널**에서 `python main.py`
5. `AI: 2026-11월 소비 요약해줘`를 입력합니다.

`.env` 구성:

```dotenv
ANTHROPIC_API_KEY=YOUR_API_KEY
ANTHROPIC_BASE_URL=https://copa.codyssey.kr
ANTHROPIC_MODEL=claude-sonnet-4
```

Anthropic SDK가 `/v1/messages`를 추가하므로 base URL에 `/v1`을 덧붙이지 마세요. 코디세이 사용 설명서에서 **Anthropic** 방식으로 발급한 키를 사용합니다. OpenAI 호환 키/엔드포인트를 사용하지 않습니다.

## 아키텍처

- `main.py`: 로컬 대화형 CLI
- `backend.py`: 루프백 바인딩 HTTP API. `GET /health`, `POST /api/chat` with JSON `{"message":"AI: ..."}`
- `config.py`: `.env`에서 Anthropic 키/URL/모델을 로드하며 기존 환경변수를 우선합니다.
- `agent.py`: Claude `tool_use` → 검증 → 허용된 Python 도구 실행 → `tool_result` → 한국어 최종 응답
- `tools.py`: 지출 추가, 예산 설정, 월별 요약, 상호별 순위, 월간 비교, CSV import (CSV는 비AI 기본 명령에서만 허용)
- `storage.py`: SQLite 데이터와 실행 감사 기록
- `tests/`: 실제 API 키 없는 단위·백엔드·모의 Tool Use 테스트
- `sample_data/`: 가상의 예시 데이터 (개인 금융 기록 아님)

## 명령 예시

```text
추가 2026-11-20 스타벅스 4800
예산 2026-11 카페 10000
요약 2026-11
AI: 2026-11월 카페 예산이 얼마나 남았는지 요약해줘
AI: 2026-11-20 스타벅스에서 4800원 쓴 내역을 등록해줘
```

**주의**: 실제 코디세이 API에 직접 연결한 테스트는 사용자의 컴퓨터에서 수행해야 합니다. 이 프로젝트의 CI/오프라인 테스트에서는 API 키를 저장하거나 호출하지 않습니다. 이미 일반 대화 테스트가 성공했더라도 Tool Use 지원 여부는 별도 검증 대상입니다.

## 오프라인 테스트

`python -m unittest discover -s tests -v`

## 개인 정보 및 안전

- `.env`, `*.db`는 `.gitignore`로 제외합니다. API 키를 코드와 GitHub에 올리지 마세요.
- 백엔드는 `127.0.0.1`에서만 실행합니다. 외부 인터넷에 공개하지 마세요.
- AI가 임의 코드를 실행하거나 은행 계좌에 접속할 수 없습니다.
- 금액/날짜가 불명확하면 확인 질문을 하도록 설계했습니다. 도구 실행은 허용 목록으로 제한합니다.
- `AI:`에서 지출 추가/예산 변경은 사용자가 명시적으로 요청해야 합니다.
- 현재 버전은 거래내역을 분석하는 로컬 프로젝트이며 실제 은행 연동이 아닙니다.

## 자동 통합 테스트 및 JSON 결과 저장

테스트용 가상의 소비 데이터만 사용하며, 실제 `spendwise.db`는 열지 않습니다.
매번 별도의 임시 SQLite DB를 생성해 **거래 등록 → 재조회 → 예산 설정 → 잔액 분석 → 잘못된 날짜·금액 거부** 순서로 실행합니다.

**1. 오프라인 모의 Claude 테스트 (기본값, API 호출 없음):**

```powershell
python test_runner.py
```

**2. 실제 코디세이 Claude Tool Use 통합 테스트 (API 사용 요금/할당량 발생 가능):**

```powershell
python test_runner.py --live
```

두 명령 모두 `results/test_results.json`을 작성합니다. `--live` 실행 전 `.env`에 `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`을 설정하세요. 인증정보가 없다면 실사용 테스트는 `SKIP`으로 기록됩니다. **mock의 PASS는 실제 Claude 호출 성공이 아닙니다.** 실제 API 사용 결과는 `mode: live`, `live_api_called: true`와 테스트별 결과를 함께 확인해야 합니다.

실제 호출 결과를 모의 결과와 별도로 보관하려면 아래처럼 실행할 수 있습니다.

```powershell
python test_runner.py --live --output results/live_test_results.json
```

**3. 단위 테스트:**

```powershell
python -m unittest discover -s tests -v
```

JSON에는 테스트용 인공 거래 정보, 호출된 도구, 허용된 결과 필드와 검증 여부만 저장합니다. API 키, 사용자 실제 거래, LLM의 자유형 원문 응답은 저장하지 않습니다. `.gitignore`는 `results/*.json`을 Git 업로드에서 제외하므로 실제 테스트 결과를 공개 저장소에 무심코 올리지 않도록 합니다. 제출 증빙으로 공유하려면 내용 확인·비식별화 후 별도 업로드하세요.

> 주의: 실제 Claude가 잘못된 날짜·금액을 **도구 호출 없이 확인 질문으로 돌려보내는 경우도 PASS**로 인정합니다. 실사용 API가 Tool Use를 지원하지 않거나 다른 도구를 선택하면 FAIL로 기록합니다.

## 실제 Claude 통합 테스트 증빙 (2026-11-21)

사용자 Windows에서 실행한 6개 live 시나리오가 전부 PASS였습니다. 실제 입력·도구·검증항목은 [`results/live_test_results.json`](results/live_test_results.json), 평가 방법과 한계는 [`REPORT.md`](REPORT.md)를 참고하세요. API 키는 저장소에 포함하지 않습니다.
