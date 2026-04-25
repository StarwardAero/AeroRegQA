import streamlit as st
from ui.state import AppState
from .status_display import render_thinking_status
from .file_uploader import render as render_file_uploader


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
            <p class="eyebrow">AI Knowledge Index</p>
            <h1 class="hero-title">更安静、更专业的低空适航知识工作台</h1>
            <p class="hero-subtitle">
                围绕适航规章、咨询通告与低空政策材料，完成上传、索引、检索与问答。
                当前界面已重构为极简现代风格，帮助你更专注于知识本身。
            </p>
            <div class="chip-row">
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

        with st.chat_message(role):
            st.markdown(content)
            if role == "assistant" and msg.get("metadata", {}).get("sources"):
                sources = msg["metadata"]["sources"]
                st.caption(f"来源文献：{', '.join(sources)}")

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

        with st.spinner("正在检索知识库并生成回答..."):
            response = agent.run(
                question=prompt,
                chat_history=chat_history[:-1],
                stop_event=AppState.get("stop_event"),
                on_step=on_step,
                on_token=on_token,
            )

        final_answer = response.final_answer

        if response.was_interrupted:
            final_answer += "\n\n*[回答已被用户中断]*"

        assistant_placeholder.markdown(final_answer)

        with st.expander("查看 AI 处理过程", expanded=False):
            render_thinking_status(agent_steps)

        if response.sources:
            st.caption(f"来源文献：{', '.join(response.sources)}")

        metadata = {
            "sources": response.sources,
            "iterations": response.total_iterations,
            "interrupted": response.was_interrupted,
        }
        messages.append({"role": "assistant", "content": final_answer, "metadata": metadata})
        AppState.set("messages", messages)
        conversation_manager.add_message(current_cid, "assistant", final_answer, metadata)

        AppState.set("is_generating", False)

        if len(messages) == 2:
            conversation_manager.auto_generate_title(current_cid)

        st.rerun()
