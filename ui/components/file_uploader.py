import streamlit as st
from config.settings import settings
from ui.state import AppState
from core.parser.parser_factory import ParserFactory
from core.chunker.semantic_chunker import SemanticChunker
from utils.file_utils import safe_save_uploaded_file
from utils.logger import get_logger

log = get_logger(__name__)


def render(services):
    """渲染文件上传与知识库构建组件"""
    st.markdown('<p class="section-label">知识库扩充</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="helper-text">上传规章、通告、政策文件后，系统会自动完成解析、分块与向量化入库。</p>',
        unsafe_allow_html=True,
    )

    with st.expander("添加文献资料", expanded=False):
        uploaded_files = st.file_uploader(
            "支持拖拽多文件，上传后自动解析并写入知识库",
            type=["pdf", "docx", "txt", "md", "csv"],
            accept_multiple_files=True,
        )

        st.caption("支持格式：PDF、DOCX、TXT、Markdown、CSV。")

        if uploaded_files:
            if st.button("开始解析并入库", type="primary", use_container_width=True):
                if AppState.get("is_generating"):
                    st.warning("正在生成对话回答，请稍后再试！")
                    return

                AppState.set("is_generating", True)

                chroma_store = services.get("chroma_store")
                chunker = SemanticChunker(
                    chunk_size=settings.CHUNK_SIZE,
                    chunk_overlap=settings.CHUNK_OVERLAP,
                )

                progress_bar = st.progress(0)
                status_text = st.empty()
                total_files = len(uploaded_files)
                total_chunks_added = 0

                for i, file in enumerate(uploaded_files):
                    status_text.text(f"[{i+1}/{total_files}] 正在处理: {file.name}")

                    try:
                        saved_path = safe_save_uploaded_file(
                            file,
                            settings.UPLOAD_DIR,
                            max_size_bytes=settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024,
                        )

                        status_text.text(f"[{i+1}/{total_files}] 正在解析文档内容: {file.name}")
                        markdown_text = ParserFactory.parse_file(saved_path)

                        status_text.text(f"[{i+1}/{total_files}] 正在进行学术语义分块: {file.name}")
                        source_name = saved_path.name
                        chunks = chunker.chunk_document(markdown_text, source_name)

                        status_text.text(f"[{i+1}/{total_files}] 正在向量化并写入知识库: {source_name}")
                        chroma_store.delete_by_source(source_name)
                        added_count = chroma_store.add_documents(chunks)
                        total_chunks_added += added_count
                    except Exception as e:
                        log.error(f"处理文件 {file.name} 失败: {e}")
                        st.error(f"❌ 处理文件 {file.name} 失败: {e}")

                    progress_bar.progress((i + 1) / total_files)

                status_text.text("全部处理完成")
                st.success(
                    f"已完成 {total_files} 个文件的入库处理，新增 {total_chunks_added} 个文本块。"
                )
                AppState.set("is_generating", False)

                st.rerun()
        else:
            st.markdown(
                """
                <div class="empty-panel" style="text-align:center;">
                    <div style="font-size:2.5rem; margin-bottom:0.5rem;">📂</div>
                    <strong>拖拽或选择待入库文档</strong><br>
                    <span style="color:var(--text-muted); font-size:0.85rem;">
                        支持 PDF、DOCX、TXT、Markdown、CSV 格式<br>
                        上传后自动完成解析→分块→向量化入库
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
