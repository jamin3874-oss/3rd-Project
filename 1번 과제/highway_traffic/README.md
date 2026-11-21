# 고속도로 TCS 영업소별 교통량 시계열 분석

- 데이터: 한국도로공사 TCS 영업소별 일간 교통량, 2026-08~2026-10
- 기간: 92일 (원본 행 수는 100개 이상). **시간축의 고유 일자는 92개**임에 유의.
- 주의: 업로드된 `.zip` 파일의 실제 포맷은 gzip이고 원본 CSV는 CP949 인코딩. `zipfile`이 아닌 `gzip`으로 처리.

## 실행 방법

1. Python 3.10 이상 사용
2. `pip install -r requirements.txt`
3. `python analysis.py`
4. 그래프: `figures/`, 보고서: `REPORT.md`, 가공 CSV: `data/` 확인

VS Code에서 폴더를 열어 `analysis.py`를 실행하면 됩니다. 그래프는 PNG 파일로 저장되며 `REPORT.md`가 자동 갱신됩니다.

## 파일 구조

- `source/` 원본 3개(변경 없이 보관)
- `analysis.py` 전체 재현 스크립트
- `REPORT.md` 실제 결과를 포함한 보고서(스크립트 재실행 시 갱신)
- `data/daily_traffic.csv`: 일자별 합계·이동평균·변화율
- `data/station_direction_daily.csv`: 날짜×영업소×입출구코드별 합계 (100개 이상 관측치 확인용)
- `figures/`: 5종 시각화

## 계산/해석 주의

영업소별 진출입 기록의 합계로서 차량 고유대수 또는 특정 고속도로 한 구간의 AADT와 다릅니다. 동일 주행이 여러 영업소 입출구로 중복 집계될 수 있어 수치를 단순히 '전국 고속도로 운행 차량 대수'로 부르지 않습니다. 3개월 92일이므로 '100개 시계열 **시점**'을 요구한다면 7월 등 한 달을 추가 받아야 합니다.

## VS Code 실행 안내

1. VS Code에서 **파일 → 폴더 열기**로 압축을 해제한 폴더를 엽니다.
2. VS Code의 Python 확장을 설치하고 Python 3.10 이상 인터프리터를 선택합니다.
3. 터미널에서 `python -m pip install -r requirements.txt`를 실행합니다.
4. `analysis.py`를 연 뒤 오른쪽 상단 실행 버튼을 누르거나 터미널에서 `python analysis.py`를 실행합니다.
5. 실행 결과는 `figures/`의 PNG 그래프와 `REPORT.md`에 저장됩니다. 원본 데이터는 `source/`에 포함되어 있습니다.

**참고:** 스크립트는 실행 중 그래프 창을 띄우지 않고 PNG로 저장합니다.
