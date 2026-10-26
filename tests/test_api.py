# -*- coding: utf-8 -*-
"""JobRadar HTTP 接口测试

运行： pytest tests/ -q
说明： 用 FastAPI TestClient（基于 httpx）驱动应用，不启动真实端口，
      因此可以跑在 CI 里；同时也保留 base_url 模式，便于对已部署实例做冒烟。
"""
import json
import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import api  # noqa: E402

API_KEY = "test-key-123"

ROWS = [
    {"company": "甲公司", "directions_hit": ["测试"], "eval": {"岗位匹配": [{"匹配度": 90, "投递建议": "建议"}]}},
    {"company": "乙公司", "directions_hit": ["开发"], "eval": {"岗位匹配": [{"匹配度": 70, "投递建议": "建议"}]}},
    {"company": "丙公司", "directions_hit": ["测试", "开发"], "eval": {"岗位匹配": [{"匹配度": 30, "投递建议": "不建议"}]}},
    {"company": "丁公司", "directions_hit": [], "eval": {}},
]


TMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp")


@pytest.fixture()
def client(monkeypatch):
    """每个用例一份独立数据文件，避免用例之间互相污染。

    刻意不用 pytest 的 tmp_path：Windows 下临时目录可能不可写，
    放在仓库内的 tests/_tmp 更稳（该目录已加入 .gitignore）。
    """
    os.makedirs(TMP_DIR, exist_ok=True)
    path = os.path.join(TMP_DIR, "scored_%s.json" % uuid.uuid4().hex)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ROWS, f, ensure_ascii=False)
    monkeypatch.setattr(api, "DATA_FILE", path)
    monkeypatch.setattr(api, "API_KEY", API_KEY)
    yield TestClient(api.app)
    try:
        os.remove(path)
    except OSError:
        pass


# ---------------------------------------------------------------- 健康检查
def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["companies"] == 4
    assert body["version"] == api.app.version


# ---------------------------------------------------------------- 列表：正常
def test_list_default(client):
    r = client.get("/api/companies")
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 1 and body["page_size"] == 10
    assert body["total"] == 4 and body["pages"] == 1
    assert len(body["items"]) == 4


def test_list_pagination_splits_rows(client):
    p1 = client.get("/api/companies", params={"page": 1, "page_size": 3}).json()
    p2 = client.get("/api/companies", params={"page": 2, "page_size": 3}).json()
    assert len(p1["items"]) == 3 and p1["pages"] == 2
    assert len(p2["items"]) == 1
    assert {r["company"] for r in p1["items"]} & {r["company"] for r in p2["items"]} == set()


def test_list_page_beyond_last_returns_empty(client):
    body = client.get("/api/companies", params={"page": 99, "page_size": 10}).json()
    assert body["items"] == []
    assert body["total"] == 4


def test_filter_min_score(client):
    body = client.get("/api/companies", params={"min_score": 80}).json()
    assert [r["company"] for r in body["items"]] == ["甲公司"]


def test_filter_direction(client):
    body = client.get("/api/companies", params={"direction": "测试"}).json()
    assert {r["company"] for r in body["items"]} == {"甲公司", "丙公司"}


def test_filter_unknown_direction_is_empty_not_error(client):
    r = client.get("/api/companies", params={"direction": "不存在的方向"})
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_filter_only_suggest(client):
    body = client.get("/api/companies", params={"only_suggest": True}).json()
    assert {r["company"] for r in body["items"]} == {"甲公司", "乙公司"}


# ---------------------------------------------------------------- 列表：参数校验
@pytest.mark.parametrize("params", [
    {"page": 0},            # 下界外
    {"page": -1},
    {"page_size": 0},       # 下界外
    {"page_size": 101},     # 上界外（上限 100）
    {"min_score": -1},
    {"min_score": 101},
    {"page": "abc"},        # 类型错
])
def test_invalid_query_returns_422(client, params):
    assert client.get("/api/companies", params=params).status_code == 422


def test_page_size_upper_bound_inclusive(client):
    assert client.get("/api/companies", params={"page_size": 100}).status_code == 200


# ---------------------------------------------------------------- 详情
def test_detail_found(client):
    r = client.get("/api/companies/甲公司")
    assert r.status_code == 200
    assert r.json()["company"] == "甲公司"


def test_detail_not_found(client):
    r = client.get("/api/companies/不存在的公司")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"]


# ---------------------------------------------------------------- 写接口：鉴权与校验
def test_push_without_key_returns_401(client):
    r = client.post("/api/scores", json={"company": "戊公司"})
    assert r.status_code == 401


def test_push_with_wrong_key_returns_401(client):
    r = client.post("/api/scores", json={"company": "戊公司"}, headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_push_missing_company_returns_422(client):
    r = client.post("/api/scores", json={"foo": 1}, headers={"X-API-Key": API_KEY})
    assert r.status_code == 422


def test_push_creates_and_lists(client):
    r = client.post("/api/scores", json={"company": "戊公司", "directions_hit": ["测试"]},
                    headers={"X-API-Key": API_KEY})
    assert r.status_code == 201
    assert r.json() == {"company": "戊公司", "total": 5}
    assert "戊公司" in {x["company"] for x in client.get("/api/companies").json()["items"]}


def test_push_same_company_updates_not_duplicates(client):
    client.post("/api/scores", json={"company": "甲公司", "directions_hit": ["开发"]},
                headers={"X-API-Key": API_KEY})
    body = client.get("/api/companies").json()
    assert body["total"] == 4
    assert client.get("/api/companies/甲公司").json()["directions_hit"] == ["开发"]


def test_push_without_server_key_configured_returns_500(client, monkeypatch):
    monkeypatch.setattr(api, "API_KEY", "")
    r = client.post("/api/scores", json={"company": "戊公司"}, headers={"X-API-Key": "any"})
    assert r.status_code == 500
