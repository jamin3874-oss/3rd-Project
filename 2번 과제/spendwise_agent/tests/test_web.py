import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from fastapi import FastAPI
from test_claude import FakeClient, block
from web_api import app, configure_origins
from web_store import MemoryStore, get_store


class WebTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        app.dependency_overrides[get_store] = lambda: self.store
        self.addCleanup(app.dependency_overrides.clear)
        self.enterContext(patch.dict(os.environ, SPENDWISE_PASSWORD="fixture"))
        self.client = TestClient(app)
        self.client.auth = ("spendwise", "fixture")
        self.item = dict(txn_date="2026-11-21", merchant="카페", amount=4500)

    def test_public_schema_and_private_records(self):
        self.assertEqual(self.client.get("/docs").status_code, 200)
        schema = self.client.get("/openapi.json").json()
        self.assertIn("/api/data/summary", schema["paths"])
        self.assertEqual(self.client.get("/api/conversations", auth=None).status_code, 401)
        self.assertEqual(self.client.post("/api/data", json={**self.item,"amount":-1}).status_code, 422)

    def test_month_change_refresh(self):
        row = self.client.post("/api/data", json=self.item)
        self.assertEqual(row.status_code, 201)
        key = row.json()["id"]
        updated = self.client.put("/api/data/"+key, json={**self.item,"txn_date":"2026-12-01"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(self.client.get("/api/data?month=2026-11").json(), [])
        self.assertEqual(self.client.get("/api/data/summary?month=2026-12").json()["total"], 4500)

    def test_cors_allowlist(self):
        origin = "https://ledger.example.org"
        headers = {"Origin": origin, "Access-Control-Request-Method": "PUT",
                   "Access-Control-Request-Headers": "authorization,content-type"}
        self.assertNotIn("access-control-allow-origin", self.client.options("/api/data", headers=headers).headers)
        separate = FastAPI()
        configure_origins(separate, origin)
        client = TestClient(separate)
        allowed = client.options("/api/data", headers=headers)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.headers["access-control-allow-origin"], origin)
        denied = client.options("/api/data", headers={**headers, "Origin": "https://other.example.org"})
        self.assertEqual(denied.status_code, 400)
        self.assertNotIn("access-control-allow-origin", denied.headers)
        with self.assertRaises(ValueError):
            configure_origins(FastAPI(), "*")

    def test_rejected_inputs_do_not_write(self):
        for change in [{"amount":0}, {"amount":2.5}, {"amount":10**12+1},
                       {"txn_date":"2026-02-30"}, {"merchant":"  "}, {"role":"admin"}]:
            with self.subTest(change=change):
                self.assertEqual(self.client.post("/api/data", json={**self.item, **change}).status_code, 422)
        self.assertEqual(self.client.get("/api/data?month=2026-13").status_code, 422)
        self.assertEqual(self.client.post("/api/chat", json={"message":" ", "month":"2026-11"}).status_code, 422)
        self.assertEqual(self.client.get("/api/data?month=2026-11").json(), [])
        self.assertEqual(self.client.get("/api/conversations").json(), [])

    def test_chat_retry_history_and_budget(self):
        request = dict(month="2026-11",message="추가 2026-11-21 카페 4500",request_id=str(uuid4()))
        reply = self.client.post("/api/chat",json=request)
        self.assertEqual(reply.status_code,200,reply.text)
        self.assertEqual(self.client.post("/api/chat",json=request).json(),reply.json())
        self.assertEqual(self.client.post("/api/chat",json={**request,"message":"다른 요청"}).status_code,409)
        self.assertEqual(self.client.get("/api/conversations").json(),[reply.json()])
        self.client.post("/api/chat",json=dict(month="2026-11",message="예산 2026-11 전체 10000"))
        self.assertEqual(self.client.get("/api/data/summary?month=2026-11").json()["overall_remaining"],5500)

    def test_claude_system_summary_and_tool_result(self):
        self.client.post("/api/data",json=self.item)
        FakeClient.calls = []
        FakeClient.scripted = [
            SimpleNamespace(content=[block("tool_use",id="fixture",name="summarize",input={"month":"2026-11"})]),
            SimpleNamespace(content=[block("text",text="이번 달 지출은 4,500원입니다.")])]
        with patch.dict("sys.modules",anthropic=SimpleNamespace(Anthropic=FakeClient)), patch.dict(os.environ,ANTHROPIC_API_KEY="fixture"):
            result = self.client.post("/api/chat",json=dict(month="2026-11",message="AI: 이번 달 지출 요약"))
        self.assertEqual(result.json()["tool"], "summarize")
        prompt = FakeClient.calls[0]["system"]
        self.assertEqual(json.loads(prompt.splitlines()[-1])["total"],4500)
        self.assertEqual(FakeClient.calls[1]["messages"][-1]["content"][0]["type"],"tool_result")
