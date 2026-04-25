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
            background: var(--bg-page);
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
            padding: 1.8rem 1.9rem;
            margin-bottom: 1.2rem;
            border: 1px solid var(--border-soft);
            border-radius: var(--radius-lg);
            background:
                linear-gradient(180deg, rgba(255,255,255,0.92) 0%, rgba(255,255,255,0.82) 100%);
            box-shadow: var(--shadow-soft);
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
            gap: 0.45rem;
            padding: 0.6rem 0.85rem;
            border-radius: 999px;
            background: var(--bg-soft);
            color: var(--text-secondary);
            font-size: 0.9rem;
            border: 1px solid rgba(15, 23, 42, 0.04);
        }

        .stat-chip strong {
            color: var(--text-primary);
            font-weight: 600;
        }

        .sidebar-brand {
            margin-bottom: 1.3rem;
            padding: 1.25rem 1.1rem;
            border-radius: 20px;
            border: 1px solid rgba(15, 23, 42, 0.05);
            background: rgba(255, 255, 255, 0.78);
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
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
            padding: 1.6rem 1.4rem;
            border-radius: var(--radius-lg);
            border: 1px dashed rgba(15, 23, 42, 0.12);
            background: rgba(255, 255, 255, 0.72);
            color: var(--text-secondary);
            text-align: center;
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
            border-color: rgba(79, 70, 229, 0.22) !important;
            background: var(--brand-soft) !important;
            color: var(--brand) !important;
            font-weight: 600 !important;
        }

        div.stButton > button[kind="primary"]:hover,
        button[kind="primary"]:hover,
        [data-testid="baseButton-primary"]:hover {
            border-color: rgba(79, 70, 229, 0.35) !important;
            background: rgba(79, 70, 229, 0.12) !important;
            color: #4338ca !important;
            box-shadow: 0 8px 18px rgba(79, 70, 229, 0.08) !important;
            transform: translateY(-1px) !important;
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

        [data-testid="stChatMessage"] {
            padding: 0.1rem 0 0.95rem;
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
        </style>
        """,
        unsafe_allow_html=True,
    )
