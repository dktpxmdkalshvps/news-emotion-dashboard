from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def debug_crawl(url):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print(f"Connecting to: {url}")
        driver.get(url)
        time.sleep(5)
        
        print("\n--- Page Title ---")
        print(driver.title)
        
        print("\n--- Page Source Snippet ---")
        print(driver.page_source[:2000])
        
        # Check for Naver News items
        items = driver.find_elements("css selector", "li.bx, div.news_area, .news_wrap")
        print(f"\nFound {len(items)} potential news items")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_crawl("https://search.naver.com/search.naver?where=news&query=%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90&sort=1")
