import time
import requests
from config import API_URL, HEADERS, PAGE_PARAMS, MAX_PAGES

DROP_KEYWORDS = [
    "销售", "市场", "商务", "行政", "人事", "hr", "财务", "会计",
    "物流", "普工", "操作工", "客服", "新媒体"
]

KEEP_KEYWORDS = [
    "测试", "测开", "qa", "算法", "ai", "运维", "devops", "sre",
    "后端", "前端", "全栈", "开发", "java", "c++", "python"
]

def _is_hard_drop(career: str) -> bool:
    text = (career or "").lower()
    if any(k in text for k in KEEP_KEYWORDS):
        return False
    return any(k in text for k in DROP_KEYWORDS)

def _load_cookies() -> dict:
    cookies = {}
    try:
        with open("cookies.txt", encoding="utf-8") as f:
            text = f.read().strip()
    except FileNotFoundError:
        raise SystemExit("请先在 cookies.txt 中粘贴你的牛客 cookie")
    for part in text.split(";"):
        part = part.strip()
        if part and "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies

def _lst(value):
    return value if isinstance(value, list) else []

def _job_key(job: dict) -> str:
    return f"{job.get('company','')}|{job.get('career','')}|{job.get('apply_link','')}"

def fetch_jobs(max_pages: int = MAX_PAGES) -> tuple[list[dict], list[dict]]:
    cookies = _load_cookies()
    new_jobs: list[dict] = []
    all_fetched_keys: set[str] = set()
    dropped = 0

    print(f"[增量抓取模式，最多翻 {max_pages} 页]")

    for page in range(1, max_pages + 1):
        params = {**PAGE_PARAMS, "page": page}
        try:
            print(f"  -> 正在获取第 {page} 页...")
            resp = requests.post(
                API_URL, headers=HEADERS, cookies=cookies, data=params, timeout=15
            )
            resp.raise_for_status()
            data = resp.json()

            body = data.get("data") or {}
            records = _lst(body.get("datas"))

            if not records:
                print(f"     [第 {page} 页无更多数据，提前结束]")
                break

            page_new = 0
            for rec in records:
                company = rec.get("name") or "未知公司"
                careers = _lst(rec.get("careerNameList"))
                if not careers:
                    careers = [rec.get("careerName", "")]
                apply_link = rec.get("customWangshenLink", "")

                for career in careers:
                    job = {
                        "company": company,
                        "career": career or "",
                        "city": rec.get("cityList", []),
                        "batch": rec.get("batchName", ""),
                        "wangshen_time": rec.get("wangshenTime", ""),
                        "apply_link": apply_link,
                        "company_evaluation": rec.get("introduction", "")
                    }
                    key = _job_key(job)
                    all_fetched_keys.add(key)

                    if _is_hard_drop(career):
                        dropped += 1
                        continue

                    new_jobs.append(job)
                    page_new += 1

            print(f"     [第 {page} 页完成] 新增 {page_new} 条有效岗位")

        except Exception as e:
            print(f"  -> 第 {page} 页异常: {e}")
            time.sleep(2)

        time.sleep(0.5)

    print(f"\n[成功] 本轮抓取完毕：新增 {len(new_jobs)} 条，丢弃 {dropped} 条。")
    return new_jobs, list(all_fetched_keys)