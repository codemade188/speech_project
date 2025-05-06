"""
批量抓取 TalkEnglish “Interview English Lessons” 例句 → 生成 questions_Interview.csv
仅输出两列：text, topic
思路：直接遍历所有 Interview 子课时详情页，提取所有 <a> 标签中以句号/问号/感叹号结尾的问答
"""

import requests
import csv
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─── 全局常量 ──────────────────────────────────────────
BASE_URL       = "https://www.talkenglish.com/"
TOPIC_NAME     = "Interview"
# Interview English Lessons 下的 8 个子课时页面
CATEGORY_PATHS = [
    "speaking/interview/intbasic1.aspx",   # Basic Interview Questions I
    "speaking/interview/intbasic2.aspx",   # Basic Interview Questions II
    "speaking/interview/intschool.aspx",   # School Related Interview Q's
    "speaking/interview/intwork1.aspx",    # Work Related Interview Q's I
    "speaking/interview/intwork2.aspx",    # Work Related Interview Q's II
    "speaking/interview/intwork3.aspx",    # Work Related Interview Q's III
    "speaking/interview/intpeople.aspx",   # Working with People Interview Q's
    "speaking/interview/intmisc.aspx",     # Miscellaneous Interview Q's
]

# 文本清洗与过滤
SPACE_CLEAN    = re.compile(r'\s+')
END_PUNCT      = re.compile(r'.+[\.!?]$')                   # 必须以 . ? ! 结尾
FILTER_NOISE   = re.compile(r'copyright|talkenglish', re.I)  # 去除版权提示

# ─── HTTP 会话与重试配置 ─────────────────────────────────
session = requests.Session()
session.trust_env = False
session.headers.update({"User-Agent": "Mozilla/5.0"})
# 遇到 429/5xx 自动重试
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

def get_soup(url: str) -> BeautifulSoup:
    """请求页面并移除 <script>/<style>/<noscript> 标签。"""
    try:
        r = session.get(url, timeout=15)
        r.raise_for_status()
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup.select('script,style,noscript'):
            tag.decompose()
        return soup
    except Exception as e:
        print(f"⚠️ 请求失败 {url}: {e}")
        return BeautifulSoup("", 'html.parser')

def clean_text(text: str) -> str:
    """合并多余空白为单空格，并去除首尾空格。"""
    return SPACE_CLEAN.sub(' ', text).strip()

def scrape_interview():
    out_file = "questions_Interview.csv"
    total = 0

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "topic"])

        for path in CATEGORY_PATHS:
            url = urljoin(BASE_URL, path)
            print(f"▶ 抓取：{url}")
            page = get_soup(url)

            for a in page.find_all("a"):
                txt = clean_text(a.get_text())
                # 只保留以标点结尾、首字母大写，且无版权噪声的句子
                if END_PUNCT.match(txt) and txt[0].isupper() and not FILTER_NOISE.search(txt):
                    writer.writerow([txt, TOPIC_NAME])
                    total += 1

            time.sleep(0.3)  # 礼貌爬取

    print(f"✅ 完成，共写入 {total} 条“{TOPIC_NAME}”例句到 {out_file}")

if __name__ == "__main__":
    scrape_interview()
