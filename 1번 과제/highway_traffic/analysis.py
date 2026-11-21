"""한국도로공사 TCS 영업소별 교통량 추세 분석. Python 3.10+, matplotlib.
Run: python analysis.py
"""
from __future__ import annotations
import csv, gzip, statistics, math, calendar, datetime as dt
from collections import defaultdict, Counter
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager, dates as mdates

ROOT = Path(__file__).resolve().parent
SRC, DATA, FIG = ROOT/'source', ROOT/'data', ROOT/'figures'
for folder in (DATA, FIG): folder.mkdir(exist_ok=True)
FILES = sorted(SRC.glob('TCS_영업소별교통량_1일_1개월_2026*.zip'))
if len(FILES) != 3: raise RuntimeError('source 폴더에 202608, 202609, 202610 원본 3개가 있어야 합니다.')
for path in font_manager.findSystemFonts():
    if 'NanumGothic' in path or 'NanumBarun' in path or 'NanumSquare' in path:
        font_manager.fontManager.addfont(path)
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=path).get_name()
        break
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 145

DIM=['집계일자','영업소코드','입출구구분코드','TCS하이패스구분코드','고속도로운영기관구분코드','영업형태구분코드']
VEH=[f'{i}종교통량' for i in range(1,7)]
DAILY=defaultdict(lambda: {'total':0,'rows':0,'types':[0]*6,'dirs':defaultdict(int),'stations':set()})
PANEL=defaultdict(int)
seen=set(); all_dates=set(); invalid=Counter(); counts=Counter(); code_counts=Counter(); n=0; mismatch=0
for path in FILES:
    with gzip.open(path,'rt',encoding='cp949',newline='') as f:
        for row in csv.DictReader(f):
            n+=1
            try:
                day=dt.date.fromisoformat(row['집계일자'])
                key=tuple(row[k].strip() for k in DIM)
                if key in seen: invalid['duplicate_key']+=1; continue
                seen.add(key)
                code=row['영업소코드'].strip()
                typ=[int(row[k]) for k in VEH]
                total=int(row['총교통량'])
                if total<0 or any(x<0 for x in typ): invalid['negative_count']+=1;continue
                if sum(typ)!=total: mismatch+=1
            except (ValueError,TypeError,KeyError):
                invalid['invalid_or_missing']+=1
                continue
            all_dates.add(day)
            rec=DAILY[day]
            rec['total']+=total; rec['rows']+=1;rec['stations'].add(code)
            rec['dirs'][row['입출구구분코드']]+=total
            for i,x in enumerate(typ):rec['types'][i]+=x
            PANEL[(day,code,row['입출구구분코드'])]+=total
            counts[(day,code)]+=1
            code_counts[row['입출구구분코드']]+=1
DAYS=sorted(DAILY)
expected=[DAYS[0]+dt.timedelta(days=i) for i in range((DAYS[-1]-DAYS[0]).days+1)]
missing=sorted(set(expected)-set(DAYS))
if missing: raise RuntimeError(f'날짜 누락: {missing}')
assert DAYS[0]==dt.date(2026,8,1) and DAYS[-1]==dt.date(2026,10,31)

series=[DAILY[d]['total'] for d in DAYS]
def moving_avg(values,window):
    return [sum(values[i-window+1:i+1])/window if i>=window-1 else math.nan for i in range(len(values))]
ma7=moving_avg(series,7);ma30=moving_avg(series,30)
changes=[math.nan]+[(series[i]/series[i-1]-1)*100 if series[i-1]!=0 else math.nan for i in range(1,len(series))]
weekdays=['월','화','수','목','금','토','일']
weekday_vals=defaultdict(list)
monthly=defaultdict(list)
for day,val in zip(DAYS,series):
    weekday_vals[day.weekday()].append(val)
    monthly[day.strftime('%Y-%m')].append(val)
wk_avg={i:statistics.mean(weekday_vals[i]) for i in range(7)}
month_avg={m:statistics.mean(vals) for m,vals in sorted(monthly.items())}
# 이전 7일 중앙값과 비교한 설명적 이상징후 플래그. 데이터 삭제/보정하지 않음.
flags=[]
for i in range(7,len(series)):
    prev=series[i-7:i]
    med=statistics.median(prev)
    if med and abs(series[i]/med-1)>=0.25:
        flags.append((DAYS[i],series[i],(series[i]/med-1)*100))

with (DATA/'daily_traffic.csv').open('w',encoding='utf-8-sig',newline='') as f:
    wr=csv.writer(f);wr.writerow(['date','total_tollgate_records','row_count','distinct_station_count','dir_0','dir_1','class_1','class_2','class_3','class_4','class_5','class_6','ma7','ma30','day_over_day_pct'])
    for i,d in enumerate(DAYS):
        r=DAILY[d]
        wr.writerow([d.isoformat(),r['total'],r['rows'],len(r['stations']),r['dirs']['0'],r['dirs']['1'],*r['types'],'' if math.isnan(ma7[i]) else round(ma7[i],2),'' if math.isnan(ma30[i]) else round(ma30[i],2),'' if math.isnan(changes[i]) else round(changes[i],3)])
with (DATA/'station_direction_daily.csv').open('w',encoding='utf-8-sig',newline='') as f:
    wr=csv.writer(f); wr.writerow(['date','station_code','entry_exit_code','total_traffic'])
    for (day,code,direction),value in sorted(PANEL.items()):wr.writerow([day,code,direction,value])

x=DAYS
# 단위는 영업소 입출구 통과 집계건수. 실제 차량 고유대수/특정 도로 AADT와 다름.
fig,ax=plt.subplots(figsize=(11.2,4.4)); ax.plot(x,series,lw=1.8,label='일별 집계건수');ax.set_title('2026년 8~10월 영업소별 TCS 일별 합산 추이');ax.set_ylabel('통과 집계건수 (건/일)');ax.grid(alpha=.22);ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'));ax.legend();fig.autofmt_xdate();fig.tight_layout();fig.savefig(FIG/'01_daily_trend.png');plt.close(fig)
fig,ax=plt.subplots(figsize=(11.2,4.4));ax.plot(x,series,alpha=.3,lw=1,label='일별');ax.plot(x,ma7,lw=2,label='7일 이동평균');ax.plot(x,ma30,lw=2.3,label='30일 이동평균');ax.set_title('TCS 일별 교통량과 이동평균');ax.set_ylabel('통과 집계건수 (건/일)');ax.grid(alpha=.22);ax.legend();fig.autofmt_xdate();fig.tight_layout();fig.savefig(FIG/'02_moving_averages.png');plt.close(fig)
fig,ax=plt.subplots(figsize=(8.7,4.7));ax.bar(weekdays,[wk_avg[i] for i in range(7)]);ax.set_title('요일별 평균 영업소 TCS 교통량');ax.set_ylabel('평균 통과 집계건수 (건/일)');ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(FIG/'03_weekday_pattern.png');plt.close(fig)
fig,ax=plt.subplots(figsize=(11.2,4.1));ax.bar(x,[0 if math.isnan(z) else z for z in changes],width=.8);ax.axhline(0,color='grey',lw=.7);ax.set_title('전일 대비 교통량 증감률');ax.set_ylabel('증감률 (%)');ax.grid(axis='y',alpha=.2);fig.autofmt_xdate();fig.tight_layout();fig.savefig(FIG/'04_daily_change.png');plt.close(fig)
fig,ax=plt.subplots(figsize=(8.7,4.7));mons=list(month_avg);ax.bar(mons,[month_avg[k] for k in mons]);ax.set_title('월별 일평균 TCS 영업소 집계 교통량');ax.set_ylabel('통과 집계건수 (건/일)');ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(FIG/'05_monthly_means.png');plt.close(fig)

minidx=min(range(len(series)),key=series.__getitem__);maxidx=max(range(len(series)),key=series.__getitem__)
week_mean=statistics.mean([v for k in range(5) for v in weekday_vals[k]])
weekend_mean=statistics.mean([v for k in [5,6] for v in weekday_vals[k]])
month_change=(month_avg['2026-10']/month_avg['2026-08']-1)*100
period_change=(statistics.mean(series[-7:])/statistics.mean(series[:7])-1)*100
hivalid=[(i,v) for i,v in enumerate(changes) if not math.isnan(v)]
up=max(hivalid,key=lambda t:t[1]);down=min(hivalid,key=lambda t:t[1])
station_count=len({key[1] for key in PANEL})
num_panel=len(PANEL)

def fm(v):return f'{v:,.0f}'
def pct(v):return f'{v:+.2f}%'
flagstr='\n'.join(f'| {d} | {fm(v)} | {pct(ch)} |' for d,v,ch in flags[:20]) or '| 없음 | - | - |'
notes='''\n### 해석할 때 주의할 점\n- **이 데이터는 구간 교통량(AADT)이나 서로 다른 차량의 고유대수가 아닙니다.** 영업소별 TCS 입·출구 집계의 합이며 동일 운행이 입구와 출구에서 각각 기록될 가능성이 있습니다. 따라서 단순 합계를 ‘전국 고속도로 이용 차량 수’로 해석하지 않습니다.\n- 운영기관 구분·영업형태 코드가 혼합되어 있으며, 영업소 수가 달라질 수 있습니다. 일별 합계 변화에는 집계 대상 또는 운영조건 차이가 일부 포함될 수 있습니다.\n- 92일의 일별 시계열만으로 계절성이나 장기적 증가 추세를 확정할 수 없습니다.\n- 수치 이상징후는 자동 제거하지 않았습니다. 연휴·행사·운영 변화 등 외부 원인은 별도 자료로 검증해야 합니다.\n'''
report=f'''# 고속도로 TCS 영업소별 교통량 데이터 기반 트렌드 분석\n\n## 1. 연구 목적과 개요\n2026년 8~10월 한국도로공사 TCS 영업소별 일간 교통량 원본을 이용해 일별 변화, 이동평균, 요일 특성, 월별 평균을 파악한다. 본 분석은 **영업소 통과 집계건수의 추세**를 대상으로 하며 도로 구간 단면 교통량 또는 차량 고유대수 분석과 구분한다.\n\n## 2. 데이터 출처 및 구조\n- 출처: 사용자가 한국도로공사 고속도로 공공데이터포털에서 직접 내려받은 `TCS_영업소별교통량_1일_1개월_202608.zip`, `202609.zip`, `202610.zip` (원본명은 `.zip`이지만 내부 포맷은 **gzip 압축된 CP949 CSV**).\n- 분석 기간: **{DAYS[0]} ~ {DAYS[-1]} ({len(DAYS)}일)**, 날짜 누락 **{len(missing)}일**.\n- 원본 관측치: **{n:,}행**; 분석 가능한 패널: **{num_panel:,}개의 날짜×영업소×입출구 코드별 집계 단위**; 구분되는 영업소 코드 **{station_count}개**.\n- 열: 집계일자, 영업소코드, 입출구구분코드, TCS하이패스구분코드, 고속도로운영기관구분코드, 영업형태구분코드, 1~6종교통량, 총교통량.\n- 과제의 100개 이상 데이터 포인트 조건은 **원본 {n:,}행/패널 {num_panel:,}개**로 충족한다. 단, **집계 후 일별 시점은 92개뿐**임을 명시한다. 과제에서 ‘시간축 100개 이상’을 요구한다면 이 데이터 3개월만으로 불충분하므로 2026년 7월이나 11월 등 다른 1개월을 추가해야 한다.\n\n## 3. 전처리 및 품질 점검\n1. 압축 형식을 gzip으로 인식하고 CP949 문자 인코딩으로 읽었다.\n2. 날짜를 ISO 날짜로 변환하고, 영업소 코드는 문자열로 보존하여 선행 0을 유지했다.\n3. 고유 키(일자, 영업소, 입출구, TCS/하이패스, 운영기관, 영업형태) 중복 **{invalid['duplicate_key']:,}건**, 음수 **{invalid['negative_count']:,}건**, 누락·형식오류 **{invalid['invalid_or_missing']:,}건**.\n4. 1~6종 합계와 총교통량 불일치 **{mismatch:,}건**. 누락 날짜 **{len(missing)}일**.\n5. 집계 단위를 보존하기 위해 날짜별 `총교통량`을 합산하고, 변화율·7일·30일 이동평균을 계산했다. 이동평균 시작 구간의 값은 **미계산(빈칸)**으로 남겨 임의 보간하지 않았다.\n6. 이상징후는 각 날짜 직전 7일 중앙값 대비 ±25% 이상 변화할 때 **검토 플래그**로 표시했다. 변동을 오류로 단정하거나 삭제하지 않았다.\n\n## 4. 분석 결과\n\n| 항목 | 결과 |\n|---|---:|\n| 기간 전체 영업소 통과 합산 집계건수 | {fm(sum(series))}건 |\n| 일평균 집계건수 | {fm(statistics.mean(series))}건/일 |\n| 최대 일별 집계 | {DAYS[maxidx]}, {fm(series[maxidx])}건 |\n| 최소 일별 집계 | {DAYS[minidx]}, {fm(series[minidx])}건 |\n| 평일 일평균 | {fm(week_mean)}건/일 |\n| 주말 일평균 | {fm(weekend_mean)}건/일 |\n| 주말/평일 평균 차이 | {pct((weekend_mean/week_mean-1)*100)} |\n| 8월 일평균 | {fm(month_avg['2026-08'])}건/일 |\n| 9월 일평균 | {fm(month_avg['2026-09'])}건/일 |\n| 10월 일평균 | {fm(month_avg['2026-10'])}건/일 |\n| 8→10월 일평균 변화 | {pct(month_change)} |\n| 최초 7일 대비 최종 7일 평균 변화 | {pct(period_change)} |\n| 최대 전일 대비 증가 | {DAYS[up[0]]}, {pct(up[1])} |\n| 최대 전일 대비 감소 | {DAYS[down[0]]}, {pct(down[1])} |\n\n### 4.1 일별 원자료 추이\n![일별 합산 추이](figures/01_daily_trend.png)\n\n### 4.2 이동평균으로 본 단기 변화\n![7일·30일 이동평균](figures/02_moving_averages.png)\n\n7일 이동평균은 주간 변동을 완화하고, 30일 이동평균은 상대적으로 완만한 흐름을 보여준다. 실제 차이가 유의한지는 추가 시계열/통계분석이 필요하다.\n\n### 4.3 요일별 특성\n![요일별 평균](figures/03_weekday_pattern.png)\n\n요일별 평균에서 최고 요일은 **{weekdays[max(wk_avg,key=wk_avg.get)]}요일**({fm(max(wk_avg.values()))}건/일), 최저 요일은 **{weekdays[min(wk_avg,key=wk_avg.get)]}요일**({fm(min(wk_avg.values()))}건/일)이다. 표본은 3개월에 한정되며 공휴일 효과를 통제하지 않았다.\n\n### 4.4 단기 변동률\n![전일 대비 증감률](figures/04_daily_change.png)\n\n### 4.5 월별 평균\n![월별 일평균](figures/05_monthly_means.png)\n\n## 5. 이상징후 점검(삭제 없이 보존)\n직전 7일 중앙값 대비 변동폭 ±25% 이상의 **탐색용 플래그 {len(flags)}건**. 이 규칙은 통계적 이상치 확정 기준이 아니라 검토 대상 선별 규칙이다. 아래는 최대 20건이다.\n\n| 날짜 | 일별 집계건수 | 직전 7일 중앙값 대비 |\n|---|---:|---:|\n{flagstr}\n\n## 6. AI 보조 해석과 인사이트\n- **관측:** 주말 평균은 평일 평균 대비 **{pct((weekend_mean/week_mean-1)*100)}** 차이가 난다. **해석:** 출퇴근과 주말 이동 수요의 차이가 반영되었을 가능성이 있지만, 통행 목적 데이터가 없어 원인을 확정할 수 없다.\n- **관측:** 8월 대비 10월 일평균 집계건수 차이는 **{pct(month_change)}**다. **해석:** 월별 일수 차이를 피하고자 총합이 아닌 **일평균**을 비교했다. 3개월 비교이므로 장기적인 성장 또는 감소 추세라고 단정하지 않는다.\n- **관측:** 최댓값 날짜는 **{DAYS[maxidx]}**, 최솟값 날짜는 **{DAYS[minidx]}**다. **가설:** 연휴나 지역·관광 수요가 영향을 줄 수 있지만 기상청 강수량·휴일 캘린더·도로 운영 이력을 결합하기 전에는 검증되지 않는다.\n- **활용 방안:** 영업소 통과량의 요일별 차이가 반복되는지 추가 월·연도 데이터로 검증하고, 영업소별로 분리해 혼잡 대응 인력·시설 운영의 기초지표로 활용할 수 있다.\n\n## 7. 한계 및 개선 방향\n{notes}\n- 더 강한 분석을 위해 **2026년 7월 자료를 추가**하면 일별 시간점 123개로 확장되어 최소 100개 시점 조건도 안전하게 만족시킬 수 있다.\n- 공휴일, 강우량, 노선 ID와 영업소 명칭 매핑이 없어 원인분석·노선별 분석은 수행하지 않았다.\n- 실제 교통량 예측이나 인과 추론은 기본 과제 범위에 포함하지 않았다.\n\n## 8. 재현 방법 및 파일\n`python -m pip install -r requirements.txt` 다음 `python analysis.py` 실행.\n\n- 원본: `source/*.zip` (gzip 포맷)\n- 정제 집계: `data/daily_traffic.csv` (UTF-8 BOM), `data/station_direction_daily.csv`\n- 시각화: `figures/*.png`\n- Python: `analysis.py`\n\n## 9. 출처\n1. 한국도로공사 고속도로 공공데이터포털(`https://data.ex.co.kr`), 영업소별 교통량(TCS) 1일·1개월, 2026년 8~10월 사용자가 제공한 원본 3건.\n2. 공공데이터포털 한국도로공사 관련 자료(집계 필드 설명 확인): https://www.data.go.kr/data/15062176/fileData.do. 단, 본 보고서의 수치는 **위의 사용자 제공 원본 3건을 직접 계산한 결과**임.\n'''
(ROOT/'REPORT.md').write_text(report,encoding='utf-8')
print('원본 행',n,'날짜',len(DAYS),'station-direction-date',num_panel,'영업소',station_count)
print('요일별',wk_avg)
print('월별',month_avg)
print('주말평일',weekend_mean,week_mean)
print('최대 최소',DAYS[maxidx],series[maxidx],DAYS[minidx],series[minidx]);print('그래프',len(list(FIG.glob('*.png'))),'flags',len(flags))
