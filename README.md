# JobRadar 校招岗位雷达

牛客的校招岗位列表 → 本地关键词粗筛 → 模型按简历打分 → 本地网页筛选。以前每天翻岗位翻到眼花，现在跑三条命令，剩下的时间用来看分数前二十家。

<img width="1262" height="703" alt="筛选界面" src="https://github.com/user-attachments/assets/f45fddab-a101-49cf-be1a-923991874f2f" />
<img width="1271" height="703" alt="岗位明细" src="https://github.com/user-attachments/assets/e3e0f7cf-1a34-4d07-91c6-0167d045d6b7" />

## 怎么跑

```bash
git clone https://github.com/Chen-zizheng/job-radar.git
cd job-radar
pip install -r requirements.txt
```

跑之前准备三样：

| 输入 | 放哪 | 说明 |
|---|---|---|
| 简历正文 | `resume.txt` | 打分时的对照基准，换成自己的内容 |
| 牛客登录态 | `cookies.txt` | 登录后从浏览器 DevTools 复制 Cookie 头，过期要重贴 |
| DeepSeek Key | 环境变量 `OPENAI_API_KEY` | 走 OpenAI SDK，`base_url` 指向 DeepSeek |

```bash
python spider.py        # 抓岗位 → output.json
python ai_scorer.py     # 粗筛 + 打分 → scored.json
streamlit run app.py    # 筛选界面
```

Windows 上双击 `一键启动.bat` 跑完前两步，界面还是要自己起。

## 两级过滤

第一级在本地：`config.py` 的 `TARGET_DIRECTIONS` 按方向关键词砍掉明显不对口的公司，不发请求，也不花钱。

第二级才调模型：粗筛剩下的公司每家一次调用，拿回 0–100 分连同匹配理由、风险点、投递建议。

粗筛规则按「宁可放宽」写：漏掉一家对口公司的代价，比多花一次 Token 高。

## 分数怎么落盘

`scored.json` 以公司为粒度存。每评估完一家立刻写回，Ctrl+C、断网、关机都不丢已完成的部分；重跑时已评估的公司直接跳过，不重复调用。

模型返回的 JSON 会带代码围栏、缺字段、字段类型不对。解析前先剥围栏，缺字段按默认值降级，一条脏数据不该让整页渲染崩掉。

## 接口层

`api.py` 是 FastAPI，把 `scored.json` 暴露成可翻页、可过滤的 REST 接口。

```bash
pip install -r requirements-dev.txt
uvicorn api:app --reload --port 8000
pytest tests -q          # 24 passed，0.76 s
```

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/health` | — | 服务与数据量探活 |
| GET | `/api/companies` | — | 分页 + 最低分 + 方向 + 只看建议 |
| GET | `/api/companies/{company}` | — | 单公司详情，不存在返回 404 |
| POST | `/api/scores` | `X-API-Key` | 写入或更新一条评估结果 |

分页越界返回 200 加空列表，不是 404：查询条件没匹配到岗位，属于「这个条件下没有」，不属于「资源不存在」。

写接口在服务端没配 key 时返回 500 并拒绝写入（fail-closed），key 对不上返回 401，缺字段返回 422。同名公司重复提交是更新而不是追加。

24 条用例按等价类、边界值、鉴权与参数的组合写，每条预期在 [`docs/接口测试用例.md`](docs/接口测试用例.md)。CI 在 `.github/workflows/test.yml`，每次 push 跑一遍。

## 已知问题

- **Cookie 会过期**。牛客没有公开 API，抓的是站点内部接口 `np-api`，字段一变抓取就断，得重新对。
- **`MAX_PAGES` 默认只翻 3 页**。翻得少是故意的：先看几页够不够用，再决定加不加。
- **写接口是全量覆盖 `scored.json`**。两个进程同时写会丢更新，挡并发要加文件锁或者换数据库，还没做。
- **`ai_scorer.py` 没有单测**。公司粒度去重和解析降级只有人工验证，接口层那 24 条测不到这里。
- **分数有波动**。同一份简历重跑，分数会小幅变化，模型不是确定性函数，当参考不当标准。
- **`一键启动.bat` 只在 Windows 上能跑**，macOS / Linux 按上面三步手动来。

## 目录

```text
config.py        # 接口地址、请求头、分页参数、粗筛方向
spider.py        # 抓取与翻页
ai_scorer.py     # 关键词粗筛 + 公司粒度增量评分 + 容错解析
api.py           # FastAPI 接口层
tests/           # 接口用例
docs/            # 接口测试用例设计
app.py           # Streamlit 界面
一键启动.bat      # Windows 一键跑全流程
output.json      # 抓取结果（生成物）
scored.json      # 评估结果（生成物）
```

