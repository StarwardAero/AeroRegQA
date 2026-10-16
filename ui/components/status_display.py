"""Agent Pipeline 可视化 — 展示检索增强生成处理流程。"""

import streamlit as st


def render_thinking_status(agent_steps: list):
    """渲染 AI Agent 处理流程的 Pipeline 可视化。"""
    if not agent_steps:
        return

    # Pipeline 阶段定义
    pipeline_stages = [
        ("rewrite", "✏️", "问题重写"),
        ("retrieve", "🔀", "混合检索"),
        ("generate", "📝", "生成草稿"),
        ("judge", "⚖️", "质量评估"),
        ("generate_final", "✅", "最终输出"),
    ]

    completed_types = {s.step_type for s in agent_steps}
    last_type = agent_steps[-1].step_type if agent_steps else ""

    # 确定最远完成的阶段索引
    current_idx = -1
    for i, (stype, _, _) in enumerate(pipeline_stages):
        if stype in completed_types:
            current_idx = i

    # ── Pipeline 图 ──
    html = '<div class="pipeline-container">'
    for i, (stype, icon, label) in enumerate(pipeline_stages):
        if i > 0:
            arrow_cls = "done" if i <= current_idx else ""
            html += f'<div class="pipeline-arrow {arrow_cls}"></div>'

        if stype in completed_types and stype != last_type:
            cls = "done"
        elif stype == last_type:
            cls = "done" if stype == "generate_final" else "active"
        else:
            cls = ""

        html += (
            f'<div class="pipeline-step {cls}">'
            f'<div class="step-icon">{icon}</div>'
            f'<div class="step-label">{label}</div>'
            f'</div>'
        )
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    # ── 步骤详情 ──
    for step in agent_steps:
        t = step.step_type
        ms = step.duration_ms
        time_html = f'<span style="float:right;color:var(--text-muted);font-size:0.8rem">{ms}ms</span>'

        if t == "rewrite":
            st.markdown(
                f'<div class="step-detail-panel">'
                f'✏️ <strong>问题理解</strong>：重写为 <code>{step.output_data}</code>{time_html}</div>',
                unsafe_allow_html=True,
            )
        elif t == "retrieve":
            sources = step.metadata.get("sources", [])
            src_text = ", ".join(sources) if sources else "无"
            st.markdown(
                f'<div class="step-detail-panel retrieval">'
                f'🔀 <strong>混合检索</strong>（BM25 + 向量 + RRF 融合 → Rerank 重排序）：'
                f'找到 {step.output_data} 相关片段'
                f'<br><span style="color:var(--text-muted);font-size:0.82rem">来源：{src_text}</span>'
                f'{time_html}</div>',
                unsafe_allow_html=True,
            )
        elif t == "generate":
            st.markdown(
                f'<div class="step-detail-panel">'
                f'📝 <strong>草稿生成</strong>：基于检索结果构建回答{time_html}</div>',
                unsafe_allow_html=True,
            )
        elif t == "judge":
            is_pass = "True" in step.output_data
            pcls = "judge-pass" if is_pass else "judge-fail"
            verdict = "✅ 通过" if is_pass else "🔄 未通过，继续迭代"
            st.markdown(
                f'<div class="step-detail-panel {pcls}">'
                f'⚖️ <strong>LLM-as-Judge</strong>：{verdict}{time_html}</div>',
                unsafe_allow_html=True,
            )
        elif t == "generate_final":
            st.markdown(
                f'<div class="step-detail-panel" style="border-left-color:#10b981;">'
                f'✅ <strong>最终输出</strong>：回答整理完成{time_html}</div>',
                unsafe_allow_html=True,
            )
