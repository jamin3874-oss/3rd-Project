import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agent import Agent
from storage import Storage


def block(kind, **data):
    class Block(SimpleNamespace):
        def model_dump(self, exclude_none=True):
            return {'type':kind, **data}
    return Block(type=kind, **data)


class FakeClient:
    scripted=[]
    calls=[]
    def __init__(self,*args,**kwargs):
        self.messages=self
    def create(self,**kwargs):
        self.calls.append(kwargs)
        return self.scripted.pop(0)


class ClaudeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.storage=Storage(Path(self.tmp.name)/'t.db')
        self.agent=Agent(self.storage)
        FakeClient.calls=[]
        FakeClient.scripted=[]
        import sys
        self.patch_module=patch.dict(sys.modules,{'anthropic': SimpleNamespace(Anthropic=FakeClient)})
        self.patch_env=patch.dict(os.environ,{
            'ANTHROPIC_API_KEY':'local-test-only','ANTHROPIC_BASE_URL':'https://copa.codyssey.kr',
            'ANTHROPIC_MODEL':'claude-sonnet-4'},clear=False)
        self.patch_module.start();self.patch_env.start()
    def tearDown(self):
        self.patch_env.stop();self.patch_module.stop()
        self.storage.conn.close();self.tmp.cleanup()
    def test_tool_use_result_roundtrip(self):
        FakeClient.scripted=[
            SimpleNamespace(content=[block('tool_use',id='toolu_123',name='summarize',input={'month':'2026-11'})]),
            SimpleNamespace(content=[block('text',text='11월 지출은 0원입니다.')]),
        ]
        result=self.agent.execute('AI: 2026-11 지출 요약해줘')
        self.assertEqual(result['tool'],'summarize')
        self.assertEqual(result['result']['total'],0)
        self.assertIn('0원',result['assistant_message'])
        second=FakeClient.calls[1]['messages']
        self.assertEqual(second[-1]['content'][0]['type'],'tool_result')
        self.assertEqual(second[-1]['content'][0]['tool_use_id'],'toolu_123')
        self.assertEqual(FakeClient.calls[0]['tools'][0]['input_schema']['type'],'object')
    def test_ambiguity_does_not_modify_db(self):
        FakeClient.scripted=[SimpleNamespace(content=[block('text',text='어느 월을 말씀하시나요?')])]
        result=self.agent.execute('AI: 이번 달 지출 정리')
        self.assertEqual(result['message'],'어느 월을 말씀하시나요?')
        self.assertEqual(self.storage.rows('SELECT COUNT(*) AS c FROM transactions')[0]['c'],0)
    def test_unapproved_tool_rejected(self):
        FakeClient.scripted=[SimpleNamespace(content=[block('tool_use',id='x',name='delete_database',input={})])]
        self.assertIn('error',self.agent.execute('AI: 지출 조회해줘'))
    def test_unrequested_write_rejected(self):
        FakeClient.scripted=[SimpleNamespace(content=[block('tool_use',id='x',name='add_expense',input={'txn_date':'2026-11-21','merchant':'스타벅스','amount':'1000'})])]
        self.assertIn('error',self.agent.execute('AI: 2026-11-21 지출 조회해줘'))
    def test_valid_add_and_followup_failure(self):
        FakeClient.scripted=[SimpleNamespace(content=[block('tool_use',id='x',name='add_expense',input={'txn_date':'2026-11-21','merchant':'스타벅스','amount':'1000'})])]
        result=self.agent.execute('AI: 2026-11-21 스타벅스 1000원 지출 등록해줘')
        self.assertEqual(result['result']['amount'],1000)
        self.assertIn('성공',result['assistant_message'])
        self.assertEqual(self.storage.rows('SELECT COUNT(*) AS c FROM transactions')[0]['c'],1)
    def test_multiple_tools_rejected(self):
        FakeClient.scripted=[SimpleNamespace(content=[block('tool_use',id='x',name='summarize',input={'month':'2026-11'}),block('tool_use',id='y',name='summarize',input={'month':'2026-10'})])]
        self.assertIn('error',self.agent.execute('AI: 두 달 조회해줘'))
    def test_provider_error_hides_key(self):
        class ErrorClient(FakeClient):
            def create(self,**kwargs):
                raise RuntimeError('Invalid key local-test-only')
        import sys
        with patch.dict(sys.modules, {'anthropic':SimpleNamespace(Anthropic=ErrorClient)}):
            result=self.agent.execute('AI: 2026-11월 소비 요약해줘')
        self.assertIn('error',result)
        self.assertNotIn('local-test-only',str(result))

if __name__=='__main__':unittest.main()
