"""岗位雷达 · HTTP 接口层

启动： uvicorn api:app --reload --port 8000
数据： 默认读 scored.json，可用环境变量 JOB_RADAR_DATA 指定其他文件
鉴权： 写接口 POST /api/scores 需要 X-API-Key，值取自环境变量 JOB_RADAR_API_KEY

设计取舍：
- 只读数据从 scored.json 现读，不缓存，避免测试之间互相污染；
- 分页参数交给 FastAPI 的 Query 约束（ge/le），越界直接 422，而不是在函数里手写 if 判断；
- 详情接口用资源名而不是下标，名字不存在返回 404，语义上更明确。
"""
import json
import math
import os

from fastapi import FastAPI, Header, HTTPException, Query

DATA_FILE = os.environ.get("JOB_RADAR_DATA", "scored.json")
API_KEY = os.environ.get("JOB_RADAR_API_KEY", "")
MAX_PAGE_SIZE = 100

app = FastAPI(title="JobRadar API", version="1.0.0")


# ------------------------------------------------------------------ 数据读取
def load_companies():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def save_companies(rows):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def _matches(row):
    return (row.get("eval") or {}).get("岗位匹配") or []


def best_score(row):
    return max([j.get("匹配度", 0) for j in _matches(row)], default=0)


def directions(row):
    return row.get("directions_hit") or []


# ------------------------------------------------------------------ 接口
@app.get("/health")
def health():
    return {"status": "ok", "companies": len(load_companies()), "version": app.version}


@app.get("/api/companies")
def list_companies(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(10, ge=1, le=MAX_PAGE_SIZE, description="每页条数，1-100"),
    min_score: int = Query(0, ge=0, le=100, description="最低匹配度"),
    direction: str | None = Query(None, description="投递方向，精确匹配"),
    only_suggest: bool = Query(False, description="只看建议投递的岗位"),
):
    rows = load_companies()
    rows = [r for r in rows if best_score(r) >= min_score]
    if direction:
        rows = [r for r in rows if direction in directions(r)]
    if only_suggest:
        rows = [r for r in rows if any(j.get("投递建议") == "建议" for j in _matches(r))]

    total = len(rows)
    pages = math.ceil(total / page_size) if total else 0
    start = (page - 1) * page_size
    return {
        "items": rows[start:start + page_size],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": pages,
    }


@app.get("/api/companies/{company}")
def get_company(company: str):
    for row in load_companies():
        if row.get("company") == company:
            return row
    raise HTTPException(status_code=404, detail="company not found: %s" % company)


@app.post("/api/scores", status_code=201)
def push_score(payload: dict, x_api_key: str | None = Header(default=None)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="JOB_RADAR_API_KEY 未配置")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="X-API-Key 无效")
    if not payload.get("company"):
        raise HTTPException(status_code=422, detail="company 不能为空")

    rows = load_companies()
    for i, row in enumerate(rows):
        if row.get("company") == payload["company"]:
            rows[i] = payload
            break
    else:
        rows.append(payload)
    save_companies(rows)
    return {"company": payload["company"], "total": len(rows)}
