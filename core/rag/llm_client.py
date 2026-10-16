import openai
from typing import Generator, Any
from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)

class LLMClient:
    def __init__(self, api_key: str, base_url: str, model_name: str, temperature: float, max_tokens: int):
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=120.0)
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    def chat(self, messages: list[dict], stream: bool = False, response_format: dict = None) -> str | Generator:
        """标准对话调用（支持流式和非流式）。

        Args:
            messages: 对话消息列表
            stream: 是否流式输出
            response_format: OpenAI 响应格式（如 {"type": "json_object"}）

        Returns:
            非流式: 返回纯文本字符串
            流式: 返回 Generator[str]

        如需获取 token 用量，请使用 chat_with_usage()
        """
        try:
            kwargs = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": stream,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = self.client.chat.completions.create(**kwargs)

            if stream:
                return (chunk.choices[0].delta.content or "" for chunk in response)
            else:
                return response.choices[0].message.content or ""

        except Exception as e:
            log.error(f"LLM API Error: {e}")
            raise e

    def chat_with_usage(self, messages: list[dict], response_format: dict = None) -> dict:
        """标准对话调用，返回 content + token 用量。

        Args:
            messages: 对话消息列表
            response_format: OpenAI 响应格式

        Returns:
            {
                "content": str,           # 回复文本
                "model": str,             # 使用的模型名
                "prompt_tokens": int,     # 输入 token 数
                "completion_tokens": int, # 输出 token 数
                "total_tokens": int,      # 总 token 数
            }
        """
        try:
            kwargs = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = self.client.chat.completions.create(**kwargs)
            usage = response.usage
            return {
                "content": response.choices[0].message.content or "",
                "model": self.model_name,
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            }
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
        """工厂方法：根据配置创建不同用途的模型客户端。

        支持类型（DeepSeek V4 + R1）：
          - "main":     主模型（常规问答，DeepSeek V4）
          - "judge":    Judge评估模型（DeepSeek R1）
          - "lite":     轻量模型（简单任务，DeepSeek V4）
          - "reasoner": 推理模型（复杂分析，DeepSeek R1）
        """
        model_map = {
            "main":     settings.LLM_MODEL_NAME,
            "judge":    settings.LLM_JUDGE_MODEL_NAME,
            "lite":     settings.LLM_LITE_MODEL_NAME,
            "reasoner": settings.LLM_REASONER_MODEL_NAME,
        }
        model_name = model_map.get(model_type, settings.LLM_MODEL_NAME)

        return LLMClient(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            model_name=model_name,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
