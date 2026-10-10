
"""JobRadar 配置 —— 已按最新浏览器 Copy as cURL 更新凭证"""

# 主接口（?_= 是浏览器的防缓存时间戳，可带可不带，requests 这里省略不影响）
API_URL = "https://www.nowcoder.com/np-api/u/school-schedule/list-card"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://www.nowcoder.com",
    "referer": "https://www.nowcoder.com/jobs/school/schedule?tab=1",
    "priority": "u=1, i",
    "sec-ch-ua": '"Chromium";v="154", "Microsoft Edge";v="154", "Not A(Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"
    ),
    "x-requested-with": "XMLHttpRequest",
    # 注意：cookie 不放这里，由 spider.py 从 cookies.txt 读取后单独传入
}

# 翻页参数（与最新 cURL 的 data-raw 完全一致）
PAGE_PARAMS = {
    "query": "",
    "propertyId": "",
    "page": 1,
    "pageSize": 20,
    "tab": 1,
}

# 能力关键词（保留，未来做语义辅助可能用到）
MY_KEYWORDS = ["测试", "测开", "质量", "QA", "自动化", "运维", "游戏", "AI"]

# 最多抓几页（先调通可设小一点，比如 2~3）
MAX_PAGES = 3