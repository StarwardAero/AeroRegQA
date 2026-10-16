"""监控 Dashboard — RAG 项目实时运营数据看板。

数据来源：
  - MySQL llm_call_logs:      token 用量、延迟、成本
  - MySQL skill_call_records:  Skill 调用分布、Judge 评分
  - Redis:                     缓存命中率

运行方式：
  streamlit run ui/dashboard.py
"""

import sys
from pathlib import Path

project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
from datetime import datetime, timedelta
from collections import Counter
import json
from pathlib import Path as PathLib

from config.settings import settings
from core.database.models import MySQLClient, LLMCallLog, SkillCallRecord
from core.database.redis_client import RedisClient

# ── 页面配置 ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RAG 系统监控",
    page_icon="📊",
    layout="wide",
)

st.title("📊 RAG 系统运营监控 Dashboard")
st.caption("实时监控系统健康度、成本、质量指标")

# ── 初始化数据库连接 ──────────────────────────────────────────────────
@st.cache_resource
def get_db():
    db = MySQLClient(database_url=settings.DATABASE_URL)
    db.create_tables()
    return db

db = get_db()

# ── 初始化 Redis 连接 ──────────────────────────────────────────────────
@st.cache_resource
def get_redis():
    redis_client = RedisClient(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        default_ttl=settings.REDIS_DEFAULT_TTL,
    )
    return redis_client

redis_client = get_redis()
cache_stats = redis_client.get_cache_stats() if redis_client.is_available else {"hits": 0, "misses": 0, "hit_rate": 0.0, "total": 0}

# ── 辅助函数 ──────────────────────────────────────────────────────────
def query_llm_logs(hours: int = 24) -> list[dict]:
    """查询最近 N 小时的 LLM 调用日志。"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    with db.get_session() as session:
        records = (
            session.query(LLMCallLog)
            .filter(LLMCallLog.timestamp >= cutoff)
            .order_by(LLMCallLog.timestamp.desc())
            .all()
        )
        return [
            {
                "call_type": r.call_type,
                "model_name": r.model_name,
                "prompt_tokens": r.prompt_tokens or 0,
                "completion_tokens": r.completion_tokens or 0,
                "total_tokens": r.total_tokens or 0,
                "duration_ms": r.duration_ms or 0,
                "success": r.success,
            }
            for r in records
        ]

def query_skill_records(hours: int = 24) -> list[dict]:
    """查询最近 N 小时的 Skill 调用记录。"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    with db.get_session() as session:
        records = (
            session.query(SkillCallRecord)
            .filter(SkillCallRecord.timestamp >= cutoff)
            .order_by(SkillCallRecord.timestamp.desc())
            .all()
        )
        return [
            {
                "skill_name": r.skill_name,
                "confidence": r.confidence or 0,
                "routing_method": r.routing_method,
                "duration_ms": r.duration_ms or 0,
                "success": r.success,
                "judge_score": r.judge_score,
            }
            for r in records
        ]

def estimate_cost(prompt_tokens: int, completion_tokens: int, model_name: str) -> float:
    """估算成本（元）。"""
    input_price = settings.MODEL_COST_PER_1M_INPUT.get(model_name, 1.0)
    output_price = settings.MODEL_COST_PER_1M_OUTPUT.get(model_name, 2.0)
    return (prompt_tokens / 1_000_000) * input_price + (completion_tokens / 1_000_000) * output_price


# ── 加载数据 ──────────────────────────────────────────────────────────
st.sidebar.header("⚙️ 时间范围")
hours = st.sidebar.slider("查询最近 N 小时", min_value=1, max_value=168, value=24, step=1)

llm_logs = query_llm_logs(hours)
skill_records = query_skill_records(hours)

total_calls = len(llm_logs)
successful_calls = sum(1 for r in llm_logs if r["success"])
total_prompt_tokens = sum(r["prompt_tokens"] for r in llm_logs)
total_completion_tokens = sum(r["completion_tokens"] for r in llm_logs)
avg_duration_ms = sum(r["duration_ms"] for r in llm_logs) / max(total_calls, 1)

# 成本估算
total_cost = sum(
    estimate_cost(r["prompt_tokens"], r["completion_tokens"], r["model_name"] or "deepseek-chat")
    for r in llm_logs
)

# 按模型分组成本
model_costs: dict[str, float] = {}
model_counts: dict[str, int] = {}
model_tokens: dict[str, int] = {}
for r in llm_logs:
    mn = r["model_name"] or "unknown"
    model_costs[mn] = model_costs.get(mn, 0) + estimate_cost(
        r["prompt_tokens"], r["completion_tokens"], mn
    )
    model_counts[mn] = model_counts.get(mn, 0) + 1
    model_tokens[mn] = model_tokens.get(mn, 0) + r["total_tokens"]

# P99 延迟
durations = sorted([r["duration_ms"] for r in llm_logs if r["duration_ms"] > 0])
p99_duration = durations[int(len(durations) * 0.99)] if len(durations) >= 100 else (durations[-1] if durations else 0)

# Skill 统计
skill_counter = Counter(r["skill_name"] for r in skill_records)
route_method_counter = Counter(r["routing_method"] for r in skill_records)
judge_scores = [r["judge_score"] for r in skill_records if r["judge_score"] is not None]
avg_judge_score = sum(judge_scores) / max(len(judge_scores), 1)

# 按调用类型的分布
call_type_counter = Counter(r["call_type"] for r in llm_logs)


# ── 页面渲染 ──────────────────────────────────────────────────────────
# === 第一行：核心 KPI ===
st.subheader("📈 核心指标")
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("LLM 调用次数", total_calls, help=f"最近 {hours} 小时")
with col2:
    st.metric("成功率", f"{successful_calls / max(total_calls, 1) * 100:.1f}%")
with col3:
    st.metric("平均延迟", f"{avg_duration_ms:.0f} ms")
with col4:
    st.metric("P99 延迟", f"{p99_duration:.0f} ms")
with col5:
    st.metric("预估总成本", f"¥{total_cost:.4f}")
with col6:
    st.metric("缓存命中率", f"{cache_stats['hit_rate']:.1%}",
              help=f"命中 {cache_stats['hits']} / 总计 {cache_stats['total']} 次查询")

# === 第二行：Token 与成本 ===
st.subheader("💰 Token 用量与成本")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("总 Prompt Token", f"{total_prompt_tokens:,}")
with col2:
    st.metric("总 Completion Token", f"{total_completion_tokens:,}")
with col3:
    st.metric("总 Token", f"{total_prompt_tokens + total_completion_tokens:,}")

# 按模型的成本分布
if model_costs:
    st.write("**按模型分组成本**")
    cost_data = {
        "模型": list(model_costs.keys()),
        "调用次数": [model_counts.get(m, 0) for m in model_costs],
        "Token 用量": [f"{model_tokens.get(m, 0):,}" for m in model_costs],
        "预估成本 (¥)": [f"{c:.4f}" for c in model_costs.values()],
    }
    st.dataframe(cost_data, use_container_width=True, hide_index=True)

# === 第三行：Skill 分布 ===
st.subheader("🎯 Skill 调用分布")
col1, col2 = st.columns(2)

with col1:
    if skill_counter:
        st.write("**各 Skill 调用次数**")
        skill_df = {"Skill": list(skill_counter.keys()), "次数": list(skill_counter.values())}
        st.bar_chart(
            data=skill_df, x="Skill", y="次数", use_container_width=True,
            x_label="", y_label="调用次数",
        )
    else:
        st.info("暂无 Skill 调用数据")

with col2:
    if route_method_counter:
        st.write("**路由方式分布**")
        st.bar_chart(
            data={"方式": list(route_method_counter.keys()), "次数": list(route_method_counter.values())},
            x="方式", y="次数", use_container_width=True,
            x_label="", y_label="命中次数",
        )
    else:
        st.info("暂无路由数据")

# === 第四行：调用类型 + 质量 ===
st.subheader("🔍 调用详情")
col1, col2 = st.columns(2)

with col1:
    if call_type_counter:
        st.write("**按调用类型分布**")
        ct_data = {"类型": list(call_type_counter.keys()), "次数": list(call_type_counter.values())}
        st.bar_chart(
            data=ct_data, x="类型", y="次数", use_container_width=True,
            x_label="", y_label="调用次数",
        )

with col2:
    if judge_scores:
        st.metric("平均 Judge 评分", f"{avg_judge_score:.3f}", help="0-1 分，越高越好")
        st.write("**Judge 评分分布**")
        st.bar_chart(
            data={"评分区间": [f"{i/10:.1f}-{(i+1)/10:.1f}" for i in range(10)],
                  "数量": [sum(1 for s in judge_scores if i/10 <= s < (i+1)/10) for i in range(10)]},
            x="评分区间", y="数量", use_container_width=True,
            x_label="", y_label="数量",
        )
    else:
        st.info("暂无 Judge 评分数据（需运行 Agentic RAG 迭代后才会产生）")

# === 评测基线指标（从 eval_baseline.json 读取）===
eval_path = PathLib(settings.BASE_DIR) / "data" / "reports" / "eval_baseline.json"
if eval_path.exists():
    st.subheader("📋 评测基线指标")
    try:
        with open(eval_path, "r", encoding="utf-8") as f:
            eval_data = json.load(f)
        eval_summary = eval_data.get("summary", {})
        eval_meta = eval_data.get("meta", {})
        per_skill = eval_data.get("per_skill", {})

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("忠实度", f"{eval_summary.get('avg_faithfulness', 0):.3f}",
                      help="回答是否忠于检索上下文")
        with col2:
            st.metric("相关性", f"{eval_summary.get('avg_relevance', 0):.3f}",
                      help="回答是否切题")
        with col3:
            st.metric("幻觉率", f"{eval_summary.get('hallucination_rate', 0):.1%}",
                      help="越低越好，0=完全无幻觉", delta_color="inverse")
        with col4:
            st.metric("召回率", f"{eval_summary.get('avg_recall', 0):.3f}",
                      help="检索覆盖了多大比例的关键信息")
        with col5:
            st.metric("引用准确率", f"{eval_summary.get('avg_citation_accuracy', 0):.3f}",
                      help="引用编号是否正确")
        with col6:
            st.metric("综合评分", f"{eval_summary.get('avg_overall', 0):.3f}",
                      help="加权综合得分（含召回率）")

        # 生成时间
        if eval_meta:
            st.caption(f"评测基线生成时间: {eval_meta.get('generated_at', 'N/A')} | "
                      f"测试题数: {eval_meta.get('total_questions', 0)} | "
                      f"评测模型: {eval_meta.get('evaluation_model', 'N/A')}")

        # 按 Skill 维度展示
        if per_skill:
            st.write("**按 Skill 类型评测指标**")
            skill_table = {
                "Skill": list(per_skill.keys()),
                "数量": [per_skill[s]["count"] for s in per_skill],
                "忠实度": [per_skill[s]["avg_faithfulness"] for s in per_skill],
                "相关性": [per_skill[s]["avg_relevance"] for s in per_skill],
                "幻觉率": [round(1 - per_skill[s]["avg_hallucination_free"], 3) for s in per_skill],
                "召回率": [per_skill[s]["avg_recall"] for s in per_skill],
                "综合": [per_skill[s]["avg_overall"] for s in per_skill],
            }
            st.dataframe(skill_table, use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning(f"评测数据加载失败: {e}")
else:
    st.info("📋 暂无评测基线数据。运行 `python -m core.evaluation.run_eval` 生成评测报告。")

# === 模型路由策略说明 ===
with st.expander("🧠 模型路由策略说明"):
    st.markdown("""
    | Skill 类型 | 模型层级 | 使用模型 | 原因 |
    |-----------|---------|---------|------|
    | chitchat / definition / concept | **Lite** | DeepSeek V4 | 简单任务，V4 即可应对 |
    | rag / comparison / procedure / compliance | **Main** | DeepSeek V4 | 常规 RAG 问答 |
    | summary / multi_doc / export / judge | **Reasoner** | DeepSeek R1 | 复杂推理，需深度思考 |

    **成本对比**（估算）：
    - DeepSeek V4 (`deepseek-chat`): 输入 ¥2/百万token, 输出 ¥8/百万token
    - DeepSeek R1 (`deepseek-reasoner`): 输入 ¥4/百万token, 输出 ¥16/百万token
    """)

# === 数据新鲜度 ===
st.caption(f"数据更新时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC | 时间范围: 最近 {hours} 小时 | 数据来源: MySQL `llm_call_logs` + `skill_call_records`")
