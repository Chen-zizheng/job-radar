# JobRadar 校招岗位智能雷达

一个自动抓取牛客网校招岗位、结合个人简历做 AI 匹配打分的本地工具。
把「逐条翻岗位、凭感觉判断值不值得投」的手工劳动，变成一条可重复运行的流水线。

<img width="1262" height="703" alt="筛选界面" src="https://github.com/user-attachments/assets/f45fddab-a101-49cf-be1a-923991874f2f" />
<img width="1271" height="703" alt="岗位明细" src="https://github.com/user-attachments/assets/e3e0f7cf-1a34-4d07-91c6-0167d045d6b7" />

## 流水线

```
牛客校招列表 ──► spider.py ──► output.json ──► 关键词粗筛 ──► ai_scorer.py ──► scored.json ──► app.py
                 (分页抓取)     (岗位原始数据)   (TARGET_DIRECTIONS)  (公司粒度+增量)   (评估结果)   (Streamlit)
```

两级过滤的设计目的是**控制成本**：先用本地关键词规则把明显不对口的公司砍掉，
再只把剩下的送进大模型精评。

## 功能亮点

- **自动抓取**：从牛客网的校招日程接口分页聚合岗位，落盘 `output.json`
- **AI 智能评分**：按简历内容对每家公司的岗位做 0–100 匹配度打分，附「匹配理由 / 风险点 / 投递建议」
- **增量评估**：以公司为粒度去重，已评估过的公司直接跳过，只为新公司花 Token
- **实时落盘**：每评估完一家立刻写回 `scored.json`，Ctrl+C / 断网 / 关机都不丢进度
- **容错解析**：模型返回非法 JSON 或字段缺失时降级处理，不让前端渲染崩掉
- **可视化筛选**：Streamlit 卡片式界面，支持按方向 / 最低分 / 是否建议投递筛选

## 技术栈

- Python 3.8+
- Streamlit（前端界面）
- OpenAI SDK（`base_url` 指向 DeepSeek，模型 `deepseek-flash`）
- Requests（抓取）
- BeautifulSoup 之外的纯 `json` 落盘，无数据库

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/Chen-zizheng/job-radar.git
cd job-radar
```

### 2. 安装依赖

```bash
pip install requests streamlit openai
```

### 3. 准备三样东西

| 文件 / 变量 | 说明 |
|---|---|
| `resume.txt` | 把你的简历正文粘进来，评分时会作为对照基准 |
| `cookies.txt` | 登录牛客后从浏览器 DevTools 复制 Cookie 头，抓取接口需要登录态 |
| `OPENAI_API_KEY` | DeepSeek 的 API Key，通过环境变量传入 |

```bash
# Linux / macOS
export OPENAI_API_KEY='你的 DeepSeek Key'
# Windows PowerShell
$env:OPENAI_API_KEY='你的 DeepSeek Key'
```

> Key 只从环境变量读取，**不写进代码、不入库**。

### 4. 跑起来

```bash
python spider.py        # 抓岗位 -> output.json
python ai_scorer.py     # 粗筛 + AI 评分 -> scored.json
streamlit run app.py    # 打开筛选界面
```

Windows 用户也可以直接双击 `一键启动.bat`。

## 目录结构

```text
config.py        # 接口地址、请求头、分页参数
spider.py        # 抓取与翻页
ai_scorer.py     # 关键词粗筛 + 公司粒度增量评分 + 容错解析
app.py           # Streamlit 界面
一键启动.bat      # Windows 一键跑全流程
output.json      # 抓取结果（生成物）
scored.json      # 评估结果（生成物）
```

## 🧭 已知局限

这是个人工具，不是生产系统，列清楚比藏着好：

- **Cookie 需要手工更新**：牛客没有公开 API，抓取走的是站点内部接口 `np-api`，
  登录态过期后需要重新复制 Cookie。接口字段变更也会直接导致抓取失败。
- **抓取是「半自动」而非严格爬虫**：分页靠 `config.py` 里的 `PAGE_PARAMS` 驱动，`MAX_PAGES` 默认只翻 3 页。
- **`一键启动.bat` 仅 Windows**：macOS / Linux 请按上面三步手动跑。
- **没有自动化测试**：`ai_scorer.py` 里的 JSON 容错解析、公司粒度去重是最该被测的两段逻辑，
  目前只有人工验证。这是下一个要补的缺口。
- **评分依赖模型判断**：同一份简历重复跑，分数会有小幅波动，不适合当绝对标准。

---

*个人项目，用于把自己从「海投 150 家」里解放出来。*
