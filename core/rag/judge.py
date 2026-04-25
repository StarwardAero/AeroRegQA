import json
import re
from dataclasses import dataclass
from utils.logger import get_logger
from .llm_client import LLMClient
from config.prompts import JUDGE_SYSTEM_PROMPT, format_judge_prompt

log = get_logger(__name__)

@dataclass
class JudgeResult:
    is_acceptable: bool
    score: float
    reasoning: str
    suggestions: list[str]

class ResponseJudge:
    def __init__(self, llm_client: LLMClient, threshold: float = 0.7):
        self.llm = llm_client
        self.threshold = threshold

    def evaluate(self, question: str, context: str, answer: str) -> JudgeResult:
        """评估回答质量并返回 JSON 结果"""
        messages = [
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": format_judge_prompt(question, context, answer)}
        ]
        
        try:
            raw_response = self.llm.chat(messages, stream=False)
            result = self._parse_judge_response(raw_response)
            
            # 判断是否接受
            result.is_acceptable = result.score >= self.threshold
            log.info(f"Judge evaluated score: {result.score}. Acceptable: {result.is_acceptable}")
            return result
            
        except Exception as e:
            log.error(f"Judge evaluation failed: {e}")
            return JudgeResult(
                is_acceptable=False,
                score=0.0,
                reasoning=f"裁判模型评估失败: {e}",
                suggestions=["建议重新生成"]
            )

    def _parse_judge_response(self, response_text: str) -> JudgeResult:
        """解析 JSON，容错处理"""
        # 尝试提取被 markdown 代码块包裹的 JSON
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return JudgeResult(
                    is_acceptable=False,  # 稍后根据 score 计算
                    score=float(data.get("score", 0.0)),
                    reasoning=data.get("reasoning", "无理由"),
                    suggestions=data.get("suggestions", [])
                )
            except json.JSONDecodeError as e:
                log.warning(f"Failed to parse JSON from judge: {e}")
                
        # 兜底默认值
        return JudgeResult(False, 0.0, "解析裁判返回格式失败", ["重试一次"])
