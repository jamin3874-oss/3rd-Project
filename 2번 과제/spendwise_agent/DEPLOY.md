# 채점용 웹 주소 만들기

이 가계부는 평가용 단일 장부다. React 화면과 FastAPI가 같은 서비스에서 실행되므로 한 번 배포하면 첫 화면과 API 문서 주소가 함께 생긴다. 공개용으로는 예시 거래를 사용한다.

## 내 컴퓨터에서 먼저 열기

프로젝트 폴더에서 Python 3.13 이상을 사용한다. PowerShell에서 다음을 실행한다. 첫 줄은 패키지를 내려받는다.

```powershell
python -m pip install -r requirements-web.txt
$env:SPENDWISE_STORE="memory"
$env:SPENDWISE_PASSWORD=Read-Host "연습용 가계부 비밀번호"
python -m uvicorn web_api:app --host 127.0.0.1 --port 8000
```

브라우저에서 `http://localhost:8000`을 열고 방금 정한 가계부 비밀번호를 입력한다. 웹 화면은 기기별로 30일간 로그인을 유지한다. Swagger에서 보호된 API를 직접 호출하려면 `/docs`의 Authorize에 사용자명 `spendwise`와 같은 비밀번호를 입력한다. 이 연습용 장부는 프로그램 종료 시 비워진다. React와 Swagger 배포 파일은 프로젝트에 포함되어 있다. JSX 수정 후 `npx esbuild frontend/app.jsx --target=es2020 --outfile=public/app.js`로 다시 만든다.

## 실제 배포에 필요한 선택

### 무료 Cloud Shell 연동 확인

프로젝트의 Cloud Shell에서 이 과제 폴더로 이동한 뒤 아래 명령을 실행한다. 활성 Google 계정에 해당 장부의 읽기·쓰기 권한이 필요하다. 실서비스 검증은 기존 합성 거래 한 건(과제 예시 카페)을 5,300원으로 수정하고 월 요약 대화 한 건을 기록한다. 같은 대화 ID를 사용하므로 재실행해도 해당 대화 건수는 늘어나지 않는다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-web.txt
export GOOGLE_CLOUD_PROJECT=spendwise-f6d6d
python verify_firestore.py
python -m unittest discover -s tests -v
```

성공하면 `evidence/live-firestore-api.json`에 실제 API 요청을 통해 관찰한 금액·합계와 대화 조회 결과가 기록된다. 화면을 열려면 아래 명령에서 미리보기 전용 비밀번호를 입력하고 Cloud Shell의 웹 미리보기에서 8080 포트를 선택한다. 사용자명은 `spendwise`다. 이 주소는 해당 Google 계정의 임시 미리보기용이다.

```bash
read -rsp 'Preview password: ' SPENDWISE_PASSWORD; echo
export SPENDWISE_PASSWORD
python -m uvicorn web_api:app --host 0.0.0.0 --port 8080
```

### 공개 채점 주소 배포

실제 [Render 서비스](https://spendwise-f6d6d.onrender.com/)는 Free 인스턴스에 배포했다. Web Service에 공개 Git 저장소와 브랜치 `spendwise-web-assessment`를 지정한다. Render의 Root Directory 입력란은 한글을 거부하므로 비워 두고 Python 3 런타임에서 다음 명령을 사용한다.

| 설정 | 실제 사용값 |
|---|---|
| Build Command | `python -m pip install -r '2번 과제/spendwise_agent/requirements-web.txt'` |
| Start Command | `cd '2번 과제/spendwise_agent' && exec python -m uvicorn web_api:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

Environment에 `GOOGLE_CLOUD_PROJECT=spendwise-f6d6d`, `SPENDWISE_PASSWORD`(별도의 채점용 비밀번호), `GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/firestore.json`을 설정한다. 과제 프로젝트에서 Cloud Datastore User 권한을 받은 전용 서비스 계정의 JSON은 Render의 Secret File `firestore.json`에 저장한다. 키 교체는 새 키를 비밀 파일에 적용하고 배포 후 월 조회를 확인한 다음 Google IAM에서 이전 키를 폐기하는 순서다.

Render 무료 인스턴스는 유휴 후 재시작할 수 있다. 채점 직전에 첫 화면과 월별 조회를 열어 응답 시간을 확인한다. [무료 인스턴스 안내](https://render.com/docs/free)

**Google Cloud Run**을 사용하는 경우의 절차는 다음과 같다.

Google Cloud 프로젝트는 이 과제의 서버, 저장소, 사용료를 한곳에서 관리하는 작업 공간이다. 프로젝트 ID는 그 공간의 고유 이름이다. 과제에서 제공한 프로젝트가 있으면 먼저 사용한다. 아래 과정에는 서비스 사용 권한과 요금 발생 가능성이 있으므로 계정 소유자가 승인한 후 진행한다.

1. 프로젝트에서 Firestore를 Native 모드로 만들고 기본 데이터베이스를 선택한다. Cloud Run, Cloud Build, Artifact Registry, Secret Manager API를 사용 설정한다. 소스 빌드 계정에는 Cloud Run Builder, 배포 담당자에게는 소스 배포 및 실행 서비스 계정 사용 권한이 필요하다.
2. 실행 전용 서비스 계정을 만들고 프로젝트에서 Cloud Datastore User를 부여한다. Firestore 서버 SDK는 이 계정으로 인증한다. 비밀키 JSON 파일은 필요하지 않다.
3. Secret Manager에 가계부 로그인 비밀번호를 `spendwise-password`로 저장한다. 채점용 로그인은 개인 계정 비밀번호와 별도로 정한다. Claude 사용을 승인한 경우에만 제공받은 API 키를 `spendwise-claude` 비밀에 저장한다. 각 비밀에 대해 실행 계정에 Secret Manager Secret Accessor를 부여한다.
4. Google Cloud CLI에서 로그인한 뒤 이 폴더에서 아래 PowerShell 명령을 실행한다. 실행 계정 주소와 프로젝트 ID는 본인의 값을 입력한다. 서울 리전은 이 안내에서 선택한 예시다.

```powershell
$projectId=Read-Host "프로젝트 ID"
$serviceAccount=Read-Host "실행 서비스 계정 이메일"
gcloud run deploy spendwise --source . --project $projectId --region asia-northeast3 --service-account $serviceAccount --allow-unauthenticated --set-env-vars "GOOGLE_CLOUD_PROJECT=$projectId" --set-secrets "SPENDWISE_PASSWORD=spendwise-password:1" --min-instances 0 --max-instances 2 --timeout 180
```

5. Claude 사용 시 Cloud Run의 새 버전 설정에서 `ANTHROPIC_API_KEY`에 위 비밀 버전을 연결한다. `ANTHROPIC_MODEL`은 계정이 사용할 수 있는 모델 ID로 설정하고, 학교 제공 호환 서버를 쓰는 경우 해당 기관이 안내한 `ANTHROPIC_BASE_URL`을 설정한다. 브라우저 환경변수에는 키를 넣지 않는다. 운영 환경에서는 `SPENDWISE_STORE`를 비워 Firestore를 사용한다.
6. 반환된 HTTPS 서비스 주소가 프론트 주소다. 같은 주소 뒤에 `/docs`, `/api/data/summary?month=2026-11`를 붙이면 API 문서와 월별 요약이 열린다. 외부 브라우저에서 로그인하고 예시 거래 등록 → 금액 수정 → 목록 갱신 → 대화 전송 → 재접속 후 대화 복원을 확인한다. Firestore 콘솔에서 같은 거래 ID와 대화 ID를 대조한다. 실제 URL, 시각, 개인정보를 가린 화면을 평가표에 추가한다.

## 콜드스타트

최소 인스턴스가 0이면 한동안 사용하지 않은 후 첫 요청에서 컨테이너 시작과 Firestore 클라이언트 초기화 시간이 추가된다. 화면에는 조회 중 표시가 나오며 실패 시 새로고침할 수 있다. Firestore 클라이언트는 프로세스에서 재사용한다. 거래 및 대화에는 오래된 합계가 표시되지 않도록 브라우저 조회 캐시를 사용하지 않는다. 채점 직전 서비스 주소와 월별 조회를 한 번 열어 두면 첫 접근을 예행할 수 있다. 최소 인스턴스를 1로 유지하면 대기 시간이 줄지만 유휴 시간 비용이 발생할 수 있다. 실제 효과는 유휴 후 첫 조회 시간과 바로 다음 조회 시간을 같은 조건에서 기록해 비교한다.

[Cloud Run 소스 배포](https://cloud.google.com/run/docs/deploying-source-code) · [비밀 연결](https://cloud.google.com/run/docs/configuring/services/secrets) · [Firestore 에뮬레이터](https://firebase.google.com/docs/emulator-suite/connect_firestore)

## 테스트

`python -m unittest discover -s tests -v`로 실행한다. Firestore 에뮬레이터의 통합 검증은 Firebase CLI와 해당 버전이 요구하는 Java를 설치한 후 프로젝트 폴더에서 아래 명령으로 실행한다. 테스트용 프로젝트 안에서 자체 생성 문서의 저장, 새 클라이언트에서의 조회, 중복 대화 시 전체 쓰기 취소, 금액 갱신을 검사한다.

```powershell
firebase emulators:exec --only firestore --project demo-spendwise "python -m unittest discover -s tests -p test_firestore_emulator.py -v"
```
