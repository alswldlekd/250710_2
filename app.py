from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import csv
import os

app = Flask(__name__)

POTENS_API_KEY = "eykC4BBZxbq16ngzIRCXHaKoGTD36nxq"

# ======================
# Utils: 엑셀/CSV 저장
# ======================
def save_analysis_result(item):
    with open('analysis_results.csv', 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([item['title'], item['link'], item['analysis']])

def save_diagnosis_result(keyword, result):
    with open('diagnosis_results.csv', 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([keyword, result])

# ======================
# Routes
# ======================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze")
def analyze():
    return render_template("analyze.html")


# ======================
# API: 블로그 링크 수집
# ======================
def get_naver_blog_links(keyword, max_fetch=5):
    query = f"{keyword} 병원"
    search_url = f"https://search.naver.com/search.naver?where=view&query={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(search_url, headers=headers)

    links = []
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if 'blog.naver.com' in href and href not in links:
                links.append(href)
            if len(links) >= max_fetch:
                break
    return links


def crawl_blog_content(blog_url):
    headers = {"User-Agent": "Mozilla/5.0"}

    if "m.blog" not in blog_url:
        blog_url = blog_url.replace("blog", "m.blog")

    try:
        resp = requests.get(blog_url, headers=headers, timeout=5)
        if resp.status_code != 200:
            return None, None

        soup = BeautifulSoup(resp.content, 'html.parser')
        title_tag = soup.find("meta", property="og:title")
        title = title_tag["content"] if title_tag and title_tag.get("content") else "제목 추출 실패"

        try:
            content = soup.find("div", class_="se-main-container").get_text(separator="\n", strip=True)
        except:
            content = ""

        if content.strip() == "":
            return None, None

        return title, content

    except Exception:
        return None, None

# ======================
# API: Potens.ai 호출
# ======================
def analyze_blog_content_via_potens(content):
    system_prompt = (
        "당신은 한국의 의료광고 전문가이자 규제 감독자 역할을 합니다. "
        "사용자가 제공하는 한국 병원 블로그 본문을 읽고 아래 작업을 정확하고 간결하게 수행합니다.\n\n"
        "- 병원명: 본문에 등장하는 병원명을 정확히 추출\n"
        "- 과대광고/허위광고 여부: 한국 의료법 기준으로 평가\n"
        "- 이유: 판단 근거를 간단명료하게 설명"
    )

    user_prompt = (
        f"[본문]\n{content}\n\n"
        "분석 결과를 아래 형식으로 정리해주세요.\n"
        "---\n"
        "✅ 병원명:\n(병원명 텍스트)\n\n"
        "✅ 과대광고/허위광고 여부:\n(있음/없음)\n\n"
        "✅ 판단 이유:\n(간단명료한 설명)"
    )

    url = "https://ai.potens.ai/api/chat"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {POTENS_API_KEY}"
    }
    data = {"prompt": f"{system_prompt}\n\n{user_prompt}"}

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        return result.get("message", "❌ Potens.ai 응답에 'message' 키가 없음!")
    else:
        return f"❌ Potens.ai API 호출 실패: {response.status_code} - {response.text}"


def get_diagnosis_code_from_potens(keyword):
    system_prompt = (
        "당신은 한국의 의학 전문가입니다. "
        "사용자가 입력한 증상이나 시술 키워드에 대해, "
        "한국질병분류코드(KCD)를 코드명+설명 형태로 추천합니다."
    )

    user_prompt = (
        f"'{keyword}' 증상으로 병원에서 진단받을 수 있는 한국의료보험 진단코드명을 "
        "코드명(예: M99.0) + 한글 설명 형태로 표나 리스트로 보기 좋게 정리해줘."
    )

    url = "https://ai.potens.ai/api/chat"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {POTENS_API_KEY}"
    }
    data = {"prompt": f"{system_prompt}\n\n{user_prompt}"}

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        return result.get("message", "❌ Potens.ai 응답에 'message' 키가 없음!")
    else:
        return f"❌ Potens.ai API 호출 실패: {response.status_code} - {response.text}"


# ======================
# Flask API 엔드포인트
# ======================
@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json()
    keyword = data.get("keyword")
    num_links = data.get("num_links", 5)
    if not keyword:
        return jsonify({"error": "No keyword provided"}), 400

    # 후보 링크 더 많이 긁어오기
    candidate_links = get_naver_blog_links(keyword, max_fetch=30)

    results = []
    for link in candidate_links:
        if len(results) >= num_links:
            break

        title, content = crawl_blog_content(link)
        if not content:
            continue

        analysis = analyze_blog_content_via_potens(content)
        results.append({"title": title, "link": link, "analysis": analysis})
        save_analysis_result({"title": title, "link": link, "analysis": analysis})

    return jsonify({"results": results})




@app.route("/api/diagnosis", methods=["POST"])
def api_diagnosis():
    data = request.get_json()
    keyword = data.get("keyword")
    if not keyword:
        return jsonify({"error": "No keyword provided"}), 400

    diagnosis_result = get_diagnosis_code_from_potens(keyword)
    save_diagnosis_result(keyword, diagnosis_result)
    return jsonify({"result": diagnosis_result})

from flask import Flask, render_template
from analysis_module import run_analysis

app = Flask(__name__)

@app.route('/')
def home():
    # ✅ 너가 만든 모델 분석 함수 불러오기
    columns, result_list = run_analysis()

    
    # ✅ HTML로 결과 넘기기
    return render_template(
    'index.html',
    columns=columns,
    rows=result_list
)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

