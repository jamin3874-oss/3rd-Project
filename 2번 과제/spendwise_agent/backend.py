"""Local-only HTTP backend for SpendWise. No API keys are sent to clients.

Run: python backend.py
POST http://127.0.0.1:8765/api/chat
body: {"message": "AI: 이번 달 소비 요약해줘"}
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from agent import Agent
from config import ROOT, load_backend_env
from storage import Storage

HOST = '127.0.0.1'  # Never expose database or key to the public network.
PORT = 8765
MAX_BODY = 8192


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        # Intentionally no Access-Control-Allow-Origin: browser cross-origin calls blocked.
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if urlparse(self.path).path == '/health':
            self._send(200, {'status': 'ok', 'llm_enabled': bool(os.getenv('ANTHROPIC_API_KEY'))})
        else:
            self._send(404, {'error': '경로를 찾을 수 없습니다.'})

    def do_POST(self):
        if urlparse(self.path).path != '/api/chat':
            return self._send(404, {'error': '경로를 찾을 수 없습니다.'})
        if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            return self._send(415, {'error': 'Content-Type: application/json이 필요합니다.'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self._send(400, {'error': '잘못된 Content-Length입니다.'})
        if size <= 0 or size > MAX_BODY:
            return self._send(413, {'error': '요청은 8KB 이하여야 합니다.'})
        try:
            data = json.loads(self.rfile.read(size))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._send(400, {'error': '올바른 JSON이 아닙니다.'})
        if not isinstance(data, dict) or not isinstance(data.get('message'), str):
            return self._send(400, {'error': 'message 문자열이 필요합니다.'})
        message = data['message'].strip()
        if not message or len(message) > 2000:
            return self._send(400, {'error': '요청 문장은 1~2000자여야 합니다.'})
        # One DB connection per request; SQLite is not shared across threads.
        db = Storage(os.getenv('SPENDWISE_DB', str(ROOT / 'spendwise.db')))
        try:
            result = Agent(db).execute(message)
        finally:
            db.conn.close()
        self._send(400 if 'error' in result else 200, result)

    def log_message(self, fmt, *args):
        # Don't log user-entered finance messages (request paths only in base class).
        return


def main():
    load_backend_env()
    with ThreadingHTTPServer((HOST, PORT), Handler) as server:
        print(f'SpendWise backend: http://{HOST}:{PORT}  (Ctrl+C로 종료)')
        print('API 키는 백엔드 환경변수에서만 읽습니다. 금융 데이터는 로컬 SQLite에 저장합니다.')
        server.serve_forever()


if __name__ == '__main__':
    main()
