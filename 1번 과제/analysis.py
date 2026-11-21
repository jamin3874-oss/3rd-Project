"""한국도로공사 TCS 영업소별 교통량 추세 분석 (Python 3.10+).
원본 gzip CSV 3개를 source/ 폴더에 넣고 python analysis.py 실행.
"""
from __future__ import annotations
import csv
import gzip
import math
import statistics
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import dates as mdates, font_manager

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source"
DATA = ROOT / "data"
FIG = ROOT / "figures"
DATA.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

files = [SOURCE / f"TCS_영업소별교통량_1일_1개월_{month}.zip"
         for month in ("202608", "202609", "202610")]
if any(not file.exists() for file in files):
    raise FileNotFoundError("source/ 폴더에 202608, 202609, 202610 원본 파일 3개가 필요합니다.")

for font in font_manager.findSystemFonts():
    if any(k in font for k in ("NanumGothic", "NanumBarun", "NanumSquare")):
        font_manager.fontManager.addfont(font)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=font).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False

dimensions = ("집계일자", "영업소코드", "입출구구분코드", "TCS하이패스구분코드",
              "고속도로운영기관구분코드", "영업형태구분코드")
classes = [f"{n}종교통량" for n in range(1, 7)]
traffic = defaultdict(int)
rows_by_date = Counter()
panel = defaultdict(int)
stations = set()
seen = set()
issues = Counter()
raw_count = 0

for filename in files:
    # 파일 확장자는 zip이지만 내용은 gzip(CP949 CSV)
    with gzip.open(filename, "rt", encoding="cp949", newline="") as stream:
        for row in csv.DictReader(stream):
            raw_count += 1
            try:
                key = tuple(row[col].strip() for col in dimensions)
                if key in seen:
                    issues["duplicates"] += 1
                    continue
                seen.add(key)
                day = date.fromisoformat(row["집계일자"])
                vals = [int(row[col]) for col in classes]
                total = int(row["총교통량"])
                if any(x < 0 for x in vals) or total < 0:
                    issues["negative"] += 1
                    continue
                if sum(vals) != total:
                    issues["class_mismatch"] += 1
                    continue
            except (ValueError, KeyError, TypeError):
                issues["invalid"] += 1
                continue
            station = row["영업소코드"].strip()
            direction = row["입출구구분코드"].strip()
            traffic[day] += total
            rows_by_date[day] += 1
            panel[(day, station, direction)] += total
            stations.add(station)

days = sorted(traffic)
if not days:
    raise ValueError("유효한 교통량이 없습니다.")
missing = [days[0] + timedelta(days=i)
           for i in range((days[-1] - days[0]).days + 1)
           if days[0] + timedelta(days=i) not in traffic]
if missing:
    raise ValueError(f"집계일 누락: {missing}")

values = [traffic[day] for day in days]
def moving_average(numbers, window):
    return [statistics.mean(numbers[i-window+1:i+1]) if i >= window-1
            else math.nan for i in range(len(numbers))]

ma7 = moving_average(values, 7)
ma30 = moving_average(values, 30)
change = [math.nan] + [
    (values[i] / values[i - 1] - 1) * 100 if values[i - 1] else math.nan
    for i in range(1, len(values))]
weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
weekday = defaultdict(list)
monthly = defaultdict(list)
for day, count in zip(days, values):
    weekday[day.weekday()].append(count)
    monthly[day.strftime("%Y-%m")].append(count)
weekday_mean = [statistics.mean(weekday[i]) for i in range(7)]
month_mean = {month: statistics.mean(counts) for month, counts in sorted(monthly.items())}
weekday_all = [v for i in range(5) for v in weekday[i]]
weekend_all = [v for i in (5, 6) for v in weekday[i]]

with (DATA / "daily_traffic.csv").open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(["date", "total_tollgate_records", "record_count", "ma7", "ma30", "day_over_day_pct"])
    for i, day in enumerate(days):
        writer.writerow([day.isoformat(), values[i], rows_by_date[day],
                         "" if math.isnan(ma7[i]) else round(ma7[i], 2),
                         "" if math.isnan(ma30[i]) else round(ma30[i], 2),
                         "" if math.isnan(change[i]) else round(change[i], 3)])

with (DATA / "station_direction_daily.csv").open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(["date", "station_code", "entry_exit_code", "total_traffic"])
    for (day, station, direction), val in sorted(panel.items()):
        writer.writerow([day, station, direction, val])

def save_chart(name):
    plt.tight_layout()
    plt.savefig(FIG / name, dpi=145)
    plt.close()

plt.figure(figsize=(11, 4.5))
plt.plot(days, values, label="일별 교통량")
plt.title("영업소별 TCS 일별 통과건수")
plt.ylabel("통과 집계건수 (건/일)")
plt.grid(alpha=0.2)
plt.gcf().autofmt_xdate()
save_chart("01_daily_trend.png")

plt.figure(figsize=(11, 4.5))
plt.plot(days, values, alpha=.35, label="일별")
plt.plot(days, ma7, label="7일 이동평균")
plt.plot(days, ma30, label="30일 이동평균")
plt.title("TCS 교통량 이동평균")
plt.legend()
plt.grid(alpha=0.2)
plt.gcf().autofmt_xdate()
save_chart("02_moving_averages.png")

plt.figure(figsize=(8.5, 4.5))
plt.bar(weekday_names, weekday_mean)
plt.title("요일별 평균 TCS 교통량")
plt.ylabel("통과 집계건수 (건/일)")
save_chart("03_weekday_pattern.png")

plt.figure(figsize=(11, 4.3))
plt.bar(days, [0 if math.isnan(v) else v for v in change], width=.8)
plt.axhline(0, color="gray", linewidth=.6)
plt.title("전일 대비 교통량 증감률")
plt.ylabel("증감률 (%)")
plt.gcf().autofmt_xdate()
save_chart("04_daily_change.png")

plt.figure(figsize=(8.5, 4.5))
plt.bar(list(month_mean), list(month_mean.values()))
plt.title("월별 일평균 TCS 통과건수")
plt.ylabel("통과 집계건수 (건/일)")
save_chart("05_monthly_means.png")

max_day = max(days, key=traffic.get)
min_day = min(days, key=traffic.get)
mean_week = statistics.mean(weekday_all)
mean_weekend = statistics.mean(weekend_all)
monthly_table = "\n".join(f"| {month} | {avg:,.0f} |" for month, avg in month_mean.items())

report = f"""# 고속도로 TCS 영업소별 교통량 데이터 기반 트렌드 분석

## 1. 분석 목적
한국도로공사 TCS 영업소별 일별 통과 집계건수를 이용해 일별 변화, 이동평균, 요일별 특성, 월별 차이를 확인한다.

## 2. 원본 및 분석 범위
- 출처: 한국도로공사 고속도로 공공데이터포털 https://data.ex.co.kr
- 기간: {days[0]} ~ {days[-1]} ({len(days)}일)
- 원본: {raw_count:,}행, 영업소 코드 {len(stations)}개, 날짜·영업소·입출구 관측치 {len(panel):,}개
- 주의: 일별 시점은 {len(days)}개이므로 최소 100개 날짜가 필수면 추가 월 데이터가 필요함.

## 3. 전처리
- CP949 인코딩 gzip CSV 3개를 읽고 날짜 및 수치 자료형 변환
- 키 중복 {issues["duplicates"]}건, 음수 {issues["negative"]}건, 오류/결측 {issues["invalid"]}건, 차종 합계 불일치 {issues["class_mismatch"]}건
- 날짜 누락 {len(missing)}일
- 7일·30일 이동평균과 전일 대비 증감률 계산 (초기 값은 미계산)
- 관측된 급격한 변화는 오류 여부가 검증되지 않아 자동 삭제하지 않음

## 4. 주요 분석 결과
| 항목 | 값 |
|---|---:|
| 일평균 통과 집계건수 | {statistics.mean(values):,.0f}건 |
| 최대 일별 집계 | {max_day}: {traffic[max_day]:,}건 |
| 최소 일별 집계 | {min_day}: {traffic[min_day]:,}건 |
| 평일 일평균 | {mean_week:,.0f}건 |
| 주말 일평균 | {mean_weekend:,.0f}건 |
| 주말/평일 차이 | {(mean_weekend / mean_week - 1) * 100:+.2f}% |

### 월별 평균
| 월 | 일평균 집계건수 |
|---|---:|
{monthly_table}

### 그림
![일별](figures/01_daily_trend.png)
![이동평균](figures/02_moving_averages.png)
![요일](figures/03_weekday_pattern.png)
![증감률](figures/04_daily_change.png)
![월별](figures/05_monthly_means.png)

## 5. 데이터 기반 인사이트
- 평일과 주말의 평균 통과량 차이는 {(mean_weekend / mean_week - 1) * 100:+.2f}%다. 원인이 출퇴근·관광 수요라는 해석은 추가 통행 목적 자료 없이는 검증되지 않는다.
- 일별 차이는 요일·연휴·집계대상 변동 등의 영향을 받을 수 있다. 원인 분석을 위해 기상·휴일 자료가 필요하다.
- 3개월만으로 계절성이나 장기 증가세를 단정할 수 없다.

## 6. 해석의 한계와 보완
- 영업소 입출구 통과건수 합산은 차량 고유대수나 특정 고속도로 구간 AADT가 아니다.
- 일별 92개 시점이므로 100개 이상 날짜를 요구하는 경우 2026년 7월 자료를 추가해야 한다.
- 같은 차량이 입구와 출구에 각각 기록될 수 있다.

## 7. 재현 방법
`pip install -r requirements.txt` 후 `python analysis.py` 실행.
"""
(ROOT / "REPORT.md").write_text(report, encoding="utf-8")
print(f"분석 완료: {len(days)}일, 원본 {raw_count:,}행, 그래프 5개")
