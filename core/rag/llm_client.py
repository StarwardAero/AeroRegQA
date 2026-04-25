import openai
from typing import Generator, Any
from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)

class LLMClient:
    def __init__(self, api_key: str, base_url: str, model_name: str, temperature: float, max_tokens: int):
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    def chat(self, messages: list[dict], stream: bool = False) -> str | Generator:
        """标准对话调用（支持流式和非流式）"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=stream
            )
            
            if stream:
                return (chunk.choices[0].delta.content or "" for chunk in response)
            else:
                return response.choices[0].message.content or ""
                
        except Exception as e:
            log.error(f"LLM API Error: {e}")
            raise e

    def chat_with_callback(self, messages: list[dict], on_token: callable, stop_event: Any) -> str:
        """流式调用，支持逐字回调和外部打断"""
        full_text = ""
        try:
            stream = self.chat(messages, stream=True)
            for token in stream:
                # 检查是否被用户打断
                if stop_event and stop_event.is_set():
                    log.info("LLM generation interrupted by user.")
                    break
                    
                full_text += token
                if on_token:
                    on_token(token)
                    
        except Exception as e:
            log.error(f"LLM Stream API Error: {e}")
            full_text += f"\n[生成出错: {str(e)}]"
            
        return full_text

    @staticmethod
    def create_from_settings(model_type: str = "main") -> "LLMClient":
        """工厂方法：根据配置创建不同用途的模型客户端"""
        if model_type == "main":
            model_name = settings.LLM_MODEL_NAME
        elif model_type == "judge":
            model_name = settings.LLM_JUDGE_MODEL_NAME
        elif model_type == "lite":
            model_name = settings.LLM_LITE_MODEL_NAME
        else:
            model_name = settings.LLM_MODEL_NAME

        return LLMClient(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            model_name=model_name,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
