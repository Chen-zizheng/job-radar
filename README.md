# JobRadar 校招岗位智能雷达

一个自动抓取牛客网校招岗位、结合个人简历进行 AI 智能匹配打分的本地工具。

## 功能亮点

- **自动抓取**：定时从牛客网聚合最新校招岗位信息
- **AI 智能评分**：调用大模型 API，根据你的简历内容对每个岗位进行匹配度打分（0-100）
- **增量评估**：只对新增岗位调用大模型，已评估结果本地缓存，节省 Token 成本
- **实时落盘**：每评估一个岗位即时写入结果，中断不丢失进度
- **可视化筛选**：Streamlit 界面直观展示岗位卡片，支持按分数/公司筛选

## 技术栈

- Python 3.8+
- Streamlit（前端界面）
- OpenAI SDK（兼容 DeepSeek API）
- Requests（网络请求）

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/Chen-zizheng/job-radar.git
cd job-radar

<img width="1262" height="703" alt="image" src="https://github.com/user-attachments/assets/f45fddab-a101-49cf-be1a-923991874f2f" />
<img width="1271" height="703" alt="image" src="https://github.com/user-attachments/assets/e3e0f7cf-1a34-4d07-91c6-0167d045d6b7" />

