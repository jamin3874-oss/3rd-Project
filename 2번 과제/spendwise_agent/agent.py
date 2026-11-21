"""Natural-language, auditable personal-finance agent.
Optional Anthropic-compatible Claude Tool Use; deterministic router works offline.
"""
import json
import os
import re
import shlex
from datetime import date
from tools import TOOLS, classify, CATEGORIES

HELP = '''사용 예:
  추가 2026-11-21 카페 4500
  예산 2026-11 식비 300000
  요약 2026-11
  상위 2026-11
  비교 2026-10 2026-11
  CSV sample_data/example_transactions.csv
  종료
자연어 예: '2026-11-21에 스타벅스에서 4500원 썼어', '2026-11월 소비 요약해줘'
기본 모드는 규칙 기반 파서이며, ANTHROPIC_API_KEY가 있으면 'AI:' 접두어로 Claude Tool Use를 사용할 수 있습니다.
'''

class Agent:
    def __init__(self, storage, *, handlers=None, context='', history=()):
        self.db=storage
        self.handlers = TOOLS if handlers is None else handlers
        self.context = context
        self.history = history

    def execute(self, command):
        command=command.strip()
        if not command: return {'error':'빈 명령입니다.'}
        if command in ('도움말','help','?'): return {'help':HELP}
        try:
            if command.startswith('AI:'):
                return self._claude_execute(command[3:].strip(), command)
            else:
                tool,args=self._route(command)
            if tool not in self.handlers: raise ValueError('허용되지 않은 도구입니다.')
            # No external command or arbitrary code execution. Only approved tools.
            result=self.handlers[tool](self.db,**args)
            self.db.log(command,tool,args,result)
            return {'tool':tool,'result':result}
        except Exception as exc:
            response={'error':str(exc),'command':command}
            self.db.log(command,'error',{},response)
            return response

    def _route(self,s):
        if s[:4].upper() == 'CSV ':
            return 'import_csv', dict(path=s[4:].strip().strip('"').strip("'"))
        parts=shlex.split(s)
        if not parts: raise ValueError('빈 명령입니다.')
        head=parts[0]
        if head=='추가' and len(parts)>=4:
            return 'add_expense',dict(txn_date=parts[1],merchant=parts[2],amount=parts[3])
        if head=='예산' and len(parts)==4:
            return 'set_budget',dict(month=parts[1],category=parts[2],amount=parts[3])
        if head=='요약' and len(parts)==2: return 'summarize',dict(month=parts[1])
        if head=='상위' and len(parts)==2: return 'top_merchants',dict(month=parts[1])
        if head=='비교' and len(parts)==3: return 'compare_months',dict(left=parts[1],right=parts[2])
        if head.upper()=='CSV' and len(parts)==2: return 'import_csv',dict(path=parts[1])
        # Limited safe, Korean natural-language patterns
        match=re.search(r'(\d{4}-\d{2}-\d{2}).*?([^\s]+)에서\s*([\d,]+)원',s)
        if match:
            return 'add_expense',dict(txn_date=match.group(1),merchant=match.group(2),amount=match.group(3).replace(',',''))
        month=re.search(r'(\d{4}-\d{2})',s)
        if month and any(k in s for k in ('요약','얼마','지출','소비')): return 'summarize',dict(month=month.group(1))
        raise ValueError('명령을 이해하지 못했습니다. 도움말을 입력하세요.')

    @staticmethod
    def _tool_schema():
        definitions = {
            'add_expense': {
                'description': '날짜·상호·금액이 분명한 지출 1건을 등록합니다. 지출을 임의 생성하지 마세요.',
                'fields': {'txn_date': '지출 날짜 YYYY-MM-DD', 'merchant': '상호명', 'amount': '양의 정수 원 단위 금액'},
            },
            'set_budget': {
                'description': '사용자가 명시적으로 요청한 월별 예산을 설정합니다.',
                'fields': {'month': '대상 월 YYYY-MM', 'category': '식비/카페/교통/쇼핑/주거/의료/교육/생활/기타/전체', 'amount': '0 이상의 원 단위 금액'},
            },
            'summarize': {
                'description': '월별 총지출, 카테고리, 예산 잔액을 조회합니다.',
                'fields': {'month': '조회 월 YYYY-MM'},
            },
            'top_merchants': {
                'description': '월별 지출이 높은 상호를 조회합니다.',
                'fields': {'month': '조회 월 YYYY-MM'},
            },
            'compare_months': {
                'description': '두 월의 지출 합계를 비교합니다.',
                'fields': {'left': '비교 시작 월 YYYY-MM', 'right': '비교 종료 월 YYYY-MM'},
            },
        }
        specs=[]
        for name, spec in definitions.items():
            specs.append({
                'name': name, 'description': spec['description'],
                'input_schema': {
                    'type': 'object',
                    'properties': {key: {'type': 'string', 'description': desc} for key, desc in spec['fields'].items()},
                    'required': list(spec['fields']),
                    'additionalProperties': False,
                },
            })
        return specs, definitions

    def _claude_execute(self, text, command):
        """Claude Messages Tool Use: assistant(tool_use) -> user(tool_result) -> assistant(text).

        Only approved tools can execute, at most one invocation per user command.
        LLM outputs never directly execute arbitrary Python, shell or CSV import.
        """
        if not text:
            raise ValueError('AI: 다음에 요청 내용을 입력해주세요.')
        key=os.getenv('ANTHROPIC_API_KEY','').strip()
        if not key or key in ('YOUR_API_KEY','본인의_코디세이_API_키'):
            raise ValueError('AI 모드에는 ANTHROPIC_API_KEY가 필요합니다. .env 파일을 확인하세요.')
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ValueError('Claude 모드는 python -m pip install anthropic 설치가 필요합니다.') from exc
        base=os.getenv('ANTHROPIC_BASE_URL','https://api.anthropic.com').strip()
        model=os.getenv('ANTHROPIC_MODEL','claude-sonnet-4').strip()
        specs,definitions=self._tool_schema()
        client=Anthropic(api_key=key,base_url=base,timeout=25.0,max_retries=1)
        messages=[*self.history, {'role':'user','content':text}]
        try:
            first=client.messages.create(
                model=model,max_tokens=1024,
                system=('당신은 가계부 AI 비서입니다. 모든 소비 수치는 제공된 도구 결과만 근거로 제시하세요. '
                        '날짜/금액이 빠진 경우 추측하지 말고 질문하세요. 요청이 읽기인지 쓰기인지 확인하세요. '
                        '하나의 명시적 작업에 대해서만 허용 도구를 호출합니다. '
                        '은행 계정 접근, 코드 실행, 임의 파일 작업은 불가능합니다.' + self.context),
                messages=messages,tools=specs,tool_choice={'type':'auto'},
            )
            calls=[item for item in first.content if item.type=='tool_use']
            if not calls:
                reply=' '.join(item.text for item in first.content if item.type=='text').strip()
                result={'message':reply or '날짜·금액 또는 요청 내용을 구체적으로 알려주세요.'}
                self.db.log(command,'clarification',{},result)
                return result
            if len(calls)!=1:
                raise ValueError('한 번에 여러 도구를 실행하려는 요청은 지원하지 않습니다. 한 작업씩 요청해주세요.')
            call=calls[0]
            name=call.name
            if name not in definitions or name not in self.handlers:
                raise ValueError('허용되지 않은 AI 도구입니다.')
            args=call.input
            if not isinstance(args,dict) or set(args)!=set(definitions[name]['fields']):
                raise ValueError('Claude의 도구 인자 형식이 올바르지 않습니다.')
            if any(not isinstance(v,str) for v in args.values()):
                raise ValueError('Claude 도구 인자는 모두 문자열이어야 합니다.')
            # Write action is explicit only; prevent unsolicited transactions/budget changes.
            if name in ('add_expense','set_budget') and not any(
                word in text for word in ('추가','등록','기록','썼','지출했','결제했','설정','변경','잡아','정해')
            ):
                raise ValueError('지출 등록이나 예산 변경을 실행하려면 명시적으로 요청해야 합니다.')
            executed=self.handlers[name](self.db,**args)
            self.db.log(command,name,args,executed)
            # Return tool_result using Anthropic Messages content blocks format.
            assistant_blocks=[]
            for block in first.content:
                if hasattr(block,'model_dump'):
                    assistant_blocks.append(block.model_dump(exclude_none=True))
                elif isinstance(block,dict):
                    assistant_blocks.append(block)
                else:
                    raise ValueError('Claude 응답 블록을 직렬화할 수 없습니다.')
            messages.extend([
                {'role':'assistant','content':assistant_blocks},
                {'role':'user','content':[{
                    'type':'tool_result','tool_use_id':call.id,
                    'content':json.dumps(executed,ensure_ascii=False),
                }]},
            ])
            try:
                final=client.messages.create(
                    model=model,max_tokens=512,
                    system='도구에서 전달된 JSON 결과만 근거로 간결하게 한국어 답변을 작성하세요. 추가 도구를 호출하지 마세요.',
                    messages=messages,
                )
                answer=' '.join(x.text for x in final.content if x.type=='text').strip()
            except Exception:
                # A successful write must not be reported as failed or retried after follow-up failure.
                answer='도구 실행은 성공했습니다. 최종 AI 문장 생성은 실패하여 구조화된 결과만 반환합니다.'
            return {'tool':name,'result':executed,'assistant_message':answer}
        except Exception as exc:
            # Do not echo provider errors, which sometimes contain API-key fragments.
            if isinstance(exc, ValueError):
                raise
            error_type=type(exc).__name__
            raise RuntimeError(f'Claude API 요청 실패 ({error_type}). 서버 주소, 인증 권한, 모델 및 Tool Use 지원을 확인하세요.') from None
