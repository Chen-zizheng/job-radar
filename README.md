# JobRadar 校招岗位雷达

把校招信息整理成一份可以筛选的本地清单：从牛客抓取公司与岗位信息，先按方向关键词粗筛，再结合简历调用 DeepSeek 评分，最后在 Streamlit 页面查看匹配理由、风险点与投递建议。另提供 FastAPI 接口，支持分页查询和结果写入。

<img width="1262" height="703" alt="筛选界面" src="https://github.com/user-attachments/assets/f45fddab-a101-49cf-be1a-923991874f2f" />
<img width="1271" height="703" alt="岗位明细" src="https://github.com/user-attachments/assets/e3e0f7cf-1a34-4d07-91c6-0167d045d6b7" />

## 快速开始

建议使用 Python 3.12（与接口测试 CI 一致）。

```bash
git clone https://github.com/Chen-zizheng/job-radar.git
cd job-radar
pip install -r requirements.txt
```

运行前准备：

| 输入 | 配置位置 | 说明 |
|---|---|---|
| 简历正文 | `resume.txt` | 替换为自己的简历，作为模型评分的对照 |
| 牛客登录态 | `cookies.txt` | 登录后从浏览器 DevTools 复制请求的 Cookie 头；过期需更新 |
| DeepSeek Key | 环境变量 `OPENAI_API_KEY` | 通过 OpenAI SDK 调用 DeepSeek |

Windows PowerShell 设置 Key：

```powershell
$env:OPENAI_API_KEY="你的 Key"
```

macOS / Linux 可使用 `export OPENAI_API_KEY="你的 Key"`。然后按顺序运行：

```bash
python spider.py        # 抓取 → output.json
python ai_scorer.py     # 关键词粗筛与模型评分 → scored.json
streamlit run app.py    # 打开本地筛选界面
```

Windows 也可以双击 `一键启动.bat` 执行前两步，Streamlit 界面仍需单独启动。抓取、评分和展示通过 JSON 文件衔接，页面不依赖 FastAPI 服务。

## 抓取与评分流程

```text
牛客校招列表 → spider.py → output.json
                            ↓ 按公司聚合、方向关键词粗筛
简历 resume.txt ───────→ ai_scorer.py → scored.json → Streamlit / FastAPI
```

- **抓取**：通过牛客站点内部 `np-api` 接口读取信息，分页参数在 `config.py`，`MAX_PAGES` 默认 3 页。Cookie 由抓取脚本从本地文件读取。
- **本地粗筛**：`ai_scorer.py` 中的 `TARGET_DIRECTIONS` 定义方向关键词，`SKIP_NO_TARGET=True` 时跳过没有命中方向的公司。这一步不调用模型。
- **模型评分**：每家公司聚合后发起一次调用，提示词带简历、公司信息和岗位方向，要求返回 0–100 匹配度、理由、风险点与建议。模型地址在 `ai_scorer.py` 中固定为 `https://api.deepseek.com/v1`。

简历和岗位内容会发送给 DeepSeek，使用前请移除不必要的个人敏感信息；不要上传 Cookie、Key 或私人简历到公开仓库。模型分数用于辅助排序，不替代对岗位要求和招聘状态的确认。

## 进度保存与重跑

结果按**公司**保存：每处理完一家，都会重写 `scored.json`。默认 `INCREMENTAL=True`，重跑时按公司名跳过已有记录，减少重复调用；不是同一家公司内部的岗位级断点续跑。

调用失败或 JSON 解析失败也可能作为记录保存，随后被增量逻辑跳过。要重试某家公司，可先备份结果并移除对应记录；换简历或需要全量重新评分时，将 `ai_scorer.py` 中的 `INCREMENTAL` 改为 `False`。脚本优先读取已有 `output.json`，需要刷新岗位时应先重新抓取。

解析会剥离常见的 Markdown 代码围栏，无法解析的内容保留为原文。当前没有完整的模型输出 schema 校验，字段或类型异常仍可能影响后续排序和展示。文件写入也不是原子事务，不保证断电或写入中断时的数据完整性。

## HTTP API

接口从 `scored.json` 读取结果，也可通过环境变量 `JOB_RADAR_DATA` 指定其他数据文件。写接口的密钥使用 `JOB_RADAR_API_KEY`，与模型 Key 分开。

```bash
pip install -r requirements-dev.txt
uvicorn api:app --reload --port 8000
```

启动后访问 `http://127.0.0.1:8000/docs` 查看交互文档。需要写入时，先在启动服务的终端设置 `JOB_RADAR_API_KEY`，请求中携带同值的 `X-API-Key`。

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/health` | 无 | 服务状态与公司数量 |
| GET | `/api/companies` | 无 | 分页，按最低分、方向、投递建议筛选 |
| GET | `/api/companies/{company}` | 无 | 单公司详情，不存在返回 404 |
| POST | `/api/scores` | `X-API-Key` | 新增或更新公司结果，成功返回 201 |

列表示例：`http://127.0.0.1:8000/api/companies?page=1&page_size=10&min_score=80`。页码从 1 开始，每页 1–100 条；参数越界返回 422，合法查询没有命中或超出末页返回 200 和空列表。

写接口未配置服务端 Key 时返回 500 并拒绝写入，Key 错误返回 401，缺少公司名返回 422。同名公司重复提交会替换整条公司记录，不是字段级合并。读接口没有鉴权，默认按本地工具使用，不宜直接暴露到公网。

## 测试

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests -q -p no:cacheprovider
```

现有 **24 条接口用例覆盖 4 个端点**，包括分页、筛选、边界参数、详情不存在、写入鉴权及同名更新，设计表见 [接口测试用例](docs/接口测试用例.md)。测试通过 FastAPI `TestClient` 在进程内驱动应用，每条用例使用独立数据文件，不监听真实端口，也没有部署实例的 `--base-url` 开关。

这些用例不覆盖真实牛客抓取、模型评分或浏览器交互。CI 配置在 `.github/workflows/test.yml`，使用 Python 3.12，在推送到 main 和 PR 时运行接口测试。

## 已知限制

- 牛客 Cookie 会过期，站点内部接口或字段变更也可能导致抓取失败；当前没有完整的抓取重试与兼容性测试。
- 评分去重只看公司名，不会自动识别同公司新岗位、简历变化或历史失败记录，需要按上述方式主动重评。
- 评分与 API 都以整个 JSON 文件覆盖写入，没有文件锁；不要同时运行多个写入进程。
- 真实模型输出不确定，评分脚本尚无自动化测试；接口用例不能证明整个抓取到评分流程通过。

## 目录

```text
config.py          # 抓取接口、请求头与分页参数
spider.py          # 抓取与翻页
ai_scorer.py       # 方向关键词、公司聚合、模型评分与增量保存
app.py             # Streamlit 筛选界面
api.py             # FastAPI 接口
tests/             # 接口自动化用例
docs/              # 用例设计
一键启动.bat        # Windows 抓取与评分入口
output.json        # 抓取结果（生成物）
scored.json        # 公司评估结果（生成物）
```
