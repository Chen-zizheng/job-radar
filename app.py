"""
岗位雷达 · Streamlit 前端
依赖：pip install streamlit
启动：在终端里执行   streamlit run app.py
读取 ai_scorer.py 生成的 scored.json，按公司渲染卡片，支持方向筛选 / 最低分筛选 / 排序。
"""
import json
import os
import streamlit as st

st.set_page_config(page_title="岗位雷达", page_icon="🎯", layout="wide")
st.title("🎯 岗位雷达 · 公司评估")

DATA = "scored.json"
if not os.path.exists(DATA):
    st.warning("还没找到 scored.json。请先在终端运行： python ai_scorer.py")
    st.stop()

with open(DATA, encoding="utf-8") as f:
    data = json.load(f)

all_dirs = sorted({d for r in data for d in r.get("directions_hit", [])})
with st.sidebar:
    st.subheader("筛选")
    dirs_sel = st.multiselect("投递方向", all_dirs, default=all_dirs)
    min_score = st.slider("只看匹配度 >=", 0, 100, 60)
    only_suggest = st.checkbox("只看建议投递的岗位", value=False)
    st.caption("共 %d 家公司" % len(data))


def best_score(r):
    jobs = (r.get("eval") or {}).get("岗位匹配") or []
    return max([j.get("匹配度", 0) for j in jobs], default=0)


def pass_filter(r):
    if dirs_sel and not (set(r.get("directions_hit", [])) & set(dirs_sel)):
        return False
    if best_score(r) < min_score:
        return False
    if only_suggest:
        jobs = (r.get("eval") or {}).get("岗位匹配") or []
        if not any(j.get("投递建议") == "建议" for j in jobs):
            return False
    return True


shown = [r for r in data if pass_filter(r)]
st.subheader("结果：%d 家公司" % len(shown))

for r in shown:
    ev = r.get("eval") or {}
    comp_eval = ev.get("公司评价") or {}
    jobs = ev.get("岗位匹配") or []
    top = best_score(r)

    with st.container(border=True):
        head = st.columns([5, 2])
        tags = "  ".join("[" + d + "]" for d in r.get("directions_hit", []))
        head[0].markdown("### " + r["company"] + "  " + tags)
        head[0].caption("批次：%s ｜ 城市：%s ｜ 网申：%s" % (
            r.get("batch") or "-",
            "、".join(r.get("cities", [])[:6]) or "-",
            r.get("wangshen_time") or "-"))
        head[1].metric("最高匹配度", "%d" % top)

        c1, c2 = st.columns(2)
        with c1:
            if comp_eval.get("生存环境"):
                st.markdown("**生存环境**：" + comp_eval["生存环境"])
            if comp_eval.get("品牌舆论"):
                st.markdown("**品牌舆论**：" + comp_eval["品牌舆论"])
        with c2:
            if comp_eval.get("市场价值"):
                st.markdown("**市场价值**：" + comp_eval["市场价值"])
            if comp_eval.get("风险点"):
                st.markdown("**风险点**：" + comp_eval["风险点"])

        if ev.get("综合建议"):
            st.info("💡 " + ev["综合建议"])

        if jobs:
            with st.expander("查看相关岗位匹配明细（%d）" % len(jobs), expanded=False):
                for j in jobs:
                    badge = {"建议": "🟢", "谨慎": "🟡", "不建议": "🔴"}.get(
                        j.get("投递建议"), "⚪")
                    st.markdown("%s **%s**（%s）— 匹配度 **%s**\n\n- 理由：%s\n- 风险：%s" % (
                        badge, j.get("岗位"), j.get("方向", "-"),
                        j.get("匹配度"), j.get("匹配理由", "-"),
                        j.get("风险点") or "无"))
        else:
            st.caption("AI 未识别出相关岗位。")

        if r.get("apply_link"):
            st.markdown("[去网申](" + r["apply_link"] + ")")
