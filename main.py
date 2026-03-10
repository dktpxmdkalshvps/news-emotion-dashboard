"""
main.py - 뉴스 감성 분석 파이프라인 v3.0
CLI: python main.py "삼성전자" --pages 3 --sites naver daum hankyung
Web: streamlit run streamlit_app.py
"""
import sys, logging
from datetime import datetime
from crawler   import MultiSiteCrawler
from sentiment import SentimentAnalyzer
from visualizer import DashboardVisualizer
from exporter  import DataExporter
from config    import parse_arguments, create_config_from_args
from logger    import setup_logger, get_logger

app_logger = setup_logger('news_sentiment', logging.INFO, 'logs/app.log')
logger = get_logger('main')


def run_pipeline(config):
    print("\n" + "="*70)
    print(f"  뉴스 감성 분석 파이프라인 시작")
    print(f"  키워드: {config.crawl.keyword}")
    print(f"  시작:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  사이트: {config.crawl.sites} | 페이지: {config.crawl.pages_per_site}")
    print("="*70)

    # STEP 1: 크롤링
    print("\n[STEP 1] 뉴스 수집 중...")
    crawler = MultiSiteCrawler(
        sites=config.crawl.sites,
        headless=config.crawl.headless,
        max_retries=config.crawl.max_retries,
        timeout_sec=config.crawl.timeout_sec,
    )
    df = crawler.crawl_to_df(config.crawl.keyword, config.crawl.pages_per_site)
    if df.empty:
        print("  ✗ 수집 데이터 없음. 종료합니다.")
        return None
    print(f"  ✓ {len(df)}건 수집 완료")

    # STEP 2: 감성 분석
    print("\n[STEP 2] 감성 분석 중...")
    analyzer = SentimentAnalyzer(
        mode=getattr(config, 'analysis_mode', 'lexicon'),
    )
    df    = analyzer.analyze(df)
    stats = analyzer.get_statistics(df)
    print(f"  ✓ 긍정:{stats['positive']}건({stats['pos_ratio']}%)"
          f" | 부정:{stats['negative']}건({stats['neg_ratio']}%)"
          f" | 중립:{stats['neutral']}건")
    print(f"    평균 점수:{stats['avg_score']:+.3f} | 평균 신뢰도:{stats['avg_confidence']:.3f}")

    # STEP 3: 시각화
    print("\n[STEP 3] 대시보드 생성 중...")
    viz  = DashboardVisualizer(keyword=config.crawl.keyword,
                               output_dir=config.visualization.output_dir)
    path = viz.create_dashboard(df)
    print(f"  ✓ {path}")

    # STEP 4: 엑셀 저장
    print("\n[STEP 4] 엑셀 저장 중...")
    exp  = DataExporter(keyword=config.crawl.keyword,
                        output_dir=config.visualization.output_dir)
    xlsx = exp.export(df)
    print(f"  ✓ {xlsx}")

    print("\n" + "="*70)
    print("  파이프라인 완료!")
    print("="*70)
    return df


def main():
    try:
        args   = parse_arguments()
        config = create_config_from_args(args)
        run_pipeline(config)
    except ValueError as e:
        print(f"\n입력 오류: {e}\n"); sys.exit(1)
    except KeyboardInterrupt:
        print("\n중단됨."); sys.exit(0)
    except Exception as e:
        print(f"\n오류: {e}\n"); sys.exit(1)


if __name__ == "__main__":
    main()