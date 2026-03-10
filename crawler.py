"""
crawler.py - 다중 뉴스 사이트 Selenium 크롤러
"""

from __future__ import annotations

import time
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


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


def build_driver(headless: bool = True) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


class BaseCrawler(ABC):
    SITE_NAME: str = ""
    SITE_KEY:  str = ""

    def __init__(self, headless: bool = True, wait_sec: int = 10,
                 delay_range: tuple = (1.0, 2.0)):
        self.headless    = headless
        self.wait_sec    = wait_sec
        self.delay_range = delay_range

    @abstractmethod
    def build_url(self, keyword: str, page: int) -> str:
        pass

    @abstractmethod
    def wait_selector(self) -> str:
        pass

    @abstractmethod
    def parse_page(self, driver: webdriver.Chrome) -> list[NewsItem]:
        pass

    def crawl(self, keyword: str, pages: int = 3) -> list[NewsItem]:
        results = []
        driver = build_driver(self.headless)
        wait = WebDriverWait(driver, self.wait_sec)

        try:
            for page in range(1, pages + 1):
                url = self.build_url(keyword, page)
                print(f"      [{self.SITE_NAME}] {page}/{pages}p 수집 중...")
                driver.get(url)

                try:
                    wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self.wait_selector())
                    ))
                    # 추가 로딩 대기
                    time.sleep(1)
                    items = self.parse_page(driver)
                    results.extend(items)
                except TimeoutException:
                    print(f"      [{self.SITE_NAME}] {page}p 타임아웃 (결과 없음)")
                    continue

                time.sleep(random.uniform(*self.delay_range))

        except Exception as e:
            print(f"      [{self.SITE_NAME}] 오류 발생: {e}")
        finally:
            driver.quit()

        return results

    @staticmethod
    def safe_text(element, selector: str, default: str = "") -> str:
        try:
            return element.find_element(By.CSS_SELECTOR, selector).text.strip()
        except NoSuchElementException:
            return default

    @staticmethod
    def safe_attr(element, selector: str, attr: str, default: str = "") -> str:
        try:
            return element.find_element(By.CSS_SELECTOR, selector).get_attribute(attr) or default
        except NoSuchElementException:
            return default


class NaverCrawler(BaseCrawler):
    SITE_NAME = "네이버뉴스"
    SITE_KEY  = "naver"
    _BASE = "https://search.naver.com/search.naver?where=news&query={kw}&start={start}&sort=1"

    def build_url(self, keyword: str, page: int) -> str:
        start = (page - 1) * 10 + 1
        return self._BASE.format(kw=quote_plus(keyword), start=start)

    def wait_selector(self) -> str:
        return "ul.list_news"

    def parse_page(self, driver) -> list:
        items = []
        cards = driver.find_elements(By.CSS_SELECTOR, "ul.list_news > li.bx")
        for card in cards:
            title = self.safe_text(card, "a.news_tit")
            if not title: continue
            press = self.safe_text(card, "a.info.press") or self.safe_text(card, "span.info")
            pub_time = self.safe_text(card, "span.info")
            url = self.safe_attr(card, "a.news_tit", "href")
            items.append(NewsItem(title, press, pub_time, url, self.SITE_KEY))
        return items


class HankyungCrawler(BaseCrawler):
    SITE_NAME = "한국경제"
    SITE_KEY  = "hankyung"
    _BASE = "https://www.hankyung.com/search?search_str={kw}&page={page}&type=news&sort=date"

    def build_url(self, keyword: str, page: int) -> str:
        return self._BASE.format(kw=quote_plus(keyword), page=page)

    def wait_selector(self) -> str:
        return "ul.list-news"

    def parse_page(self, driver) -> list:
        items = []
        cards = driver.find_elements(By.CSS_SELECTOR, "ul.list-news > li")
        for card in cards:
            title = self.safe_text(card, "h3.title")
            if not title: continue
            url = self.safe_attr(card, "h3.title a", "href")
            if url and url.startswith("/"): url = "https://www.hankyung.com" + url
            press = "한국경제"
            pub_time = self.safe_text(card, "span.date")
            items.append(NewsItem(title, press, pub_time, url, self.SITE_KEY))
        return items


class MultiSiteCrawler:
    _REGISTRY = {
        "naver":    NaverCrawler,
        "hankyung": HankyungCrawler,
    }

    def __init__(self, sites=None, headless: bool = True):
        target_keys = sites or list(self._REGISTRY.keys())
        self.crawlers = [self._REGISTRY[k](headless=headless) for k in target_keys if k in self._REGISTRY]

    def crawl_to_df(self, keyword: str, pages_per_site: int = 3):
        import pandas as pd
        all_items = []
        for crawler in self.crawlers:
            items = crawler.crawl(keyword, pages_per_site)
            all_items.extend(items)
        
        # 중복 제거
        unique_items = []
        seen_urls = set()
        for item in all_items:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_items.append(item)
                
        return pd.DataFrame([i.to_dict() for i in unique_items])
