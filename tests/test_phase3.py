import os
from config.settings import settings
from utils.logger import get_logger
from core.rag.llm_client import LLMClient
from core.conversation.storage import ConversationStorage
from core.conversation.title_generator import TitleGenerator
from core.conversation.manager import ConversationManager

log = get_logger("test_phase3")

def main():
    log.info("Testing Phase 3 (Conversation Persistence)...")
    
    # 1. 初始化
    lite_llm = LLMClient.create_from_settings("lite")
    storage = ConversationStorage(settings.CONVERSATION_DIR)
    title_gen = TitleGenerator(llm_client=lite_llm)
    manager = ConversationManager(storage, title_gen)
    
    # 2. 创建新对话
    conv = manager.create_conversation("deepseek-chat")
    cid = conv.conversation_id
    print(f"Created conversation ID: {cid}")
    
    # 3. 添加消息
    manager.add_message(cid, "user", "请问强化学习在自动驾驶里有什么应用？")
    manager.add_message(cid, "assistant", "强化学习在自动驾驶中常用于决策规划和轨迹控制等场景...", metadata={"sources": ["paper_1.pdf"]})
    
    # 4. 获取历史记录
    history = manager.get_chat_history(cid)
    print(f"Chat History length: {len(history)}")
    
    # 5. 自动生成标题 (调用大模型)
    print("Auto generating title...")
    title = manager.auto_generate_title(cid)
    print(f"Generated Title: {title}")
    
    # 6. 列出所有对话
    all_convs = manager.list_conversations()
    print(f"Total conversations in storage: {len(all_convs)}")
    for c in all_convs:
        print(f" - {c['title']} (Updated: {c['updated_at']})")
    
    # 7. 测试删除
    print("Cleaning up test conversation...")
    manager.delete_conversation(cid)
    
    log.info("Phase 3 Test Completed successfully!")

if __name__ == "__main__":
    main()