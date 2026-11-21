import json
import os
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from backend import Handler


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dbfile = str(Path(self.temp.name) / 'backend-test.db')
        self.patch = patch.dict(os.environ, {'SPENDWISE_DB': self.dbfile}, clear=False)
        self.patch.start()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.patch.stop()
        self.temp.cleanup()

    def request(self, method, path, payload=None, ctype='application/json'):
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        body = None if payload is None else json.dumps(payload).encode('utf-8')
        headers = {'Content-Type': ctype}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        result = (response.status, response.getheader('Access-Control-Allow-Origin'), json.loads(raw))
        connection.close()
        return result

    def test_health_no_key_exposure(self):
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-secret-key'}):
            code, cors, result = self.request('GET', '/health')
        self.assertEqual(code, 200)
        self.assertNotIn('test-secret-key', json.dumps(result))
        self.assertIsNone(cors)

    def test_register_and_summarize(self):
        code, _, data = self.request('POST', '/api/chat', {'message': '추가 2026-11-20 스타벅스 4800'})
        self.assertEqual(code, 200)
        self.assertEqual(data['result']['amount'], 4800)
        code, _, data = self.request('POST', '/api/chat', {'message': '요약 2026-11'})
        self.assertEqual(code, 200)
        self.assertEqual(data['result']['total'], 4800)

    def test_rejects_non_json(self):
        code, _, data = self.request('POST', '/api/chat', {'message': 'hello'}, 'text/plain')
        self.assertEqual(code, 415)

    def test_rejects_missing_message(self):
        code, _, data = self.request('POST', '/api/chat', {'foo': 'bar'})
        self.assertEqual(code, 400)

    def test_llm_needs_config(self):
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': ''}):
            code, _, data = self.request('POST', '/api/chat', {'message': 'AI: 2026-11 지출 요약해줘'})
        self.assertEqual(code, 400)
        self.assertIn('ANTHROPIC_API_KEY', data['error'])


if __name__ == '__main__':
    unittest.main()
