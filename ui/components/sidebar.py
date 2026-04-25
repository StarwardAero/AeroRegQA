import streamlit as st
from ui.state import AppState
from config.settings import settings


def render(conversation_manager, services):
    """渲染侧边栏"""
    st.markdown(
        """
        <div class="sidebar-brand">
            <p class="eyebrow">Workspace</p>
            <h1 class="sidebar-title">低空适航知识索引</h1>
            <p class="sidebar-subtitle">
                面向适航规章、AC 通告与低空政策文献的知识问答工作台。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<p class="section-label">模型配置</p>', unsafe_allow_html=True)
    available_models = [settings.LLM_MODEL_NAME, "deepseek-reasoner", "gpt-4o"]
    selected_model = st.selectbox(
        "当前模型",
        available_models,
        index=available_models.index(settings.LLM_MODEL_NAME) if settings.LLM_MODEL_NAME in available_models else 0,
        label_visibility="collapsed",
    )
    AppState.set("selected_model", selected_model)
    st.caption("当前问答将使用所选模型完成检索增强生成。")

    st.markdown('<p class="section-label">会话历史</p>', unsafe_allow_html=True)

    if st.button("新建对话", use_container_width=True, type="primary"):
        new_conv = conversation_manager.create_conversation(selected_model)
        AppState.set("current_conversation_id", new_conv.conversation_id)
        AppState.set("messages", [])
        st.rerun()

    conversations = conversation_manager.list_conversations()
    if not conversations:
        st.markdown(
            """
            <div class="empty-panel">
                <strong>还没有历史对话</strong>
                新建一个会话后，即可开始围绕适航规章与低空政策材料进行问答。
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        with st.container(height=300):
            for conv in conversations:
                cid = conv["id"]
                title = conv["title"]
                updated = conv["updated_at"][:10]
                is_active = cid == AppState.get("current_conversation_id")
                btn_label = f"{title} · {updated}"

                col1, col2 = st.columns([5, 1])
                with col1:
                    if st.button(
                        btn_label,
                        key=f"btn_{cid}",
                        help="点击载入该会话",
                        use_container_width=True,
                        type="primary" if is_active else "secondary",
                    ):
                        AppState.set("current_conversation_id", cid)
                        full_conv = conversation_manager.get_conversation(cid)
                        if full_conv:
                            AppState.set("messages", [m.to_dict() for m in full_conv.messages])
                        st.rerun()
                with col2:
                    if st.button("删除", key=f"del_{cid}", help="删除该对话"):
                        conversation_manager.delete_conversation(cid)
                        if is_active:
                            AppState.set("current_conversation_id", None)
                            AppState.set("messages", [])
                        st.rerun()

    st.markdown('<p class="section-label">知识库状态</p>', unsafe_allow_html=True)
    chroma_store = services.get("chroma_store")
    if chroma_store:
        stats = chroma_store.get_collection_stats()
        sources = chroma_store.list_sources()

        st.metric(label="已索引文本块", value=stats.get("total_chunks", 0))
        st.caption("上传的文档会被解析、分块并写入向量索引。")

        with st.expander("查看已收录文献", expanded=False):
            if sources:
                for source in sources:
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.markdown(source)
                    with col2:
                        if st.button("移除", key=f"del_src_{source}", help=f"从知识库移除 {source}"):
                            chroma_store.delete_by_source(source)
                            st.toast(f"已移除文献: {source}")
                            st.rerun()
            else:
                st.caption("知识库为空，请先上传文献。")
