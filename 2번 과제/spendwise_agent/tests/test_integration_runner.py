import json
import tempfile
import unittest
from pathlib import Path
from test_runner import run

class RunnerTests(unittest.TestCase):
    def test_mock_scenarios_write_json_and_pass(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'results.json'
            report=run('mock',path)
            self.assertEqual(report['summary'],{'total':6,'PASS':6,'FAIL':0,'SKIP':0})
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['summary'],report['summary'])
            self.assertFalse(report['live_api_called'])
    def test_no_api_key_skips_live_without_call(self):
        import os
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'ANTHROPIC_API_KEY':''}):
            report=run('live',Path(d)/'live.json')
            self.assertEqual(report['summary']['SKIP'],6)
            self.assertFalse(report['live_api_called'])

if __name__=='__main__': unittest.main()
