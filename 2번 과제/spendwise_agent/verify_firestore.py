"""Verify the assignment fixture using FastAPI and the real Firestore project."""
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from web_api import app
from web_store import FirestoreStore

PROJECT = "spendwise-f6d6d"
SAMPLE = "0eea85e2-70ac-4917-a118-de950b170001"
TURN = "ea776e3c-5910-4b2a-91af-bc54a4c90001"
MONTH = "2026-11"


def verify(client, store):
    def call(method, route, **kwargs):
        response = client.request(method, route, **kwargs)
        response.raise_for_status()
        return response.json()

    list_route = f"/api/data?month={MONTH}"
    summary_route = f"/api/data/summary?month={MONTH}"
    rows = call("GET", list_route)
    row = next((item for item in rows if item["id"] == SAMPLE), None)
    if not row or row["merchant"] != "과제 예시 카페" or row["amount"] not in (5200, 5300):
        raise RuntimeError("검증용 거래가 예상 상태와 다릅니다. 기존 거래를 확인하세요.")
    before = call("GET", summary_route)
    edit = {"merchant":row["merchant"], "txn_date":row["txn_date"], "amount":5300}
    call("PUT", f"/api/data/{SAMPLE}", json=edit)
    after = call("GET", summary_route)
    reloaded = next(item for item in call("GET", list_route) if item["id"] == SAMPLE)
    if (reloaded["amount"] != 5300 or store.get("data", SAMPLE)["amount"] != 5300
            or after["count"] != before["count"] or after["total"] - before["total"] != 5300 - row["amount"]):
        raise RuntimeError("거래 문서, 목록, 월 요약 값이 일치하지 않습니다.")
    turn = call("POST", "/api/chat", json={"message":"요약 "+MONTH, "month":MONTH, "request_id":TURN})
    history = call("GET", "/api/conversations?limit=100")
    if (turn not in history or turn["tool"] != "summarize" or
            store.get("conversations", TURN)["reply"] != turn["reply"]):
        raise RuntimeError("대화 응답과 Firestore에 저장한 대화가 일치하지 않습니다.")
    return {"checked_at":datetime.now(timezone.utc).isoformat(), "project":PROJECT,
            "document":SAMPLE, "before_amount":row["amount"], "after_amount":reloaded["amount"],
            "before_total":before["total"], "after_total":after["total"], "conversation":turn}


if __name__ == "__main__":
    if (os.getenv("GOOGLE_CLOUD_PROJECT") != PROJECT or os.getenv("FIRESTORE_EMULATOR_HOST")
            or os.getenv("SPENDWISE_STORE") == "memory"):
        raise SystemExit(f"실제 검증 프로젝트 {PROJECT} 설정을 확인하세요.")
    os.environ.setdefault("SPENDWISE_PASSWORD", secrets.token_urlsafe(32))
    with TestClient(app) as client:
        client.auth = ("spendwise", os.environ["SPENDWISE_PASSWORD"])
        result = verify(client, FirestoreStore())
    target = Path(__file__).parent / "evidence" / "live-firestore-api.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
