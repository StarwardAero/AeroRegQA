import threading
import streamlit as st
from config.settings import settings

class AppState:
    @staticmethod
    def initialize():
        """初始化所有 session_state 默认值"""
        defaults = {
            "current_conversation_id": None,
            "messages": [],
            "is_generating": False,
            "stop_event": threading.Event(),
            "agent_steps": [],
            "selected_model": settings.LLM_MODEL_NAME,
            "uploaded_files_status": {},
            "knowledge_base_stats": {"total_chunks": 0, "sources": []}
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    @staticmethod
    def get(key, default=None):
        return st.session_state.get(key, default)

    @staticmethod
    def set(key, value):
        st.session_state[key] = value

    @staticmethod
    def request_stop():
        """请求打断生成"""
        st.session_state["stop_event"].set()

    @staticmethod
    def reset_stop():
        """重置打断事件"""
        st.session_state["stop_event"] = threading.Event()
