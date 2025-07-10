import datetime
import time
import urllib.parse
from collections import Counter
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# ============================================
# ✅ ✅ ✅ 여기만 너가 직접 바꿔서 쓰면 돼
chromedriver_path = r"C:\Users\조민지\Desktop\local ai\web2\chromedriver-win64\chromedriver.exe"

keywords = ["도수치료"]
pages_to_crawl = 50
output_excel_path = "trend_data.xlsx"
# ============================================


# ✅ 날짜 처리
def clean_date(date_string, crawl_date=None):
    if crawl_date is None:
        crawl_date = datetime.date.today()
    if pd.isna(date_string):
        return str(crawl_date)
    date_string = str(date_string).strip()
    if any(keyword in date_string for keyword in ['전', '시간', '분', '일']):
        return str(crawl_date)
    return date_string

def standardize_date_format(date_string):
    if pd.isna(date_string):
        return date_string
    date_string = str(date_string).strip()
    if date_string.endswith('.'):
        date_string = date_string[:-1]
    return date_string.replace('.', '-')


# ✅ 연관 키워드 추출 (본문 + 제목에서 상위 3개)
def extract_related_keywords(title, content, top_n=3):
    all_words = (title + " " + content).split()
    tokens = [w for w in all_words if len(w) > 1]
    counter = Counter(tokens)
    top_keywords = [w for w, _ in counter.most_common(top_n)]
    return ", ".join(top_keywords)


# ✅ 크롤링 함수
def crawl_naver_cafe(keyword, last_page, chromedriver_path):
    ENCODED_KEYWORD = urllib.parse.quote(keyword)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    results = []

    def parse_page(html, page_num):
        soup = BeautifulSoup(html, "html.parser")
        related_keywords = [btn.get_text(strip=True) for btn in soup.select('.aside_search_tag button')]
        related_keywords_str = ", ".join(related_keywords)
        for item in soup.select('.ArticleItem'):
            link_tag = item.select_one('a')
            if link_tag:
                link = link_tag['href']
                title_elem = link_tag.select_one('strong.title')
                text_elem = link_tag.select_one('p.text')
                title = title_elem.get_text(strip=True) if title_elem else ""
                snippet = text_elem.get_text(strip=True) if text_elem else ""
            else:
                link = title = snippet = ""
            date_elem = item.select_one('span.date')
            date = date_elem.get_text(strip=True) if date_elem else ""
            results.append({
                "날짜": date,
                "제목": title,
                "링크": link,
                "본문": snippet,
                "연관검색어": related_keywords_str
            })

    base_url = f"https://section.cafe.naver.com/ca-fe/home/search/articles?q={ENCODED_KEYWORD}"
    driver.get(base_url)
    time.sleep(5)
    current_block = 1
    for page in range(1, last_page + 1):
        if page == 1:
            parse_page(driver.page_source, page)
            continue
        try:
            target_block = ((page - 1) // 10) + 1
            while current_block < target_block:
                next_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.type_next"))
                )
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(3)
                current_block += 1
            btn_xpath = f"//button[@class='btn number' and normalize-space(text())='{page}']"
            page_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, btn_xpath))
            )
            driver.execute_script("arguments[0].click();", page_btn)
            time.sleep(4)
            parse_page(driver.page_source, page)
        except Exception as e:
            print(f"[오류] {page}페이지 이동 실패: {e}")

    driver.quit()
    return results


# ✅ 메인
def main():
    all_data = []
    for keyword in keywords:
        print(f"\n✅ '{keyword}' 크롤링 시작...")
        crawl_results = crawl_naver_cafe(keyword, pages_to_crawl, chromedriver_path)
        if not crawl_results:
            print(f"❗ '{keyword}' 결과 없음")
            continue

        df = pd.DataFrame(crawl_results)
        print(f"✅ 크롤링 완료: {len(df)}건")

        df['날짜'] = df['날짜'].apply(clean_date).apply(standardize_date_format)
        df['키워드'] = keyword
        df['총_크롤링_개수'] = len(df)

        # ✅ 연관키워드 생성
        df['연관키워드'] = df.apply(lambda row: extract_related_keywords(row['제목'], row['본문']), axis=1)

        all_data.append(df)

    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        final_df = final_df[['키워드','총_크롤링_개수','날짜','제목','링크','본문','연관검색어','연관키워드']]
        final_df.to_excel(output_excel_path, index=False)
        print(f"\n✅ 모든 키워드 크롤링 완료 → '{output_excel_path}' 저장 완료!")
    else:
        print("\n❗ 크롤링된 데이터가 없습니다.")


if __name__ == "__main__":
    main()

