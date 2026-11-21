# 8번 과제 보고서: SpendWise Agent (가계부·소비 분석 비서)

이 문서는 기존 CLI 버전의 보고서다. 웹 재개발 기능과 검증 기록은 [최신 평가표](ASSESSMENT.md)와 [웹 실행 안내](DEPLOY.md)에서 확인할 수 있다.

## 최종 실제 Claude API 통합 테스트 (2026-11-21)

사용자의 Windows 환경에서 실행한 `python test_runner.py --live --output results/live_test_results.json` 결과를 근거로 기록했다.

- **실행 모드:** `live`, **API 호출 기록:** `live_api_called: true`
- **검증 결과:** 총 6개, **PASS 6 / FAIL 0 / SKIP 0**
- **데이터:** 실제 금융거래가 아닌 합성 테스트 거래
- **DB:** 독립적인 임시 SQLite 데이터베이스(종료 후 제거)

| ID | 검증 항목 | 기대/실제 도구 | 판정 |
|---|---|---|---|
| TC-001 | 2026-11-21 스타벅스 4,500원 등록·DB 저장 | `add_expense` / `add_expense` | PASS |
| TC-002 | 11월 4,500원·1건 재조회 | `summarize` / `summarize` | PASS |
| TC-003 | 11월 카페 예산 50,000원 저장 | `set_budget` / `set_budget` | PASS |
| TC-004 | 예산 잔액 45,500원 확인 | `summarize` / `summarize` | PASS |
| TC-005 | 존재하지 않는 날짜 `2026-02-30` 입력 거부, DB 불변 | 도구 호출 없음 | PASS |
| TC-006 | 음수 금액 `-100원` 입력 거부, DB 불변 | 도구 호출 없음 | PASS |

**증빙:** [`results/live_test_results.json`](results/live_test_results.json) 파일은 각 실제 입력, 예상·실행 도구, 검증 플래그 및 판정을 포함한다. 키는 기록하지 않았다.

**해석 범위:** `live_api_called: true` 및 도구명은 사용자의 로컬에서 실행된 테스트 러너가 기록한 값이다. 여기서는 사용자의 비밀키로 네트워크 테스트를 독립 재현하지 않았다. 모든 요청 유형과 장기 안정성을 검증한 것은 아니다.

---


## 1. 목적과 분석 질문

- **Q1.** 일상적인 한국어 소비 기록을 어떤 도구로 연결해 저장·분류할 수 있는가?
- **Q2.** 월별 지출 및 예산 대비 잔여액을 어떻게 확인하고 비교할 수 있는가?
- **Q3.** 입력 오류, 중복 CSV, 미인식 요청에 Agent가 어떻게 안전하게 대응하는가?

## 2. 기능 및 Agent 구조

`사용자 입력 → Agent._route() (또는 AI:_llm_route()) → 허용 도구 검증 → tools.py → SQLite → 실행 결과 및 agent_events 저장`

- 지출 등록, 상호명 키워드 기반 카테고리 추정, 예산 등록, 월별 요약, 가맹점 상위 지출, 전월/당월 비교, CSV 중복 방지.
- Agent가 사용할 수 있는 도구는 코드에 명시한 `TOOLS`에 한정된다. 불확실한 명령은 임의 실행하지 않고 오류 메시지로 처리한다.
- 초기 버전은 OpenAI 호출을 사용했으나, **현재 제출 버전은 Codyssey Claude Anthropic Tool Use를 사용**한다. 실제 연동 결과는 상단 '최종 실제 Claude API 통합 테스트'를 참조한다.
- 거래 데이터는 가상 예시이며 실제 소비 수준에 관한 분석·추론이 아니다.

## 3. 데이터 및 재현성

- `sample_data/example_transactions.csv`: 2026년 10~11월에 걸친 11건의 가상 거래.
- 필수 CSV 필드 `date,merchant,amount`; 원단위 정수만 입력.
- 실행: `python main.py`; 테스트: `python -m unittest discover -s tests -v`.
- SQLite `transactions`, `budgets`, `agent_events` 테이블에 저장. 실제 DB 파일과 API 키는 `.gitignore`로 제외.

## 4. AI 활용 및 검증

### 실제 프로젝트 생성 과정에서 확인한 요청
- **사용자 질문 원문:** “AI 가계부, 소비 분석 비서로 해보자”
- **작업 방향:** 지출 등록·분류·예산·소비분석 도구를 갖춘 VS Code Python Agent 및 테스트 프로젝트를 구축.
- **검증 방식:** 가상 CSV로 입력-분류-요약-비교 도구를 실행하며 unittest를 통과하는지 검사. 실제 오프라인 테스트 결과는 아래에 명시.

### 검증 원칙
- AI가 추정한 분류(`스타벅스 → 카페` 등)는 상호명 규칙이며 확정된 카드 업종코드와 다를 수 있다.
- 월별 통계는 SQLite 원본 레코드를 SQL로 합산하여 확인한다. 예산 잔액도 실제 저장 금액과 비교한다.
- 미확인 외부 API 동작을 성공이라고 작성하지 않는다. 실제 AI 질의응답·테스트 로그를 과장하거나 창작하지 않는다.

## 5. 위험·제약과 개선 방향

- 금융계좌 직접 연동·OCR·실시간 은행 API는 구현하지 않았다. 사용자 제공 CSV만 취급한다.
- CSV 중복 방지는 동일 절대경로+행번호+내용 조합 기준으로 작동한다.
- 자연어 해석은 오프라인에서는 제한된 문법만 지원하며, LLM 모드도 외부 API 키 없이는 실행할 수 없다.
- 실제 사용자는 원본 거래정보에서 카드번호, 주민번호, 계좌번호 등 민감 식별자를 제거해야 한다.
- 향후 보완: 카테고리 수정 기능, 지출 삭제 전 확인 기능, 예산 초과 알림, 다중 모델 비교.

## 6. 실행 검증 결과 (2026-11-21)

아래 명령으로 Python 표준 라이브러리 기반 오프라인 모드를 검증했다.

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```

- **9개 테스트 실행, 9개 통과(OK).**
- 검사 항목: 분류, 지출·요약, 예산 잔액, 한국어 지출 입력, 음수 금액 차단, 모르는 명령 기록, 잘못된 월 처리, CSV 재가져오기 중복 방지, 월 비교.
- 외부 LLM API는 별도 키·네트워크가 필요하므로 **미검증**이며 성공으로 표기하지 않는다.

## 백엔드 기반 LLM 연동 및 검증 (2026-11-21 추가)

### 설계와 인증정보 관리
- 사용자는 CLI 또는 `127.0.0.1:8765`의 로컬 Python HTTP API로 자연어 요청을 전달한다.
- 로컬 백엔드는 `.env` 또는 환경변수에서만 `OPENAI_API_KEY`를 읽는다. 키를 GitHub 소스·API 응답에 넣지 않는다.
- `AI:` 요청은 OpenAI Function Calling으로 허용된 도구 중 하나를 선택하고, Python 코드가 실제로 도구를 실행한다. 비AI 요청은 규칙 기반 파서로 처리한다.
- SQLite는 거래, 예산, 도구 실행 기록을 로컬에 영속 보관한다. `*.db`, `.env`는 Git 관리에서 제외한다.
- 현재 HTTP 서버는 로컬 전용이다. 외부 공개 서비스로 사용하려면 인증·HTTPS·별도 보안 설계가 추가로 필요하다.

### LLM 도구 선택과 안전성
도구는 `add_expense`, `set_budget`, `summarize`, `top_merchants`, `compare_months`로 제한했다. 불명확한 입력은 도구를 강제 호출하지 않고 오류를 반환한다. CSV 불러오기, 임의 명령 실행 및 삭제는 LLM 도구 목록에서 제외했다.

### 테스트 로그 (실제 오프라인 실행)
- 실행 명령: `python -m unittest discover -s tests -v`
- 결과: **14 tests, OK** (기존 9개 + 로컬 HTTP 백엔드 5개).
- 검증 예: 정상 거래 등록 후 요약 금액 확인, 잘못된 JSON 요청 거부, 누락된 `message` 거부, 설정되지 않은 API 키 사용 오류, 상태 응답에서 비밀 키가 노출되지 않는지 확인.
- **당시 검증되지 않았던 부분:** 초기 OpenAI 버전의 외부 호출. 현재 Claude 전환 버전의 실제 호출은 상단의 사용자 제공 live 테스트 결과로 별도 확인했으며, 초기 OpenAI 테스트 결과를 Claude 결과로 대체하거나 혼동하지 않는다.

### AI 사용·검증 기록의 한계
본 프로젝트의 LLM 연동 구조와 코드 변경은 AI 보조로 작성되었으며, 실행 가능한 테스트를 통해 백엔드 동작을 검증했다. 과거 프롬프트·답변 전문이나 실제 API 테스트 결과를 가공하거나 만들어내지 않았다. 평가에서 AI 활용 원본 전문을 요구한다면 실제 ChatGPT 대화 내역을 별도로 첨부한다.

---

## 2026-11-21 Claude Tool Use 전환 검증 기록

### 변경 근거
- 사용자가 코디세이에서 **Anthropic 호환** 키를 발급받은 화면을 제공함.
- 코디세이 문서 예제는 `https://copa.codyssey.kr/v1/messages`, `x-api-key`, `anthropic-version: 2023-06-01`, `model: claude-sonnet-4`, `max_tokens`를 명시함.
- 사용자가 별도의 `test_claude_api.py`로 **Claude 일반 대화 응답 수신 성공**을 보고함. 이는 도구 사용 가능성까지 보장하지 않음.

### 구현
1. `config.py`: `.env`에서 `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`을 읽음.
2. `agent.py`: `anthropic.Anthropic(...).messages.create` 및 `input_schema` 도구 정의로 교체.
3. 허용 도구는 `add_expense`, `set_budget`, `summarize`, `top_merchants`, `compare_months` 다섯 가지. CSV 경로를 LLM에 맡기지 않음.
4. Claude의 `tool_use` 블록을 파싱해 필수 인자를 검증한 후 실제 Python 도구 1개를 실행하고, `tool_result`를 Claude에게 다시 전달하여 최종 문장을 생성함.
5. 모호한 요청은 DB를 변경하지 않고 확인 질문을 반환하며, 쓰기 요청은 지출 등록/예산 변경 의도가 명시되어야 실행함.
6. 후속 LLM 응답 생성 실패 시에는 실제 SQLite 실행 결과를 보존하고 성공한 작업을 실패로 오인하지 않게 처리함.
7. API 공급자가 보낸 오류에 키 일부가 들어갈 수 있으므로 원문을 그대로 사용자·로그에 노출하지 않고 오류 유형만 출력함.

### 오프라인 검증 결과

`python -m unittest discover -s tests -v` → **21개 테스트 통과(21/21)**.

신규 모의 Claude 테스트 7개는 다음을 검증한다.
- 도구 선택 → SQLite 실행 → `tool_result` → 응답 생성
- 모호한 요청의 무변경 응답
- 허가되지 않은 도구 호출 거부
- 요청하지 않은 지출 등록 거부
- 도구 실행 후 후속 응답 실패의 일관성 유지
- 하나의 요청에서 복수 Tool Use 거부
- API 오류 문자열에 포함된 인증 정보 비노출

**당시 검증 한계(개발 초기 단계):** 이 실행 환경에서는 외부 API 키가 없어 E2E 테스트를 수행하지 못했다. **이후 사용자 Windows PC에서 실제 Tool Use 6건 테스트를 실행했고, 모두 PASS가 기록되었다**(상단 실제 Claude API 통합 테스트 참조).

### API 사용 대화 기록(발췌, 허구 생성 없음)
- 사용자: “코디세이에서 발급받은 키 맞아”
- 사용자 제공 화면: 키 관리의 호환 방식은 “Anthropic”이며 상태는 “활성”.
- 사용자 제공 문서: Anthropic Messages `https://copa.codyssey.kr/v1/messages`, 모델 `claude-sonnet-4`.
- 사용자: `python test_claude_api.py` 실행 후 Claude의 자기소개 문장 출력.
- 사용자: “오케이 해보자” → 본 전환 구현을 진행함.

이 기록은 해당 대화의 발췌이며, 실제 Tool Use 라이브 응답을 만들어 기재하지 않았다.

## 자동 JSON 통합 테스트 증빙 (추가 기능)

- 테스트 스크립트: `test_runner.py`
- 모의 기록 경로: `results/test_results.json` (재실행 시 갱신, Git에서 제외). 별도 실사용 증빙은 `results/live_test_results.json`에 보관하고 Git 추적 대상으로 포함했다.
- 모의 테스트: `python test_runner.py` — Claude SDK를 모의 응답으로 대체. 실제 외부 LLM 호출은 하지 않음.
- 실사용 테스트: `python test_runner.py --live` — 사용자의 로컬 `.env`에 있는 Codyssey Anthropic 키를 이용하여 실제 Claude Tool Use를 호출. 요금 및 API 사용량이 발생할 수 있음.
- 테스트 원칙: 실제 가계부 DB를 변경하지 않도록 임시 SQLite에서 가상의 스타벅스 4,500원 거래와 카페 예산 50,000원만 사용.
- 자동 검증 항목: 등록 결과 및 DB 행 수, 재조회 총액 4,500원, 카테고리별 집계, 예산 DB 저장, 카페 잔액 45,500원, 잘못된 날짜/금액에 따른 신규 거래 없음.
- 결과의 `mode`/`live_api_called`/`status`를 통해 **모의 PASS와 실제 Claude API PASS를 구분**함.
- 증빙 한계: 모의 JSON은 실제 API 사용 증빙이 아니다. 이후 사용자 PC에서 실행된 별도 `live_test_results.json`을 첨부했으며, API 호출에 대한 독립적인 네트워크 재검증은 수행하지 않았다. AI 대화 질문·응답 원문 전체를 생성 또는 위조하지 않는다.
