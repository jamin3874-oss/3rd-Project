"""Pure, testable tools used by the agent."""
import csv
import hashlib
import re
from datetime import date
from collections import defaultdict
from pathlib import Path

CATEGORIES = ('식비','카페','교통','쇼핑','주거','의료','교육','생활','기타')
RULES = {
    '카페': ('스타벅스','이디야','투썸','컴포즈','메가커피','커피빈','카페'),
    '교통': ('택시','지하철','버스','주유','고속도로','충전소','톨게이트'),
    '식비': ('식당','김밥','치킨','피자','버거','마트','편의점','배달','국밥','분식'),
    '쇼핑': ('쿠팡','올리브영','무신사','다이소','쇼핑'),
    '주거': ('관리비','전기요금','도시가스','월세','인터넷'),
    '의료': ('병원','약국','치과'),
    '교육': ('학원','서점','교재','강의'),
    '생활': ('세탁','미용실','생활용품'),
}

def classify(merchant):
    for category, words in RULES.items():
        if any(word.casefold() in merchant.casefold() for word in words):
            return category
    return '기타'

def valid_month(value):
    if not re.fullmatch(r'\d{4}-\d{2}',value): raise ValueError('월 형식은 YYYY-MM 이어야 합니다.')
    date.fromisoformat(value+'-01')
    return value

def add_expense(db, txn_date, merchant, amount, category=None, note='', source_id=None):
    date.fromisoformat(txn_date)
    merchant = merchant.strip()
    if not merchant: raise ValueError('상호명을 입력하세요.')
    amount = int(amount)
    if amount <= 0: raise ValueError('지출 금액은 양수여야 합니다.')
    category = category or classify(merchant)
    if category not in CATEGORIES: raise ValueError('등록되지 않은 카테고리입니다.')
    try:
        db.write('INSERT INTO transactions(txn_date,merchant,amount,category,note,source_id) VALUES(?,?,?,?,?,?)',
                 (txn_date,merchant,amount,category,note,source_id))
    except Exception as exc:
        import sqlite3
        if isinstance(exc,sqlite3.IntegrityError) and source_id is not None: return {'status':'duplicate_skipped'}
        raise
    return {'status':'added','date':txn_date,'merchant':merchant,'amount':amount,'category':category}

def set_budget(db, month, category, amount):
    valid_month(month)
    if category not in CATEGORIES and category != '전체': raise ValueError('등록되지 않은 카테고리입니다.')
    amount=int(amount)
    if amount<0: raise ValueError('예산은 0 이상이어야 합니다.')
    db.write('INSERT INTO budgets(month,category,amount) VALUES(?,?,?) ON CONFLICT(month,category) DO UPDATE SET amount=excluded.amount', (month,category,amount))
    return {'month':month,'category':category,'budget':amount}

def summarize(db, month):
    valid_month(month)
    rows=db.rows('SELECT category,COUNT(*) AS count,SUM(amount) AS total FROM transactions WHERE substr(txn_date,1,7)=? GROUP BY category ORDER BY total DESC',(month,))
    budget={x['category']:x['amount'] for x in db.rows('SELECT category,amount FROM budgets WHERE month=?',(month,))}
    total=sum(x['total'] for x in rows)
    return {'month':month,'total':total,'count':sum(x['count'] for x in rows),'by_category':rows,
            'budget':budget,'overall_remaining':budget.get('전체',None)-total if '전체' in budget else None,
            'category_remaining':{c:budget[c]-next((x['total'] for x in rows if x['category']==c),0) for c in budget if c!='전체'}}

def top_merchants(db, month, limit=5):
    valid_month(month)
    limit=max(1,min(int(limit),30))
    return db.rows('SELECT merchant, SUM(amount) total, COUNT(*) count FROM transactions WHERE substr(txn_date,1,7)=? GROUP BY merchant ORDER BY total DESC LIMIT ?', (month,limit))

def compare_months(db, left, right):
    a,b=summarize(db,left),summarize(db,right)
    return {'from':left,'to':right,'from_total':a['total'],'to_total':b['total'],
            'difference':b['total']-a['total'],
            'change_pct':round((b['total']/a['total']-1)*100,2) if a['total'] else None}

def import_csv(db, path):
    path=Path(path).resolve()
    if not path.is_file(): raise FileNotFoundError('CSV 경로를 확인하세요.')
    if path.suffix.lower()!='.csv': raise ValueError('CSV 파일만 지원합니다.')
    added=dupes=errors=0
    # utf-8-sig only; no bank login or remote account connection
    with path.open('r',encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        expected={'date','merchant','amount'}
        if not expected.issubset(reader.fieldnames or []): raise ValueError('CSV에는 date,merchant,amount 열이 필요합니다.')
        for idx,row in enumerate(reader, start=2):
            try:
                identity=hashlib.sha256((str(path)+'|'+str(idx)+'|'+repr(row)).encode()).hexdigest()
                result=add_expense(db,row['date'],row['merchant'],row['amount'],row.get('category') or None,row.get('note') or '', identity)
                if result['status']=='duplicate_skipped': dupes+=1
                else: added+=1
            except (ValueError,KeyError,TypeError): errors+=1
    return {'imported':added,'duplicates_skipped':dupes,'invalid_rows':errors}

TOOLS = {
    'add_expense':add_expense,'set_budget':set_budget,'summarize':summarize,
    'top_merchants':top_merchants,'compare_months':compare_months,'import_csv':import_csv,
}
