"""
config.py - 프로젝트 설정 관리 시스템
사용자 입력 검증, 기본값 설정, 환경 변수 통합
"""

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List


@dataclass
class CrawlConfig:
    """크롤링 설정"""
    keyword: str
    pages_per_site: int = 2
    sites: List[str] = None
    headless: bool = True
    timeout_sec: int = 20
    max_retries: int = 3
    retry_delay_sec: float = 2.0
    
    def __post_init__(self):
        if self.sites is None:
            self.sites = ["naver", "hankyung"]
        # 입력 검증
        if not self.keyword or len(self.keyword.strip()) == 0:
            raise ValueError("키워드는 필수 입력 항목입니다.")
        if self.pages_per_site < 1 or self.pages_per_site > 20:
            raise ValueError("페이지 수는 1-20 사이여야 합니다.")
        if not self.sites:
            raise ValueError("최소 1개 이상의 사이트를 선택해야 합니다.")


@dataclass
class SentimentConfig:
    """감성 분석 설정"""
    pos_threshold: float = 0.5
    neg_threshold: float = -0.5
    enable_compound_words: bool = True
    enable_intensifiers: bool = True
    negation_context_window: int = 15  # 부정어 검색 범위 (문자 수)


@dataclass
class VisualizationConfig:
    """시각화 설정"""
    dash_width: int = 16
    dash_height: int = 10
    dpi: int = 150
    enable_wordcloud: bool = True
    wordcloud_max_words: int = 100
    output_dir: str = "output"


@dataclass
class AppConfig:
    """전체 애플리케이션 설정"""
    crawl: CrawlConfig
    sentiment: SentimentConfig = None
    visualization: VisualizationConfig = None
    
    def __post_init__(self):
        if self.sentiment is None:
            self.sentiment = SentimentConfig()
        if self.visualization is None:
            self.visualization = VisualizationConfig()


def parse_arguments() -> argparse.Namespace:
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="뉴스 감성 분석 대시보드",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python main.py "삼성전자" --pages 3 --sites naver hankyung
  python main.py "현대차" --pages 2 --sites naver
  python main.py "카카오" --no-headless  # 브라우저 화면 표시
        """
    )
    
    parser.add_argument(
        "keyword",
        type=str,
        help="분석할 검색 키워드 (예: '삼성전자', '현대차')"
    )
    
    parser.add_argument(
        "--pages", "-p",
        type=int,
        default=2,
        dest="pages_per_site",
        help="사이트별 수집 페이지 수 (기본값: 2, 범위: 1-20)"
    )
    
    parser.add_argument(
        "--sites", "-s",
        type=str,
        nargs="+",
        default=["naver", "hankyung"],
        help="크롤링할 사이트 (기본값: naver hankyung)"
    )
    
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="브라우저 창을 표시하며 실행 (기본값: headless 모드)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="페이지 로드 타임아웃 (초, 기본값: 20)"
    )
    
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="최대 재시도 횟수 (기본값: 3)"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="로깅 레벨 (기본값: INFO)"
    )
    
    parser.add_argument(
        "--no-wordcloud",
        action="store_false",
        dest="enable_wordcloud",
        help="워드클라우드 시각화 비활성화"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="output",
        help="출력 디렉토리 (기본값: output)"
    )
    
    return parser.parse_args()


def create_config_from_args(args: argparse.Namespace) -> AppConfig:
    """CLI 인자에서 설정 객체 생성"""
    crawl_config = CrawlConfig(
        keyword=args.keyword,
        pages_per_site=args.pages_per_site,
        sites=args.sites,
        headless=args.headless,
        timeout_sec=args.timeout,
        max_retries=args.retries,
    )
    
    viz_config = VisualizationConfig(
        enable_wordcloud=args.enable_wordcloud,
        output_dir=args.output,
    )
    
    return AppConfig(
        crawl=crawl_config,
        visualization=viz_config,
    )


def save_config_to_file(config: AppConfig, filepath: str) -> None:
    """설정을 JSON 파일로 저장"""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        config_dict = {
            'crawl': asdict(config.crawl),
            'sentiment': asdict(config.sentiment),
            'visualization': asdict(config.visualization),
        }
        json.dump(config_dict, f, ensure_ascii=False, indent=2)


def load_config_from_file(filepath: str) -> AppConfig:
    """JSON 파일에서 설정 로드"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    crawl = CrawlConfig(**data['crawl'])
    sentiment = SentimentConfig(**data['sentiment'])
    visualization = VisualizationConfig(**data['visualization'])
    
    return AppConfig(
        crawl=crawl,
        sentiment=sentiment,
        visualization=visualization,
    )
