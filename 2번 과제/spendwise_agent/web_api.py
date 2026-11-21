import hmac
import json
import os
import re
import secrets
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from agent import Agent
from tools import CATEGORIES, classify, valid_month
from web_store import get_store

app = FastAPI(title="SpendWise 가계부", version="2.0", docs_url=None, redoc_url=None)


def configure_origins(application, setting):
    origins = [entry.strip() for entry in setting.split(",") if entry.strip()]
    for origin in origins:
        address = urlsplit(origin)
        if (address.scheme not in {"http", "https"} or not address.hostname
                or address.username is not None or "*" in origin
                or address.path or address.query or address.fragment):
            raise ValueError("허용 주소에는 정확한 HTTP(S) 오리진만 지정하세요.")
    if origins:
        application.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                                   allow_methods=["GET", "POST", "PUT"],
                                   allow_headers=["Authorization", "Content-Type"])


configure_origins(app, os.getenv("SPENDWISE_ALLOWED_ORIGINS", ""))
security = HTTPBasic(auto_error=False)
assets = Path(__file__).parent / "public"
Month = Annotated[str, StringConstraints(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$"), AfterValidator(valid_month)]
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


SESSION_COOKIE = "spendwise_session"
SESSION_SECONDS = 30 * 24 * 60 * 60


def server_password():
    password = os.getenv("SPENDWISE_PASSWORD")
    if not password:
        raise HTTPException(503, "서버의 가계부 비밀번호 설정이 필요합니다.")
    return password


def signature(payload, password):
    return hmac.digest(password.encode(), ("SpendWise session v1:" + payload).encode(), "sha256").hex()


def valid_session(request, password):
    token = request.cookies.get(SESSION_COOKIE, "")
    if not re.fullmatch(r"[0-9]{10,11}\.[0-9a-f]{32}\.[0-9a-f]{64}", token):
        return False
    payload, mac = token.rsplit(".", 1)
    return (int(payload.split(".")[0]) > time.time()
            and secrets.compare_digest(mac, signature(payload, password)))


def authorize(request: Request, response: Response,
              credentials: Annotated[HTTPBasicCredentials | None, Depends(security)]):
    password = server_password()
    response.headers["Cache-Control"] = "no-store"
    if valid_session(request, password):
        return
    if credentials and credentials.username == "spendwise" and secrets.compare_digest(
            credentials.password.encode(), password.encode()):
        return
    headers = {} if request.headers.get("X-SpendWise-Web") else {"WWW-Authenticate": 'Basic realm="SpendWise"'}
    raise HTTPException(401, "로그인이 필요합니다.", headers=headers)


protected = [Depends(authorize)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Expense(Input):
    txn_date: date
    merchant: Label
    amount: int = Field(gt=0, le=10**12)


class Record(Expense):
    id: str
    category: str


class Summary(BaseModel):
    month: Month
    total: int
    count: int
    by_category: dict[str, int]
    budget: dict[str, int]
    overall_remaining: int | None
    category_remaining: dict[str, int]


class Chat(Input):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    month: Month
    request_id: UUID = Field(default_factory=uuid4)


class Turn(BaseModel):
    id: UUID
    created_at: datetime
    month: Month
    message: str
    reply: str
    tool: str | None


def expense_row(expense, key):
    return dict(**expense.model_dump(mode="json"), id=key, month=expense.txn_date.strftime("%Y-%m"),
                kind="expense", category=classify(expense.merchant))


def monthly(store, month):
    valid_month(month)
    rows = store.rows("data", month)
    return [row for row in rows if row["kind"] == "expense"], {
        row["category"]: row["amount"] for row in rows if row["kind"] == "budget"}


def summary(store, month):
    expenses, budgets = monthly(store, month)
    categories = Counter()
    for row in expenses:
        categories[row["category"]] += row["amount"]
    total = sum(categories.values())
    return Summary(month=month, total=total, count=len(expenses), by_category=dict(categories),
                   budget=budgets, overall_remaining=budgets["전체"] - total if "전체" in budgets else None,
                   category_remaining={key: value - categories[key] for key, value in budgets.items() if key != "전체"})


class PendingTurn:
    def __init__(self, store):
        self.store = store
        self.changes = []
        self.audit = None

    def log(self, command, tool, args, result):
        self.audit = {"tool": tool, "args": args, "result": result}

    def add(self, txn_date, merchant, amount):
        row = expense_row(Expense(txn_date=txn_date, merchant=merchant, amount=amount), str(uuid4()))
        self.changes.append((row["id"], row))
        return Record.model_validate(row, extra="ignore").model_dump(mode="json")

    def budget(self, month, category, amount):
        valid_month(month)
        amount = int(amount)
        if category not in (*CATEGORIES, "전체") or not 0 <= amount <= 10**12:
            raise ValueError("예산 범위와 분류를 확인하세요.")
        key = f"budget-{month}-{category}"
        row = dict(id=key, month=month, kind="budget", category=category, amount=amount)
        self.changes.append((key, row))
        return row

    def top(self, month):
        expenses, _ = monthly(self.store, month)
        totals = Counter()
        for row in expenses:
            totals[row["merchant"]] += row["amount"]
        return dict(totals.most_common(5))

    def compare(self, left, right):
        first = summary(self.store, left).total
        last = summary(self.store, right).total
        return {"from_total": first, "to_total": last, "difference": last - first}


handlers = {"add_expense": PendingTurn.add, "set_budget": PendingTurn.budget,
            "summarize": lambda session, month: summary(session.store, month).model_dump(),
            "top_merchants": PendingTurn.top, "compare_months": PendingTurn.compare}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/docs", include_in_schema=False)
def docs():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="SpendWise API",
                               swagger_js_url="/assets/vendor/swagger-ui-bundle.js",
                               swagger_css_url="/assets/vendor/swagger-ui.css",
                               swagger_favicon_url="data:,",
                               swagger_ui_parameters={"validatorUrl": None})


@app.get("/api/data/summary", dependencies=protected, response_model=Summary)
def get_summary(month: Month, store=Depends(get_store)):
    return summary(store, month)


@app.get("/api/data", dependencies=protected, response_model=list[Record])
def list_data(month: Month, store=Depends(get_store)):
    rows, _ = monthly(store, month)
    return [Record.model_validate(row, extra="ignore") for row in sorted(
        rows, key=lambda row: (row["txn_date"], row["id"]), reverse=True)]


@app.post("/api/data", dependencies=protected, response_model=Record, status_code=201)
def add_data(item: Expense, store=Depends(get_store)):
    row = expense_row(item, str(uuid4()))
    store.save([(row["id"], row)])
    return Record.model_validate(row, extra="ignore")


@app.put("/api/data/{key}", dependencies=protected, response_model=Record)
def update_data(key: UUID, item: Expense, store=Depends(get_store)):
    if not store.get("data", str(key)):
        raise HTTPException(404, "거래를 찾을 수 없습니다.")
    row = expense_row(item, str(key))
    store.save([(str(key), row)])
    return Record.model_validate(row, extra="ignore")


@app.get("/api/conversations", dependencies=protected, response_model=list[Turn])
def conversations(limit: int = Query(50, ge=1, le=100), store=Depends(get_store)):
    return store.rows("conversations", recent=limit)


def replay(old, chat):
    if old["message"] != chat.message or old["month"] != chat.month:
        raise HTTPException(409, "이미 다른 요청에서 사용한 요청 ID입니다.")
    return old


@app.post("/api/chat", dependencies=protected, response_model=Turn)
def chat(request: Chat, store=Depends(get_store)):
    key = str(request.request_id)
    previous = store.get("conversations", key)
    if previous:
        return replay(previous, request)
    session = PendingTurn(store)
    context = "\n화면에서 선택한 월의 실제 요약 JSON\n" + summary(store, request.month).model_dump_json()
    history = []
    for turn in reversed(store.rows("conversations", recent=6)):
        history.extend([dict(role="user", content=turn["message"]), dict(role="assistant", content=turn["reply"])])
    agent = Agent(session, handlers=handlers, context=context, history=history)
    result = agent.execute(request.message)
    if "error" in result:
        if request.message.startswith("AI:"):
            raise HTTPException(502, "AI 요청을 처리하지 못했습니다. 서버 설정과 요청 내용을 확인하세요.")
        raise HTTPException(400, "명령을 확인하세요. 예시: 요약 2026-11")
    payload = result.get("result", {})
    reply = result.get("assistant_message") or result.get("message") or result.get("help")
    if not reply:
        tool = result["tool"]
        if tool == "summarize":
            reply = f'{payload["month"]} 지출은 {payload["count"]}건, 총 {payload["total"]:,}원입니다.'
        elif tool == "set_budget":
            reply = f'{payload["month"]} {payload["category"]} 예산을 {payload["amount"]:,}원으로 설정했습니다.'
        elif tool == "add_expense":
            reply = f'{payload["merchant"]} 지출 {payload["amount"]:,}원을 기록했습니다.'
        else:
            reply = json.dumps(payload, ensure_ascii=False)
    turn = dict(id=key, month=request.month, created_at=datetime.now(timezone.utc),
                message=request.message, reply=reply, tool=result.get("tool"),
                schema_version=1, audit=session.audit)
    if not store.save(session.changes, turn):
        return replay(store.get("conversations", key), request)
    return turn


@app.get("/", include_in_schema=False)
def home(request: Request):
    page = "index.html" if valid_session(request, server_password()) else "login.html"
    return FileResponse(assets / page, headers={"Cache-Control": "no-store"})


@app.post("/session", include_in_schema=False)
def login(request: Request, credentials: Annotated[HTTPBasicCredentials | None, Depends(security)]):
    password = server_password()
    if not credentials or credentials.username != "spendwise" or not secrets.compare_digest(
            credentials.password.encode(), password.encode()):
        raise HTTPException(401, "가계부 비밀번호를 확인하세요.")
    payload = f"{int(time.time()) + SESSION_SECONDS}.{secrets.token_hex(16)}"
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.set_cookie(SESSION_COOKIE, payload + "." + signature(payload, password),
                        max_age=SESSION_SECONDS, secure=True, httponly=True, samesite="lax")
    return response


@app.post("/session/logout", include_in_schema=False)
def logout(request: Request):
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403)
    response = RedirectResponse("/", status_code=303, headers={"Cache-Control": "no-store"})
    response.delete_cookie(SESSION_COOKIE, secure=True, httponly=True, samesite="lax")
    return response


app.mount("/assets", StaticFiles(directory=assets, check_dir=False), name="assets")
