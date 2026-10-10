
"""
岗位雷达 · AI 评估器（公司粒度 + 增量更新省Token版）
----------------------------------------------------
相比上一版，新增两件事：
1) 增量更新（INCREMENTAL）：已经评估过的公司直接跳过，不再花钱调 AI，
   只把"新出现的公司"送去评估 -> 省 Token、省时间。
2) 实时落盘：每评估完一家立刻把结果写回 scored.json，
   中途按 Ctrl+C / 断网 / 关机都不会丢失已完成的进度，下次接着跑。

上传 GitHub 前务必处理 API Key（见文件末尾"上传 git 前必做"）。
"""
import os
import json
import time
from collections import OrderedDict
from openai import OpenAI

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCORED_PATH = os.path.join(_BASE_DIR, 'scored.json')

# ---- 配置（当前为"写死模式"，方便你本地直接跑）----
_api_key = os.getenv('OPENAI_API_KEY')#这里填你自己的真实deepseek Api
_base_url = "https://api.deepseek.com/v1"
MODEL = "deepseek-flash"

print('=== 配置自检 ===')
print(f'OPENAI_API_KEY  : {(_api_key[:6] + "..." + _api_key[-4:]) if _api_key else "(空！没读到 key)"}')
print(f'OPENAI_BASE_URL : {_base_url}')
print(f'MODEL           : {MODEL}')
print('================')

if not _api_key:
    raise SystemExit('未配置 API Key。')

# timeout=60 防止单家公司请求时无限卡住；max_retries 让偶发网络抖动自动重试
client = OpenAI(api_key=_api_key, base_url=_base_url, timeout=60.0, max_retries=2)

# ---- 投递方向关键词 ----
TARGET_DIRECTIONS = {
    '测试/测开': ['测试', '测开', '质量', 'qa', 'sdet', 'test'],
    '运维/SRE': ['运维', 'sre', 'devops', '基础架构', '系统', '可靠性', '平台工程'],
    'AI/算法': ['算法', 'ai', '人工智能', '机器学习', '大模型', 'llm', 'agent', 'nlp', '数据'],
    '研发/开发': ['开发', '后端', '前端', '客户端', 'java', 'golang', 'go', '软件', '研发', 'c++', 'c#'],
}

SKIP_NO_TARGET = True   # 旗下没有任何对口方向的岗位的公司，直接跳过（也省 token）
INCREMENTAL = True      # 增量开关：True=只评估新公司；想全量重跑改成 False


def load_resume(path='resume.txt'):
    try:
        with open(os.path.join(_BASE_DIR, path), encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return '（未提供简历，请在 resume.txt 中粘贴你的简历）'


def load_jobs():
    out = os.path.join(_BASE_DIR, 'output.json')
    if os.path.exists(out):
        with open(out, encoding='utf-8') as f:
            return json.load(f)
    from spider import fetch_jobs
    jobs = fetch_jobs()
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    return jobs


def load_scored():
    """读取已评估过的历史结果，用于增量跳过。"""
    if os.path.exists(SCORED_PATH):
        try:
            with open(SCORED_PATH, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def detect_directions(careers):
    hit = {}
    for c in careers:
        cl = (c or '').lower()
        for direction, kws in TARGET_DIRECTIONS.items():
            if any(k in cl for k in kws):
                hit.setdefault(direction, []).append(c)
                break
    return hit


def group_by_company(jobs):
    comp = OrderedDict()
    for j in jobs:
        name = j.get('company') or '未知公司'
        d = comp.setdefault(name, {
            'company': name,
            'batch': j.get('batch', ''),
            'cities': [],
            'wangshen_time': j.get('wangshen_time', ''),
            'apply_link': j.get('apply_link') or j.get('source_information', ''),
            'company_evaluation': j.get('company_evaluation', ''),
            'careers': [],
        })
        for city in (j.get('city') or []):
            if city not in d['cities']:
                d['cities'].append(city)
        if j.get('career') and j['career'] not in d['careers']:
            d['careers'].append(j['career'])
        if not d['company_evaluation'] and j.get('company_evaluation'):
            d['company_evaluation'] = j.get('company_evaluation')
    return comp


def build_prompt(resume, info, directions):
    schema = (
        '请只输出一个 JSON 对象，不要任何解释、不要代码块。结构如下：\n'
        '{\n'
        '  "方向命中": ["命中了你投递方向的career名", ...],\n'
        '  "公司评价": {"生存环境": "...", "品牌舆论": "...", "市场价值": "...", "风险点": "..."},\n'
        '  "岗位匹配": [\n'
        '    {"岗位": "...", "方向": "测试/测开 或 运维/SRE 或 AI/算法 或 研发/开发 或 其他", '
        '"匹配度": 0到100的整数, "匹配理由": "1-2句", "风险点": "1句或空", '
        '"投递建议": "建议/谨慎/不建议"}\n'
        '  ],\n'
        '  "综合建议": "一句话：这家公司值不值得投、优先投哪个岗位"\n'
        '}'
    )
    return (
        '你是校招岗位匹配助手。基于【我的简历】判断这家公司旗下哪些岗位适合我，并对公司本身做评价。\n\n'
        '【我的简历】\n' + resume + '\n\n'
        '【公司信息】\n'
        '公司：' + info['company'] + '\n'
        '批次：' + str(info['batch']) + '\n'
        '城市：' + '、'.join(info['cities']) + '\n'
        '网申时间：' + str(info['wangshen_time']) + '\n'
        '牛客公司简介：' + (info['company_evaluation'] or '无') + '\n'
        '旗下岗位类别：' + str(info['careers']) + '\n\n'
        '（参考）按关键词初筛，可能相关的方向：' + str(directions) + '\n\n'
        '要求：\n'
        '1. 【岗位匹配】只列与我的简历方向相关的岗位，无关的（销售/人事/财务/电气/机械/化工等）不要列；\n'
        '2. 匹配度综合考量技术栈吻合度、学历经验门槛、方向对口度；\n'
        '3. 【公司评价】客观、具体，不空泛；风险点写真实的（如工作地点、行业周期、扩招/缩招）。\n\n'
        + schema
    )


def call_ai(prompt):
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.3,
    )
    text = resp.choices[0].message.content.strip()
    fence = '```'
    if text.startswith(fence):
        text = text.split(fence)[1]
        if text.startswith('json'):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {'解析失败_原文': text}


def _max_score(r):
    jobs = (r.get('eval', {}) or {}).get('岗位匹配', []) or []
    return max([j.get('匹配度', 0) for j in jobs], default=0)


def save_results(results):
    """实时落盘：任何时刻中断，已完成的都在文件里。"""
    results.sort(key=_max_score, reverse=True)
    with open(SCORED_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def score_all(limit=None):
    resume = load_resume()
    jobs = load_jobs()
    companies = group_by_company(jobs)

    # 增量：已评估过的公司名集合，直接跳过，不再花钱
    old_results = load_scored() if INCREMENTAL else []
    done_companies = {r.get('company') for r in old_results}
    results = list(old_results)

    total = len(companies)
    skipped = 0
    new_done = 0
    print(f'\n共 {total} 家公司，其中已评估 {len(done_companies)} 家（将跳过），开始评估新公司...\n')

    for name, info in companies.items():
        if name in done_companies:
            skipped += 1
            continue

        directions = detect_directions(info['careers'])
        if SKIP_NO_TARGET and not directions:
            continue

        if limit and new_done >= limit:
            break

        try:
            ai = call_ai(build_prompt(resume, info, directions))
        except Exception as e:
            ai = {'调用失败': str(e)}

        results.append({
            'company': name,
            'batch': info['batch'],
            'cities': info['cities'],
            'apply_link': info['apply_link'],
            'wangshen_time': info['wangshen_time'],
            'directions_hit': list(directions.keys()),
            'eval': ai,
        })
        new_done += 1

        # 关键：每跑完一家立刻落盘，中断也不丢进度
        save_results(results)
        print(f'[新增 {new_done} | 跳过 {skipped}] {name} 评估完成（已实时保存）')
        time.sleep(1)

    save_results(results)
    print('\n完成。本次新增评估 %d 家，跳过已评估 %d 家，共 %d 家 -> scored.json'
          % (new_done, skipped, len(results)))
    return results


if __name__ == '__main__':
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    score_all(limit=n)

# ============================================================
# 上传 GitHub 前必做（你上一轮让我提醒的）
# 现在 API Key 是明文写死在代码里的，直接 push 会泄露，
# 别人拿去就能刷你的钱（你那张账单 43 万 token 就是例子）。
# 上线前先做下面任一处理：
#   方案A(推荐)：把 _api_key 这一行改回读环境变量：
#       _api_key = (os.getenv('OPENAI_API_KEY') or '').strip()
#       并在项目根目录 .env 里写 OPENAI_API_KEY=sk-xxxx，
#       然后确认 .gitignore 里有一行： .env
#   方案B：push 前把 _api_key 改成 "" 占位，提交后再在本地改回。
# ============================================================