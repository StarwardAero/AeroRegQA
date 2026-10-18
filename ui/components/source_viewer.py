"""Read-only source viewer, restricted to bundled public documents."""
import streamlit as st
from core.rag.evidence import source_path, original_url


def render_references(sources, references):
    if references:
        st.caption('参考依据（编号对应回答中的引用；页码为 PDF 文件页码）')
        for ref in references:
            name, page = ref['source'], ref.get('page')
            label = f'[{ref["id"]}] {name}' + (f' · 第 {page} 页' if page else '')
            url = original_url(name, page)
            if url:
                st.link_button('查看原文：'+label, url)
            else:
                st.caption(label+'（本地上传资料，暂无公开原文链接）')
            with st.expander(f'证据摘录 [{ref["id"]}]', expanded=False):
                st.text(ref['excerpt'])
    else:
        for source in sources:
            url = original_url(source)
            if url:
                st.link_button('查看原文：'+source, url)
            else:
                st.caption('来源：'+source)


def render_source_page():
    source = st.query_params.get('source')
    if not source:
        return False
    path = source_path(source)
    st.link_button('返回问答', '/')
    if path is None:
        st.error('未找到该原文。')
        return True
    st.title('原文查阅')
    st.write(source)
    st.download_button('下载原文件', path.read_bytes(), file_name=source)
    if path.suffix.lower() == '.pdf':
        import fitz
        with fitz.open(path) as doc:
            try:
                initial = int(st.query_params.get('page', '1'))
            except ValueError:
                initial = 1
            initial = min(max(initial, 1), len(doc))
            number = st.number_input('PDF 页码', min_value=1, max_value=len(doc), value=initial, step=1)
            page = doc[number-1]
            st.caption(f'PDF 第 {number} / {len(doc)} 页')
            st.image(page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).tobytes('png'), use_container_width=True)
            with st.expander('本页原文文本', expanded=True):
                st.text(page.get_text())
    else:
        st.info('此格式请下载原文件查阅。')
    return True
