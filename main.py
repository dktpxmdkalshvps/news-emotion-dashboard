"""
main.py - 뉴스 수집 및 감성 분석 대시보드 파이프라인
"""

from crawler import MultiSiteCrawler
from sentiment import SentimentAnalyzer
from visualizer import DashboardVisualizer
from exporter import DataExporter
from datetime import datetime
import os


def run_pipeline(keyword: str, pages_per_site: int = 2, sites: list = None):
    print("=" * 60)
    print(f"  [뉴스 감성 분석 파이프라인 시작] 키워드: {keyword}")
    print(f"  시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 크롤링
    print("\n[STEP 1] 뉴스 수집 중...")
    crawler = MultiSiteCrawler(sites=sites)
    df = crawler.crawl_to_df(keyword=keyword, pages_per_site=pages_per_site)

    if df.empty:
        print("  ! 수집된 데이터가 없습니다. 종료합니다.")
        return None

    print(f"  - 수집 완료: 총 {len(df)}건")

    # 2. 감성 분석
    print("\n[STEP 2] 감성 분석 수행 중...")
    analyzer = SentimentAnalyzer()
    df = analyzer.analyze(df)
    stats = analyzer.get_statistics(df)
    
    print(f"  - 결과 요약: 긍정({stats['positive']}건), 부정({stats['negative']}건), 중립({stats['neutral']}건)")
    print(f"  - 평균 점수: {stats['avg_score']:+.3f}")

    # 3. 시각화 대시보드 생성
    print("\n[STEP 3] 시각화 대시보드 생성 중...")
    viz = DashboardVisualizer(keyword=keyword)
    dashboard_path = viz.create_dashboard(df)
    if dashboard_path:
        print(f"  - 대시보드 저장 완료: {dashboard_path}")

    # 4. 데이터 엑셀 저장
    print("\n[STEP 4] 데이터 엑셀 파일 저장 중...")
    exporter = DataExporter(keyword=keyword)
    excel_path = exporter.export(df)
    if excel_path:
        print(f"  - 엑셀 파일 저장 완료: {excel_path}")

    print("\n" + "=" * 60)
    print("  분석이 성공적으로 완료되었습니다!")
    print("=" * 60)
    return df


if __name__ == "__main__":
    # 분석 설정
    KEYWORD = "삼성전자"  # 분석할 검색어
    PAGES   = 2           # 사이트별 수집 페이지 수
    SITES   = ["naver", "hankyung"]  # 수집할 사이트
    
    run_pipeline(KEYWORD, PAGES, SITES)
