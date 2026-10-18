import streamlit as st
from ui.state import AppState
from .status_display import render_thinking_status
from .file_uploader import render as render_file_uploader
from core.rag.agent import AgentStep
from .source_viewer import render_references


def render(conversation_manager, agent, services):
    """渲染主聊天区域"""

    current_cid = AppState.get("current_conversation_id")
    messages = AppState.get("messages", [])

    active_model = AppState.get("selected_model", "未选择模型")
    sources_count = len(services.get("chroma_store").list_sources()) if services.get("chroma_store") else 0
    chunks_count = 0
    if services.get("chroma_store"):
        chunks_count = services["chroma_store"].get_collection_stats().get("total_chunks", 0)

    st.markdown(
        f"""
        <section class="page-hero">
            <p class="eyebrow">Agentic RAG · Knowledge Workspace</p>
            <h1 class="hero-title">低空适航智能知识工作台</h1>
            <p class="hero-subtitle">
                基于 Agentic RAG 架构，融合混合检索、语义重排序与多轮推理，
                围绕适航规章、咨询通告与低空政策文献提供专业级问答服务。
            </p>
            <div class="chip-row" style="margin-top:0.8rem;">
                <span class="tech-badge rag">🤖 Agentic RAG</span>
                <span class="tech-badge hybrid">🔀 Hybrid Search</span>
                <span class="tech-badge rerank">📊 Rerank</span>
                <span class="tech-badge llm">🧠 来源溯源</span>
                <span class="tech-badge api">⚡ FastAPI</span>
            </div>
            <div class="chip-row" style="margin-top:0.5rem;">
                <span class="stat-chip"><strong>模型</strong>{active_model}</span>
                <span class="stat-chip"><strong>文献</strong>{sources_count} 份</span>
                <span class="stat-chip"><strong>索引块</strong>{chunks_count} 条</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    render_file_uploader(services)

    if not current_cid:
        st.markdown(
            """
            <div class="empty-panel">
                <strong>从左侧新建或选择一个对话</strong>
                进入会话后，你可以基于已上传的知识文档提出问题，系统会结合检索结果生成回答。
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        msg_index = messages.index(msg)

        with st.chat_message(role):
            st.markdown(content)
            if role == "assistant" and msg.get("metadata", {}).get("sources"):
                sources = msg["metadata"]["sources"]
                render_references(sources, msg['metadata'].get('references', []))

            # ── 用户反馈按钮（仅 AI 回答） ──
            if role == "assistant" and msg.get("content"):
                feedback_key = f"feedback_{current_cid}_{msg_index}"
                fb_col1, fb_col2, fb_col3 = st.columns([1, 1, 8])
                with fb_col1:
                    if st.button("👍", key=f"{feedback_key}_up", help="回答有帮助"):
                        services["mysql_client"].save_feedback(
                            conversation_id=current_cid,
                            rating=5,
                            comment="用户点赞",
                        )
                        st.toast("感谢反馈！👍", icon="✅")
                with fb_col2:
                    if st.button("👎", key=f"{feedback_key}_down", help="回答需要改进"):
                        services["mysql_client"].save_feedback(
                            conversation_id=current_cid,
                            rating=1,
                            comment="用户点踩",
                        )
                        st.toast("感谢反馈，我们会持续改进！👎", icon="📝")

    prompt = st.chat_input("请输入与你的适航规章、政策文本或知识库内容相关的问题")

    if prompt:
        if AppState.get("is_generating"):
            st.warning("上一个问题正在回答中，请稍后！")
            return

        with st.chat_message("user"):
            st.markdown(prompt)

        messages.append({"role": "user", "content": prompt})
        AppState.set("messages", messages)
        conversation_manager.add_message(current_cid, "user", prompt)

        AppState.set("is_generating", True)
        AppState.reset_stop()

        assistant_placeholder = st.chat_message("assistant").empty()
        agent_steps = []
        token_accumulator = []

        def on_step(step):
            agent_steps.append(step)

        def on_token(token):
            token_accumulator.append(token)
            assistant_placeholder.markdown("".join(token_accumulator) + "▌")

        chat_history = conversation_manager.get_chat_history(current_cid, last_n=10)

        effective_history = chat_history[:-1]

        with st.spinner("正在理解问题、检索知识库并生成回答..."):
            intent_router = services.get("intent_router")
            skill_registry = services.get("skill_registry")

            if intent_router and skill_registry:
                routing_decision = intent_router.route(prompt, effective_history)
                routing_detail = (
                    f"路由至 Skill: {routing_decision.skill_name} "
                    f"(置信度: {routing_decision.confidence:.2f}, 方式: {routing_decision.method})"
                )
                on_step(AgentStep("routing", prompt, routing_detail, 0))

                skill = skill_registry.get(routing_decision.skill_name)
                if not skill:
                    skill = skill_registry.get(skill_registry.default_skill_name)

                result = skill.execute(
                    question=prompt,
                    chat_history=effective_history,
                    stop_event=AppState.get("stop_event"),
                    on_step=on_step,
                    on_token=on_token,
                )

                final_answer = result.answer
                sources = result.sources
                iterations = result.iterations
                was_interrupted = result.was_interrupted
                skill_name = result.skill_name or routing_decision.skill_name
            else:
                response = agent.run(
                    question=prompt,
                    chat_history=effective_history,
                    stop_event=AppState.get("stop_event"),
                    on_step=on_step,
                    on_token=on_token,
                )
                final_answer = response.final_answer
                sources = response.sources
                iterations = response.total_iterations
                was_interrupted = response.was_interrupted
                skill_name = "rag"

        if was_interrupted:
            final_answer += "\n\n*[回答已被用户中断]*"

        assistant_placeholder.markdown(final_answer)

        with st.expander("查看 AI 处理过程", expanded=False):
            render_thinking_status(agent_steps)

        references = []
        for step in agent_steps:
            if step.step_type == 'citation_check':
                references = step.metadata.get('details', {}).get('references', [])
        if sources:
            render_references(sources, references)

        metadata = {
            "sources": sources,
            "references": references,
            "iterations": iterations,
            "interrupted": was_interrupted,
            "skill_name": skill_name,
        }
        messages.append({"role": "assistant", "content": final_answer, "metadata": metadata})
        AppState.set("messages", messages)
        conversation_manager.add_message(current_cid, "assistant", final_answer, metadata)

        AppState.set("is_generating", False)

        if len(messages) == 2:
            conversation_manager.auto_generate_title(current_cid)

        st.rerun()
