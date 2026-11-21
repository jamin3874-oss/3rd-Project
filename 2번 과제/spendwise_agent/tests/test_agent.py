import tempfile
import unittest
from pathlib import Path
from storage import Storage
from agent import Agent
from tools import classify

class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Storage(Path(self.temp.name)/'test.db')
        self.agent=Agent(self.db)
    def tearDown(self):self.db.conn.close();self.temp.cleanup()
    def test_classification(self):self.assertEqual(classify('스타벅스'),'카페')
    def test_add_and_summary(self):
        self.assertEqual(self.agent.execute('추가 2026-11-20 스타벅스 4800')['result']['category'],'카페')
        self.assertEqual(self.agent.execute('요약 2026-11')['result']['total'],4800)
    def test_budget(self):
        self.agent.execute('예산 2026-11 카페 10000')
        self.agent.execute('추가 2026-11-20 스타벅스 4800')
        self.assertEqual(self.agent.execute('요약 2026-11')['result']['category_remaining']['카페'],5200)
    def test_natural_language(self):
        self.assertEqual(self.agent.execute('2026-11-20에 스타벅스에서 4,800원 썼어')['result']['amount'],4800)
    def test_negative_rejected(self):self.assertIn('error',self.agent.execute('추가 2026-11-20 식당 -200'))
    def test_unknown_command_logged(self):
        self.assertIn('error',self.agent.execute('아무 말'))
        self.assertEqual(len(self.db.rows('SELECT * FROM agent_events')),1)
    def test_invalid_budget(self):self.assertIn('error',self.agent.execute('예산 2026-15 식비 1000'))
    def test_import_idempotence(self):
        path=Path(self.temp.name)/'sample.csv'
        path.write_text('date,merchant,amount\n2026-11-01,스타벅스,1000\n',encoding='utf-8')
        a=self.agent.execute(f'CSV {path}')['result']
        b=self.agent.execute(f'CSV {path}')['result']
        self.assertEqual(a['imported'],1)
        self.assertEqual(b['duplicates_skipped'],1)
    def test_compare(self):
        self.agent.execute('추가 2026-10-11 식당 1000')
        self.agent.execute('추가 2026-11-11 식당 1200')
        self.assertEqual(self.agent.execute('비교 2026-10 2026-11')['result']['change_pct'],20)
if __name__=='__main__':unittest.main()
