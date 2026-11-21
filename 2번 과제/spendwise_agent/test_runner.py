"""Reproducible SpendWise integration scenarios.

Default: mocked Claude Tool Use with temporary SQLite, no network.
--live: actual Codyssey Claude Tool Use, explicitly opt-in (may incur usage charges).
Never opens or modifies spendwise.db; never writes API keys to JSON.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agent import Agent
from config import ROOT, load_backend_env
from storage import Storage

RESULTS = ROOT / 'results'
TEST_MONTH = '2026-11'


def _block(kind, **fields):
    class Block(SimpleNamespace):
        def model_dump(self, exclude_none=True):
            return {'type': kind, **fields}
    return Block(type=kind, **fields)


class MockClaude:
    """Predictable Anthropic SDK stand-in; proves routing, not model quality."""
    current = None
    def __init__(self, **kwargs):
        self.messages = self
    def create(self, **kwargs):
        state = type(self).current
        state['call_count'] += 1
        if state['call_count'] == 1:
            if state['tool'] is None:
                return SimpleNamespace(content=[_block('text', text='올바른 금액과 날짜를 입력해주세요.')])
            return SimpleNamespace(content=[_block('tool_use', id='mock_001', name=state['tool'], input=state['args'])])
        return SimpleNamespace(content=[_block('text', text='도구 실행 결과를 확인했습니다.')])


# All amounts and merchants in test data are fabricated. None are user's real records.
SCENARIOS = [
    {'id': 'TC-001', 'label': '거래 등록', 'input': 'AI: 2026-11-21 스타벅스에서 4500원 쓴 내역을 등록해줘',
     'expected_tool': 'add_expense', 'args': {'txn_date':'2026-11-21','merchant':'스타벅스','amount':'4500'}},
    {'id': 'TC-002', 'label': '등록 거래 재조회', 'input': 'AI: 2026-11월 소비 요약해줘',
     'expected_tool': 'summarize', 'args': {'month':TEST_MONTH}},
    {'id': 'TC-003', 'label': '카페 예산 설정', 'input': 'AI: 2026-11월 카페 예산을 50000원으로 설정해줘',
     'expected_tool': 'set_budget', 'args': {'month':TEST_MONTH,'category':'카페','amount':'50000'}},
    {'id': 'TC-004', 'label': '예산 잔액 검증', 'input': 'AI: 2026-11월 카페 예산에서 얼마를 썼고 얼마나 남았는지 요약해줘',
     'expected_tool': 'summarize', 'args': {'month':TEST_MONTH}},
    {'id': 'TC-005', 'label': '잘못된 날짜 거부', 'input': 'AI: 2026-02-30에 스타벅스에서 1200원 쓴 내역을 등록해줘',
     'expected_tool': None, 'args': {}},
    {'id': 'TC-006', 'label': '잘못된 금액 거부', 'input': 'AI: 2026-11-21 스타벅스에서 -100원 쓴 내역을 등록해줘',
     'expected_tool': None, 'args': {}},
]


def _safe(text):
    """Remove credentials from any human-readable exception message."""
    text = str(text)
    for name in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY'):
        secret = os.environ.get(name, '')
        if secret:
            text = text.replace(secret, '[REDACTED]')
    text = re.sub(r'sk-[A-Za-z0-9_-]{8,}', '[REDACTED]', text)
    return text[:280]


def _count(db):
    return db.rows('SELECT COUNT(*) AS n FROM transactions')[0]['n']


def _validate(case, response, db):
    tool = response.get('tool')
    result = response.get('result') or {}
    expected = case['expected_tool']
    checks = {'tool_match': tool == expected} if expected else {'write_rejected': tool not in ('add_expense','set_budget')}
    if case['id'] == 'TC-001':
        checks['persisted_amount'] = (result.get('status')=='added' and result.get('amount')==4500 and _count(db)==1)
    elif case['id'] == 'TC-002':
        checks['summary_matches_db'] = (result.get('total')==4500 and result.get('count')==1 and any(x['category']=='카페' and x['total']==4500 for x in result.get('by_category',[])))
    elif case['id'] == 'TC-003':
        checks['budget_persisted'] = (result.get('budget')==50000 and db.rows("SELECT amount FROM budgets WHERE month=? AND category=?", (TEST_MONTH,'카페'))[0]['amount']==50000)
    elif case['id'] == 'TC-004':
        checks['budget_remaining'] = (result.get('total')==4500 and result.get('category_remaining',{}).get('카페')==45500)
    else:
        checks['database_unchanged'] = _count(db)==1
        checks['not_accidentally_accepted'] = 'error' in response or 'message' in response
    return checks


def run(mode='mock', output=None):
    if mode not in ('mock','live'):
        raise ValueError('mode must be mock or live')
    if mode=='live':
        load_backend_env()
    output = Path(output) if output else RESULTS/'test_results.json'
    report={'schema_version':1,'run_at_utc':datetime.now(timezone.utc).isoformat(),
            'mode':mode,'source':'script-generated, synthetic transactions',
            'live_api_called':False,'is_live_evidence':False,
            'database':'isolated temporary SQLite (removed after execution)',
            'test_cases':[]}
    key=os.environ.get('ANTHROPIC_API_KEY','').strip()
    if mode=='live' and (not key or key in ('YOUR_API_KEY','본인의_코디세이_API_키')):
        for case in SCENARIOS:
            report['test_cases'].append({'test_id':case['id'],'label':case['label'],'input':case['input'],
                                         'expected_tool':case['expected_tool'],'actual_tool':None,
                                         'validation':{},'status':'SKIP','reason':'No configured Anthropic API key'})
    else:
        with tempfile.TemporaryDirectory(prefix='spendwise_test_') as temp:
            db=Storage(Path(temp)/'integration.sqlite3')
            agent=Agent(db)
            try:
                for case in SCENARIOS:
                    with ExitStack() as stack:
                        if mode=='mock':
                            MockClaude.current={'tool':case['expected_tool'], 'args':case['args'], 'call_count':0}
                            stack.enter_context(patch.dict(sys.modules, {'anthropic':SimpleNamespace(Anthropic=MockClaude)}))
                            stack.enter_context(patch.dict(os.environ, {'ANTHROPIC_API_KEY':'mock-key-do-not-use',
                                'ANTHROPIC_BASE_URL':'https://mock.invalid', 'ANTHROPIC_MODEL':'mock'}, clear=False))
                        else:
                            report['live_api_called']=True
                        try:
                            response=agent.execute(case['input'])
                            checks=_validate(case,response,db)
                            status='PASS' if all(checks.values()) else 'FAIL'
                            item={'test_id':case['id'],'label':case['label'],'input':case['input'],
                                  'expected_tool':case['expected_tool'],'actual_tool':response.get('tool'),
                                  'validation':checks,'status':status}
                            # Only allowlisted synthetic result fields; do not store free-form model responses.
                            if response.get('result'):
                                result=response['result']
                                item['result']={k:result.get(k) for k in ('status','date','merchant','amount','category','total','count','budget','category_remaining') if k in result}
                            if 'error' in response: item['error'] = _safe(response['error'])
                        except Exception as e:
                            item={'test_id':case['id'],'label':case['label'],'input':case['input'],
                                  'expected_tool':case['expected_tool'],'actual_tool':None,
                                  'validation':{},'status':'FAIL','error':_safe(e)}
                        report['test_cases'].append(item)
            finally:
                db.conn.close()
    counts={s:sum(t['status']==s for t in report['test_cases']) for s in ('PASS','FAIL','SKIP')}
    report['summary']={'total':len(SCENARIOS), **counts}
    report['is_live_evidence'] = mode == 'live' and report['live_api_called']
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description='SpendWise 자동 테스트 및 JSON 증빙 생성')
    parser.add_argument('--live',action='store_true', help='실제 Claude API 호출 (명시적 선택, 요금 발생 가능)')
    parser.add_argument('--output',default=None,help='JSON 결과 파일 경로')
    opts=parser.parse_args()
    result=run('live' if opts.live else 'mock',opts.output)
    print(json.dumps({'mode':result['mode'],'summary':result['summary'],
        'output':str(Path(opts.output) if opts.output else RESULTS/'test_results.json')},ensure_ascii=False,indent=2))
    return 1 if result['summary']['FAIL'] else 0


if __name__=='__main__':
    raise SystemExit(main())
