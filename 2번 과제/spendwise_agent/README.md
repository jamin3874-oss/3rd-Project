# SpendWise Agent — 코디세이 Claude 백엔드 버전

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
