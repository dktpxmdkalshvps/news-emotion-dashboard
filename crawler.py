"""
crawler.py - 3대 뉴스 사이트 통합 크롤러 v3.0
BaseCrawler → NaverCrawler / DaumCrawler / HankyungCrawler → MultiSiteCrawler
재시도 로직, 에러 처리, 상세 로깅 포함
"""
from __future__ import annotations

import time
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import quote_plus
from typing import Optional, List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    _USE_WDM = True
except ImportError:
    _USE_WDM = False

from logger import get_logger
logger = get_logger('crawler')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  데이터 클래스
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@dataclass
class NewsItem:
    title:      str
    press:      str
    pub_time:   str
    url:        str
    source:     str
    crawled_at: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    def to_dict(self) -> dict:
        return {
            "title":      self.title,
            "press":      self.press,
            "pub_time":   self.pub_time,
            "url":        self.url,
            "source":     self.source,
            "crawled_at": self.crawled_at,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  드라이버 팩토리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def build_driver(headless: bool = True) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if _USE_WDM:
        service = Service(ChromeDriverManager().install())
        driver  = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  추상 베이스 클래스
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class BaseCrawler(ABC):
    """
    공통 인터페이스 – 사이트별 크롤러가 상속

    추상 메서드:
      build_url(keyword, page)  → str
      parse_page(driver)        → list[NewsItem]

    공통 엔진:
      crawl(keyword, pages)     → list[NewsItem]  (재시도 포함)
    """
    SITE_NAME: str = ""
    SITE_KEY:  str = ""

    def __init__(self, headless: bool = True, wait_sec: int = 20,
                 max_retries: int = 3, retry_delay_sec: float = 2.0):
        self.headless        = headless
        self.wait_sec        = wait_sec
        self.max_retries     = max_retries
        self.retry_delay_sec = retry_delay_sec
        self._err_count      = 0

    @abstractmethod
    def build_url(self, keyword: str, page: int) -> str: ...

    @abstractmethod
    def parse_page(self, driver: webdriver.Chrome) -> list: ...

    # ── 공통 크롤링 엔진 ──────────────────────────────────────────────
    def crawl(self, keyword: str, pages: int = 2) -> list:
        results = []
        for page in range(1, pages + 1):
            items = self._crawl_with_retry(keyword, page, pages)
            results.extend(items)
            if page < pages:
                time.sleep(random.uniform(1.0, 2.0))
        logger.info(f"[{self.SITE_NAME}] 완료: {len(results)}건 (오류 {self._err_count}회)")
        return results

    def _crawl_with_retry(self, keyword: str, page: int, total: int) -> list:
        url = self.build_url(keyword, page)
        for attempt in range(1, self.max_retries + 1):
            driver = None
            try:
                logger.debug(f"[{self.SITE_NAME}] {page}/{total}p 시도 {attempt}/{self.max_retries}")
                driver = build_driver(self.headless)
                driver.get(url)
                WebDriverWait(driver, self.wait_sec).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                )
                time.sleep(1.2)  # JS 렌더링 대기
                items = self.parse_page(driver)
                if items:
                    logger.debug(f"[{self.SITE_NAME}] {len(items)}건 수집")
                return items
            except TimeoutException:
                self._err_count += 1
                logger.warning(f"[{self.SITE_NAME}] 타임아웃 (시도 {attempt})")
            except (WebDriverException, Exception) as e:
                self._err_count += 1
                logger.warning(f"[{self.SITE_NAME}] 오류: {e} (시도 {attempt})")
            finally:
                if driver:
                    try: driver.quit()
                    except: pass
            if attempt < self.max_retries:
                time.sleep(self.retry_delay_sec * attempt)
        logger.error(f"[{self.SITE_NAME}] 최대 재시도 실패: {url}")
        return []

    # ── 헬퍼 ─────────────────────────────────────────────────────────
    @staticmethod
    def safe_text(el, css: str, default: str = "") -> str:
        try:
            return el.find_element(By.CSS_SELECTOR, css).text.strip()
        except NoSuchElementException:
            return default

    @staticmethod
    def safe_attr(el, css: str, attr: str, default: str = "") -> str:
        try:
            return el.find_element(By.CSS_SELECTOR, css).get_attribute(attr) or default
        except NoSuchElementException:
            return default


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  구현체 1 – 네이버 뉴스
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class NaverCrawler(BaseCrawler):
    """
    네이버 뉴스 검색 크롤러
    URL: search.naver.com/search.naver?where=news&query={kw}&start={start}&sort=1
    페이지네이션: start = (page-1)*10 + 1
    주요 셀렉터: a.news_tit / a.info.press / span.info
    """
    SITE_NAME = "네이버"
    SITE_KEY  = "naver"

    def build_url(self, keyword: str, page: int) -> str:
        start = (page - 1) * 10 + 1
        return (f"https://search.naver.com/search.naver"
                f"?where=news&query={quote_plus(keyword)}&start={start}&sort=1")

    def parse_page(self, driver) -> list:
        items = []
        cards = []
        for sel in ["li.bx", "ul.list_news > li", "div.news_wrap"]:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(cards) > 3:
                break
        for card in cards:
            try:
                title_el = card.find_element(By.CSS_SELECTOR, "a.news_tit")
                title = title_el.text.strip()
                url   = title_el.get_attribute("href") or ""
                if not title:
                    continue
                press    = self.safe_text(card, "a.info.press") or self.safe_text(card, "a.press") or "네이버"
                pub_time = self._time(card)
                items.append(NewsItem(title, press, pub_time, url, self.SITE_KEY))
            except Exception:
                continue
        return items

    @staticmethod
    def _time(card) -> str:
        spans = card.find_elements(By.CSS_SELECTOR, "span.info")
        for s in spans:
            t = s.text.strip()
            if any(k in t for k in ["전", ".", "시간", "일"]):
                return t
        return spans[-1].text.strip() if spans else ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  구현체 2 – 다음 뉴스  ★ NEW ★
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class DaumCrawler(BaseCrawler):
    """
    다음(Daum) 뉴스 검색 크롤러

    검색 URL:
      https://search.daum.net/search?w=news&q={kw}&p={page}&sort=recency

    뉴스 메인 URL (카테고리 탐색용):
      https://news.daum.net/

    페이지네이션: p 파라미터 (1, 2, 3 …)

    주요 셀렉터 (다음은 구조가 자주 변경되므로 다중 후보 적용):
      목록  li.g_item  /  div.cont_inner  /  li[data-docid]
      제목  a.tit_main  /  a.link_txt  /  a.item-title  /  strong.tit_g > a
      언론사  span.name_cp  /  span.txt_cp
      시간  span.num_date  /  span.date_txt
    """
    SITE_NAME = "다음"
    SITE_KEY  = "daum"

    # 검색 결과 URL
    _SEARCH_URL = (
        "https://search.daum.net/search"
        "?w=news&q={kw}&p={page}&spacing=0&sort=recency"
    )

    def build_url(self, keyword: str, page: int) -> str:
        return self._SEARCH_URL.format(kw=quote_plus(keyword), page=page)

    def parse_page(self, driver) -> list:
        items = []

        # ── 다양한 레이아웃 대응: 3가지 카드 셀렉터 시도 ──────────────
        cards = []
        card_selectors = [
            "li.g_item",            # 최신 다음 검색 뉴스 구조
            "li[data-docid]",       # 구형 다음 구조
            "div.cont_inner",       # 대안
            "li.f_fb",              # 또 다른 변형
        ]
        for sel in card_selectors:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 2:
                cards = found
                logger.debug(f"[다음] 카드 셀렉터 '{sel}' 매칭 {len(found)}건")
                break

        for card in cards:
            # 제목 추출 (우선순위 순)
            title_el = None
            title_selectors = [
                "a.tit_main",
                "a.link_txt",
                "a.item-title",
                "strong.tit_g > a",
                "a.tit_g",
                "a[class*='tit']",
            ]
            for ts in title_selectors:
                try:
                    title_el = card.find_element(By.CSS_SELECTOR, ts)
                    if title_el.text.strip():
                        break
                except NoSuchElementException:
                    continue

            if title_el is None:
                continue

            title = title_el.text.strip()
            url   = title_el.get_attribute("href") or ""
            if not title:
                continue

            # 언론사
            press = (
                self.safe_text(card, "span.name_cp")
                or self.safe_text(card, "span.txt_cp")
                or self.safe_text(card, "span.info_txt")
                or "다음뉴스"
            )

            # 게시 시간
            pub_time = (
                self.safe_text(card, "span.num_date")
                or self.safe_text(card, "span.date_txt")
                or self.safe_text(card, "span.info_date")
                or self.safe_attr(card, "span.num_date", "title")
            )

            items.append(NewsItem(title, press, pub_time, url, self.SITE_KEY))

        # 결과가 없으면 페이지 소스 경고 (디버그용)
        if not items:
            logger.debug(f"[다음] 파싱 결과 없음. 현재 URL: {driver.current_url[:80]}")

        return items


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  구현체 3 – 한국경제
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class HankyungCrawler(BaseCrawler):
    """
    한국경제(hankyung.com) 뉴스 검색 크롤러
    URL: hankyung.com/search/?query={kw}&page={page}
    주요 셀렉터: h3.title a / a.tit / .news-tit
    특징: 경제/산업 전문 용어 풍부 → 감성 사전 적중률 높음
    """
    SITE_NAME = "한국경제"
    SITE_KEY  = "hankyung"

    def build_url(self, keyword: str, page: int) -> str:
        return (f"https://www.hankyung.com/search/"
                f"?query={quote_plus(keyword)}&page={page}")

    def parse_page(self, driver) -> list:
        items = []
        cards = []
        for sel in ["ul.list_news li", "li.item", "article.list-item", "li.news-item"]:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(cards) > 2:
                break
        for card in cards:
            title = (
                self.safe_text(card, "h3.title a")
                or self.safe_text(card, "a.tit")
                or self.safe_text(card, ".news-tit")
                or self.safe_text(card, "h2 a")
            )
            if not title or len(title) < 5:
                continue
            url = (
                self.safe_attr(card, "h3.title a", "href")
                or self.safe_attr(card, "a.tit", "href")
                or self.safe_attr(card, ".news-tit", "href")
            )
            if url and url.startswith("/"):
                url = "https://www.hankyung.com" + url
            pub_time = self.safe_text(card, "span.date") or self.safe_text(card, "time")
            press    = self.safe_text(card, "span.author") or "한국경제"
            items.append(NewsItem(title, press, pub_time, url, self.SITE_KEY))
        return items


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  통합 매니저
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MultiSiteCrawler:
    """
    3대 뉴스 사이트 통합 크롤러 매니저
    _REGISTRY에 {key: Class}를 추가하면 바로 새 사이트 지원

    사용 예:
        crawler = MultiSiteCrawler(sites=["naver","daum","hankyung"])
        df = crawler.crawl_to_df(keyword="삼성전자", pages_per_site=2)
    """

    _REGISTRY: dict[str, type] = {
        "naver":    NaverCrawler,
        "daum":     DaumCrawler,       # ★ 다음 추가
        "hankyung": HankyungCrawler,
    }

    def __init__(self, sites: Optional[List[str]] = None,
                 headless: bool = True, max_retries: int = 3,
                 retry_delay_sec: float = 2.0, timeout_sec: int = 20):

        target = sites or list(self._REGISTRY.keys())
        invalid = set(target) - set(self._REGISTRY)
        if invalid:
            raise ValueError(f"지원하지 않는 사이트: {invalid}")

        self.crawlers = [
            self._REGISTRY[k](
                headless=headless,
                wait_sec=timeout_sec,
                max_retries=max_retries,
                retry_delay_sec=retry_delay_sec,
            )
            for k in target
        ]
        logger.info(f"크롤러 초기화: {[c.SITE_NAME for c in self.crawlers]}")

    def crawl_to_df(self, keyword: str, pages_per_site: int = 2):
        import pandas as pd
        logger.info(f"크롤링 시작: '{keyword}' ({pages_per_site}p × {len(self.crawlers)}사이트)")
        all_items = []

        for crawler in self.crawlers:
            try:
                items = crawler.crawl(keyword, pages_per_site)
                all_items.extend(items)
                logger.info(f"[{crawler.SITE_NAME}] {len(items)}건")
            except Exception as e:
                logger.error(f"[{crawler.SITE_NAME}] 실패: {e}", exc_info=True)

        # URL 기반 중복 제거
        seen, unique = set(), []
        for item in all_items:
            key = (item.url or item.title).strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(item)

        dup = len(all_items) - len(unique)
        logger.info(f"크롤링 완료: {len(unique)}건 (중복 {dup}건 제거)")

        return pd.DataFrame([i.to_dict() for i in unique]) if unique else pd.DataFrame()

    @classmethod
    def list_sites(cls) -> list:
        return list(cls._REGISTRY.keys())