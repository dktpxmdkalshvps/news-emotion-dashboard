## 🚀 News Sentiment Dashboard - 빠른 시작 가이드

---

## 📦 Step 1: 설치

```bash
# 1. 필수 라이브러리 설치
pip install -r requirements.txt

# 또는 conda 사용
conda install -c conda-forge selenium webdriver-manager pandas matplotlib seaborn wordcloud openpyxl
```

---

## 🎯 Step 2: 기본 실행

### 가장 간단한 방법
```bash
python main.py "삼성전자"
```

**출력 결과:**
- `output/삼성전자_dashboard_extended.png` - 5패널 대시보드 (워드클라우드 포함)
- `output/삼성전자_감성분석_YYYYMMDD_HHMMSS.xlsx` - 분석 결과 엑셀

---

## 🎮 Step 3: 다양한 사용법

### 페이지 수 변경 (기본값: 2)
```bash
python main.py "현대차" --pages 5
# 결과: 더 많은 뉴스 수집
```

### 특정 사이트만 크롤링 (기본값: naver hankyung)
```bash
python main.py "카카오" --sites naver
```

### 브라우저 화면 보기 (기본값: headless)
```bash
python main.py "삼성전자" --no-headless
# 크롤링 과정이 브라우저에 표시됨
```

### 디버깅 로그 확인
```bash
python main.py "현대차" --log-level DEBUG
# logs/app.log에 상세 정보 저장
```

### 고급 옵션 조합
```bash
python main.py "CJ제일제당" \
    --pages 5 \
    --sites naver hankyung \
    --timeout 30 \
    --retries 5 \
    --output ./my_results \
    --log-level DEBUG
```

---

## 📚 Step 4: 모든 CLI 옵션 확인

```bash
python main.py --help
```

**출력:**
```
usage: main.py [-h] [--pages PAGES_PER_SITE] [--sites SITES [SITES ...]]
               [--no-headless] [--timeout TIMEOUT] [--retries RETRIES]
               [--log-level {DEBUG,INFO,WARNING,ERROR}] [--no-wordcloud]
               [--output OUTPUT]
               keyword

뉴스 감성 분석 대시보드

positional arguments:
  keyword                분석할 검색 키워드 (예: '삼성전자', '현대차')

optional arguments:
  -h, --help            도움말 표시
  --pages PAGES_PER_SITE, -p PAGES_PER_SITE
                        사이트별 수집 페이지 수 (기본값: 2, 범위: 1-20)
  --sites SITES [SITES ...], -s SITES [SITES ...]
                        크롤링할 사이트 (기본값: naver hankyung)
  --no-headless         브라우저 창을 표시하며 실행
  --timeout TIMEOUT     페이지 로드 타임아웃 (초, 기본값: 20)
  --retries RETRIES     최대 재시도 횟수 (기본값: 3)
  --log-level {DEBUG,INFO,WARNING,ERROR}
                        로깅 레벨 (기본값: INFO)
  --no-wordcloud        워드클라우드 시각화 비활성화
  --output OUTPUT       출력 디렉토리 (기본값: output)
```

---

## 📊 Step 5: 실행 결과 확인

### 콘솔 출력 예
```
======================================================================
  【 뉴스 감성 분석 파이프라인 시작 】
  📌 키워드: 삼성전자
  📅 시작 시간: 2026-03-10 15:45:30
======================================================================

▶ [STEP 1] 뉴스 수집 중...
  ✓ 수집 완료: 총 42건

▶ [STEP 2] 감성 분석 수행 중...
  ✓ 분석 완료
     - 긍정: 18건 (42.9%)
     - 부정: 12건 (28.6%)
     - 중립: 12건 (28.6%)
     - 평균 점수: +0.542
     - 평균 신뢰도: 0.687

▶ [STEP 3] 시각화 대시보드 생성 중...
  ✓ 대시보드 저장 완료: output/삼성전자_dashboard_extended.png

▶ [STEP 4] 데이터 엑셀 파일 저장 중...
  ✓ 엑셀 파일 저장 완료: output/삼성전자_감성분석_20260310_154530.xlsx

======================================================================
  ✓ 분석이 성공적으로 완료되었습니다!
======================================================================
```

### 생성된 파일
```
output/
├── 삼성전자_dashboard_extended.png        # 5패널 대시보드 (워드클라우드 포함)
├── 삼성전자_dashboard.png                 # 기본 4패널 대시보드
└── 삼성전자_감성분석_20260310_154530.xlsx # 분석 결과 엑셀

logs/
└── app.log                                  # 상세 실행 로그
```

### 엑셀 파일 구조
| 시트명 | 내용 |
|--------|------|
| 분석결과 | 모든 뉴스 데이터 (제목, 출처, 감정, 점수, 신뢰도) |
| 긍정뉴스 | 긍정 분류된 뉴스만 |
| 부정뉴스 | 부정 분류된 뉴스만 |
| 중립뉴스 | 중립 분류된 뉴스만 |
| 통계 | 긍정율, 평균 점수, 평균 신뢰도 등 |

---

## 🐛 트러블슈팅

### 문제 1: "No module named 'selenium'"
```bash
# 해결책
pip install selenium webdriver-manager
```

### 문제 2: "타임아웃 오류"
```bash
# 해결책: 타임아웃 시간 증가
python main.py "키워드" --timeout 40
```

### 문제 3: "데이터 수집 없음"
```bash
# 해결책: 다른 키워드 시도 또는 페이지 수 증가
python main.py "다른키워드" --pages 3
```

### 문제 4: "WordCloud 미설치"
```bash
# 해결책
pip install wordcloud
```

---

## 💡 유용한 팁

### Tip 1: 배치 처리 (여러 키워드 분석)
```bash
# keywords.txt 파일 생성 후
for keyword in "삼성전자" "현대차" "카카오"; do
    python main.py "$keyword" --pages 3
done
```

### Tip 2: 고품질 분석 (느리지만 정확)
```bash
python main.py "키워드" --pages 5 --timeout 30 --retries 5 --log-level DEBUG
```

### Tip 3: 빠른 테스트 (속도 우선)
```bash
python main.py "키워드" --pages 1 --timeout 15
```

### Tip 4: 로그 확인
```bash
# 실시간 로그 보기
tail -f logs/app.log

# 또는 notepad에서 열기
notepad logs/app.log
```

---

## 🎓 이해해야 할 개념

### 감성 점수 해석
- **+3.0**: 매우 긍정적
- **+1.0 ~ +2.9**: 긍정적
- **+0.5 ~ +0.9**: 약간 긍정적
- **-0.5 ~ +0.4**: 중립
- **-0.9 ~ -0.5**: 약간 부정적
- **-1.0 ~ -2.9**: 부정적
- **-3.0**: 매우 부정적

### 신뢰도 해석
- **0.9 ~ 1.0**: 매우 높음 (강한 신호)
- **0.7 ~ 0.8**: 높음 (신뢰할 수 있음)
- **0.5 ~ 0.6**: 중간 (참고용)
- **0.0 ~ 0.4**: 낮음 (불확실함)

---

## 🚀 다음 단계

1. **여러 키워드 비교**: 같은 산업 내 기업들 비교
2. **시계열 분석**: 같은 키워드를 주기적으로 분석해 트렌드 추적
3. **감정 사전 확장**: 특정 산업에 맞게 키워드 추가
4. **API 서버화**: Flask/FastAPI로 웹 서비스 제공

---

## 📞 지원

- 🔍 **로그 확인**: `logs/app.log`에서 상세 정보 확인
- 📖 **전체 문서**: `README_v2.md` 참조
- 📋 **개선사항**: `IMPROVEMENTS_SUMMARY.md` 참조

---

**행운을 빕니다! 🎉**
