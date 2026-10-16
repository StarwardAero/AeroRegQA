import streamlit as st


def inject_custom_css():
    st.markdown(
        """
        <style>
        :root {
            --bg-page: #fafafa;
            --bg-surface: rgba(255, 255, 255, 0.78);
            --bg-surface-strong: #ffffff;
            --bg-soft: #f3f4f6;
            --text-primary: #333333;
            --text-secondary: #5f6368;
            --text-muted: #8a8f98;
            --border-soft: rgba(15, 23, 42, 0.08);
            --border-strong: rgba(79, 70, 229, 0.18);
            --brand: #4f46e5;
            --brand-soft: rgba(79, 70, 229, 0.08);
            --shadow-soft: 0 10px 30px rgba(15, 23, 42, 0.05);
            --radius-lg: 24px;
            --radius-md: 18px;
            --radius-sm: 14px;
        }

        #MainMenu,
        footer {
            visibility: hidden;
        }

        /* 修复左侧栏缩进后无法展开的问题：使顶部栏透明但不隐藏，保留左侧展开按钮 */
        header[data-testid="stHeader"] {
            background: transparent !important;
        }

        /* 隐藏右上角的 Github / Deploy / 菜单等默认元素，保持页面极简 */
        [data-testid="stHeaderActionElements"] {
            display: none;
        }

        html,
        body,
        [class*="css"] {
            font-family: "Inter", "Segoe UI", sans-serif;
        }

        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main {
            background: linear-gradient(180deg, #f8f7ff 0%, #fafafa 30%, #f5f5f7 100%);
            color: var(--text-primary);
        }

        .main .block-container {
            max-width: 1320px;
            padding-top: 2.1rem;
            padding-bottom: 2rem;
            padding-left: 2.4rem;
            padding-right: 2.4rem;
        }

        [data-testid="stSidebar"] {
            min-width: 320px;
            max-width: 360px;
            background:
                radial-gradient(circle at top left, rgba(79, 70, 229, 0.08), transparent 34%),
                linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.88) 100%);
            border-right: 1px solid rgba(15, 23, 42, 0.04);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.3rem;
        }

        h1, h2, h3, h4, h5, h6 {
            color: var(--text-primary);
            letter-spacing: -0.02em;
            font-weight: 600;
        }

        h1 {
            font-size: 2.2rem;
            line-height: 1.15;
        }

        h2 {
            font-size: 1.4rem;
        }

        h3 {
            font-size: 1.05rem;
        }

        p,
        li,
        .stMarkdown,
        .stCaption {
            color: var(--text-secondary);
            line-height: 1.7;
        }

        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] .stCaption {
            color: var(--text-secondary);
        }

        hr {
            border: none;
            height: 1px;
            background: rgba(15, 23, 42, 0.05);
            margin: 1.2rem 0 1.4rem;
        }

        .page-hero {
            background: linear-gradient(135deg, rgba(79, 70, 229, 0.06) 0%, rgba(139, 92, 246, 0.04) 50%, rgba(59, 130, 246, 0.03) 100%);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(79, 70, 229, 0.12);
            border-radius: 28px;
            padding: 2.5rem 2.8rem;
            margin-bottom: 2rem;
            box-shadow: 0 8px 40px rgba(79, 70, 229, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
            position: relative;
            overflow: hidden;
        }

        .page-hero::before {
            content: '';
            position: absolute;
            top: -60%;
            right: -20%;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(79, 70, 229, 0.08) 0%, transparent 70%);
            pointer-events: none;
        }

        .page-hero::after {
            content: '';
            position: absolute;
            bottom: -40%;
            left: -10%;
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(139, 92, 246, 0.06) 0%, transparent 70%);
            pointer-events: none;
        }

        .eyebrow {
            margin-bottom: 0.6rem;
            color: var(--brand);
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .hero-title {
            margin: 0;
            color: var(--text-primary);
            font-size: 2.15rem;
            line-height: 1.15;
            font-weight: 650;
        }

        .hero-subtitle {
            margin: 0.85rem 0 0;
            max-width: 760px;
            color: var(--text-secondary);
            font-size: 1rem;
            line-height: 1.75;
        }

        .chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.7rem;
            margin-top: 1rem;
        }

        .stat-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 16px;
            border-radius: 24px;
            font-size: 0.82rem;
            color: var(--text-secondary);
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(15, 23, 42, 0.06);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
        }

        .stat-chip strong {
            color: var(--brand);
            margin-right: 2px;
        }

        .sidebar-brand {
            padding: 1.2rem 0 1.5rem;
            border-bottom: 1px solid rgba(15, 23, 42, 0.06);
            margin-bottom: 1.2rem;
            position: relative;
        }

        .sidebar-brand::after {
            content: '';
            position: absolute;
            bottom: -1px;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, #4f46e5, #7c3aed, transparent);
        }

        .sidebar-title {
            margin: 0;
            color: var(--text-primary);
            font-size: 1.2rem;
            font-weight: 650;
        }

        .sidebar-subtitle {
            margin-top: 0.45rem;
            color: var(--text-secondary);
            font-size: 0.92rem;
            line-height: 1.7;
        }

        .section-label {
            margin: 1.2rem 0 0.55rem;
            color: var(--text-muted);
            font-size: 0.76rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .helper-text {
            margin: -0.15rem 0 0.85rem;
            color: var(--text-muted);
            font-size: 0.88rem;
        }

        .empty-panel {
            background: linear-gradient(135deg, rgba(79, 70, 229, 0.03) 0%, rgba(255, 255, 255, 0.5) 100%);
            border: 2px dashed rgba(79, 70, 229, 0.15);
            border-radius: 20px;
            padding: 2.5rem 2rem;
            text-align: center;
            color: var(--text-secondary);
            line-height: 1.75;
        }

        .empty-panel strong {
            display: block;
            margin-bottom: 0.55rem;
            color: var(--text-primary);
            font-size: 1.02rem;
            font-weight: 600;
        }

        div.stButton > button {
            border-radius: var(--radius-sm);
            border: 1px solid rgba(15, 23, 42, 0.08);
            background: rgba(255, 255, 255, 0.92);
            color: var(--text-primary);
            min-height: 2.85rem;
            padding: 0.68rem 0.95rem;
            box-shadow: none;
            transition: all 0.18s ease;
        }

        div.stButton > button:hover {
            border-color: rgba(79, 70, 229, 0.22);
            color: var(--text-primary);
            background: #ffffff;
            box-shadow: 0 8px 18px rgba(79, 70, 229, 0.08);
            transform: translateY(-1px);
        }

        div.stButton > button[kind="primary"],
        button[kind="primary"],
        [data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, #4f46e5 0%, #6366f1 50%, #7c3aed 100%) !important;
            border: none !important;
            box-shadow: 0 4px 16px rgba(79, 70, 229, 0.3), 0 1px 3px rgba(0, 0, 0, 0.08) !important;
            color: white !important;
            font-weight: 700 !important;
            letter-spacing: 0.02em !important;
        }

        div.stButton > button[kind="primary"]:hover,
        button[kind="primary"]:hover,
        [data-testid="baseButton-primary"]:hover {
            box-shadow: 0 6px 24px rgba(79, 70, 229, 0.4), 0 2px 6px rgba(0, 0, 0, 0.1) !important;
            transform: translateY(-2px) !important;
            background: linear-gradient(135deg, #4338ca 0%, #4f46e5 50%, #6d28d9 100%) !important;
            color: white !important;
        }

        div.stButton > button[kind="secondary"] {
            border-color: rgba(15, 23, 42, 0.08);
            background: #ffffff;
            color: var(--text-primary);
        }

        div.stButton > button[kind="secondary"]:hover {
            border-color: rgba(15, 23, 42, 0.18);
            background: #f9fafb;
            color: var(--text-primary);
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
            transform: translateY(-1px);
        }

        [data-testid="stBaseButton-tertiary"] {
            color: var(--text-secondary);
        }

        .stSelectbox label,
        .stFileUploader label,
        .stChatInput label {
            color: var(--text-secondary);
            font-size: 0.9rem;
        }

        div[data-baseweb="select"] > div,
        .stTextInput input,
        .stTextArea textarea {
            min-height: 3rem;
            border-radius: 14px;
            border-color: rgba(15, 23, 42, 0.08);
            background: rgba(255, 255, 255, 0.88);
        }

        div[data-baseweb="select"] > div:hover,
        .stTextInput input:hover,
        .stTextArea textarea:hover {
            border-color: rgba(79, 70, 229, 0.18);
        }

        [data-testid="stFileUploaderDropzone"] {
            border-radius: 18px;
            border: 1px dashed rgba(79, 70, 229, 0.18);
            background: rgba(255, 255, 255, 0.76);
            padding: 1.2rem;
        }

        [data-testid="stFileUploaderDropzone"]:hover {
            border-color: rgba(79, 70, 229, 0.3);
            background: rgba(79, 70, 229, 0.04);
        }

        [data-testid="stMetric"] {
            padding: 1rem 1.1rem;
            border-radius: 18px;
            border: 1px solid rgba(15, 23, 42, 0.06);
            background: rgba(255, 255, 255, 0.78);
        }

        [data-testid="stMetricLabel"] p,
        [data-testid="stMetricValue"] {
            color: var(--text-primary);
        }

        [data-testid="stExpander"] {
            border: 1px solid rgba(15, 23, 42, 0.06);
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.78);
            overflow: hidden;
        }

        [data-testid="stExpander"] details summary {
            padding-top: 0.2rem;
            padding-bottom: 0.2rem;
        }

        [data-testid="stChatMessage"],
        div[data-testid="stChatMessage"] {
            border-radius: 20px;
            padding: 1rem 1.2rem;
            margin: 0.6rem 0;
            border: 1px solid rgba(15, 23, 42, 0.05);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
            transition: box-shadow 0.2s ease;
        }

        [data-testid="stChatMessage"]:hover,
        div[data-testid="stChatMessage"]:hover {
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
        }

        [data-testid="stChatMessageContent"] {
            padding: 1rem 1.15rem;
            border-radius: 20px;
            border: 1px solid rgba(15, 23, 42, 0.06);
            background: rgba(255, 255, 255, 0.84);
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.03);
        }

        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] {
            background: rgba(243, 244, 246, 0.95);
        }

        [data-testid="stChatInput"] {
            background: transparent;
        }

        [data-testid="stChatInput"] > div {
            border-radius: 20px;
            border: 1px solid rgba(15, 23, 42, 0.08);
            background: rgba(255, 255, 255, 0.92);
            box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
        }

        .source-ref {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            margin-left: 0.35rem;
            padding: 0.2rem 0.5rem;
            border-radius: 999px;
            background: var(--bg-soft);
            color: var(--text-secondary);
            font-size: 0.82rem;
        }

        @keyframes pulse {
            0% { opacity: 0.55; }
            50% { opacity: 1; }
            100% { opacity: 0.55; }
        }

        .thinking-status {
            color: var(--text-muted);
            animation: pulse 2s infinite;
        }

        .stAlert {
            border-radius: 18px;
            border: 1px solid rgba(15, 23, 42, 0.06);
        }

        /* ── Pipeline 可视化 ── */
        .pipeline-container {
            display: flex;
            align-items: center;
            gap: 0;
            padding: 1.2rem 0.5rem;
            overflow-x: auto;
            background: linear-gradient(135deg, rgba(79, 70, 229, 0.03) 0%, rgba(255, 255, 255, 0.5) 100%);
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-soft);
        }

        .pipeline-step {
            display: flex;
            flex-direction: column;
            align-items: center;
            min-width: 100px;
            position: relative;
        }

        .pipeline-step .step-icon {
            width: 52px;
            height: 52px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
            background: white;
            border: 2.5px solid #e2e8f0;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 1;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }

        .pipeline-step.active .step-icon {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            border-color: transparent;
            color: white;
            box-shadow: 0 0 0 6px rgba(79, 70, 229, 0.12), 0 4px 16px rgba(79, 70, 229, 0.25);
            animation: pulse-brand 2s infinite;
        }

        .pipeline-step.done .step-icon {
            background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
            border-color: transparent;
            color: white;
            box-shadow: 0 2px 12px rgba(16, 185, 129, 0.2);
        }

        .pipeline-step .step-label {
            font-size: 0.72rem;
            color: var(--text-secondary);
            margin-top: 6px;
            text-align: center;
            font-weight: 500;
        }

        .pipeline-step.active .step-label {
            color: var(--brand);
            font-weight: 600;
        }

        .pipeline-step.done .step-label {
            color: #10b981;
        }

        .pipeline-arrow {
            width: 36px;
            height: 2.5px;
            background: linear-gradient(90deg, #e2e8f0, #cbd5e1);
            flex-shrink: 0;
            margin-top: -16px;
            border-radius: 2px;
        }

        .pipeline-arrow.done {
            background: linear-gradient(90deg, #10b981, #34d399);
        }

        @keyframes pulse-brand {
            0%, 100% { box-shadow: 0 0 0 6px rgba(79, 70, 229, 0.08); }
            50% { box-shadow: 0 0 0 12px rgba(79, 70, 229, 0.15); }
        }

        /* ── 技术标签 ── */
        .tech-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: default;
        }

        .tech-badge:hover {
            transform: translateY(-2px) scale(1.02);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }

        .tech-badge.rag { background: rgba(79, 70, 229, 0.12); color: #4f46e5; border: 1px solid rgba(79, 70, 229, 0.15); }
        .tech-badge.hybrid { background: rgba(16, 185, 129, 0.12); color: #059669; border: 1px solid rgba(16, 185, 129, 0.15); }
        .tech-badge.rerank { background: rgba(245, 158, 11, 0.12); color: #d97706; border: 1px solid rgba(245, 158, 11, 0.15); }
        .tech-badge.llm { background: rgba(236, 72, 153, 0.12); color: #db2777; border: 1px solid rgba(236, 72, 153, 0.15); }
        .tech-badge.api { background: rgba(59, 130, 246, 0.12); color: #2563eb; border: 1px solid rgba(59, 130, 246, 0.15); }

        /* ── 来源文献卡片 ── */
        .source-card {
            padding: 0.8rem 1.1rem;
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.6);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(15, 23, 42, 0.06);
            border-left: 4px solid var(--brand);
            margin-bottom: 0.6rem;
            font-size: 0.88rem;
            color: var(--text-secondary);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
            transition: all 0.2s ease;
        }

        .source-card:hover {
            transform: translateX(4px);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
        }

        /* ── 消息渐入动画 ── */
        @keyframes fadeSlideIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message-new {
            animation: fadeSlideIn 0.4s ease forwards;
        }

        /* ── 步骤详情面板 ── */
        .step-detail-panel {
            background: rgba(255, 255, 255, 0.6);
            backdrop-filter: blur(8px);
            border-radius: 14px;
            padding: 1rem 1.2rem;
            margin: 0.5rem 0;
            border-left: 4px solid var(--brand);
            font-size: 0.88rem;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.03);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .step-detail-panel:hover {
            transform: translateX(4px);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
        }

        .step-detail-panel.retrieval {
            border-left-color: #10b981;
        }

        .step-detail-panel.rerank {
            border-left-color: #f59e0b;
        }

        .step-detail-panel.judge-pass {
            border-left-color: #10b981;
        }

        .step-detail-panel.judge-fail {
            border-left-color: #ef4444;
        }

        /* ── 知识库统计卡片 ── */
        .kb-stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.6rem;
            margin: 0.5rem 0;
        }

        .kb-stat-card {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(12px);
            border-radius: 16px;
            padding: 1rem;
            text-align: center;
            border: 1px solid rgba(15, 23, 42, 0.06);
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.03);
            transition: transform 0.2s ease;
        }

        .kb-stat-card:hover {
            transform: translateY(-2px);
        }

        .kb-stat-card .stat-value {
            font-size: 1.8rem;
            font-weight: 800;
            background: linear-gradient(135deg, #4f46e5, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .kb-stat-card .stat-label {
            font-size: 0.72rem;
            color: var(--text-muted);
            margin-top: 2px;
        }

        /* ── 上传区域空状态美化 ── */
        .upload-empty-panel {
            padding: 2rem 1.4rem;
            border-radius: var(--radius-lg);
            border: 2px dashed rgba(79, 70, 229, 0.18);
            background: linear-gradient(135deg, rgba(79, 70, 229, 0.03) 0%, rgba(16, 185, 129, 0.03) 100%);
            color: var(--text-secondary);
            text-align: center;
            line-height: 1.75;
            transition: all 0.25s ease;
        }

        .upload-empty-panel:hover {
            border-color: rgba(79, 70, 229, 0.32);
            background: linear-gradient(135deg, rgba(79, 70, 229, 0.06) 0%, rgba(16, 185, 129, 0.06) 100%);
        }

        .upload-empty-panel .upload-icon {
            font-size: 2.2rem;
            margin-bottom: 0.5rem;
        }

        .upload-empty-panel strong {
            display: block;
            margin-bottom: 0.4rem;
            color: var(--text-primary);
            font-size: 1.02rem;
            font-weight: 600;
        }

        .upload-empty-panel .upload-formats {
            display: flex;
            justify-content: center;
            gap: 0.5rem;
            margin-top: 0.6rem;
            flex-wrap: wrap;
        }

        .upload-empty-panel .format-tag {
            padding: 2px 10px;
            border-radius: 12px;
            background: rgba(79, 70, 229, 0.08);
            color: var(--brand);
            font-size: 0.72rem;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
