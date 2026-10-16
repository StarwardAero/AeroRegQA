"""Prompt 工程管理系统 — 统一管理、版本控制、A/B 测试 Prompt 模板。

提供：
- PromptTemplate: 带变量插值、版本管理的 Prompt 模板
- PromptRegistry: Prompt 注册表，统一管理所有模板
- PromptOptimizer: 基于评测结果自动优化 Prompt
- 支持模板继承、组合、条件渲染
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PromptTemplate:
    """Prompt 模板 — 支持变量插值、版本追踪。"""
    name: str
    template: str
    version: str = "1.0"
    description: str = ""
    variables: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def render(self, **kwargs) -> str:
        """渲染模板，插入变量值。"""
        rendered = self.template
        for key, value in kwargs.items():
            rendered = rendered.replace(f"{{{key}}}", str(value))
        return rendered

    def render_safe(self, **kwargs) -> str:
        """安全渲染 — 缺失变量用占位符替代而不报错。"""
        rendered = self.template
        for key, value in kwargs.items():
            rendered = rendered.replace(f"{{{key}}}", str(value))
        # 保留未替换的变量标记
        return rendered

    @property
    def hash(self) -> str:
        """模板内容的 MD5 哈希，用于变更检测。"""
        return hashlib.md5(self.template.encode()).hexdigest()[:8]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "template": self.template,
            "version": self.version,
            "description": self.description,
            "variables": self.variables,
            "hash": self.hash,
        }


class PromptRegistry:
    """Prompt 注册表 — 统一管理所有 Prompt 模板。

    支持：
    - 模板注册与检索
    - 版本历史管理
    - A/B 测试（同名模板多版本）
    - JSON 导入/导出
    """

    def __init__(self) -> None:
        self._templates: dict[str, PromptTemplate] = {}
        self._history: dict[str, list[PromptTemplate]] = {}  # name → version history

    def register(self, template: PromptTemplate) -> None:
        """注册或更新 Prompt 模板。"""
        name = template.name
        # 保存历史版本
        if name in self._templates:
            self._history.setdefault(name, []).append(self._templates[name])
        self._templates[name] = template
        logger.debug(f"[PromptRegistry] 注册模板: {name} v{template.version}")

    def get(self, name: str) -> PromptTemplate | None:
        """获取模板。"""
        return self._templates.get(name)

    def render(self, name: str, **kwargs) -> str:
        """直接渲染指定名称的模板。"""
        template = self.get(name)
        if template is None:
            raise KeyError(f"Prompt 模板不存在: {name}")
        return template.render(**kwargs)

    def list_templates(self) -> list[dict]:
        """列出所有已注册的模板摘要。"""
        return [
            {"name": t.name, "version": t.version, "description": t.description, "hash": t.hash}
            for t in self._templates.values()
        ]

    def get_history(self, name: str) -> list[dict]:
        """获取模板的版本历史。"""
        history = self._history.get(name, [])
        return [t.to_dict() for t in history]

    def export_json(self, filepath: str) -> None:
        """导出所有模板为 JSON 文件。"""
        data = {name: t.to_dict() for name, t in self._templates.items()}
        Path(filepath).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"[PromptRegistry] 导出 {len(data)} 个模板到 {filepath}")

    def import_json(self, filepath: str) -> int:
        """从 JSON 文件导入模板。返回导入数量。"""
        try:
            data = json.loads(Path(filepath).read_text(encoding="utf-8"))
            count = 0
            for name, t_data in data.items():
                template = PromptTemplate(
                    name=t_data["name"],
                    template=t_data["template"],
                    version=t_data.get("version", "1.0"),
                    description=t_data.get("description", ""),
                    variables=t_data.get("variables", []),
                )
                self.register(template)
                count += 1
            logger.info(f"[PromptRegistry] 导入 {count} 个模板")
            return count
        except Exception as exc:
            logger.error(f"[PromptRegistry] 导入失败: {exc}")
            return 0

    def __len__(self) -> int:
        return len(self._templates)


class PromptOptimizer:
    """Prompt 自动优化器 — 基于评测结果提供优化建议。

    分析 Prompt 模板的评测分数，自动生成改进建议。
    """

    def __init__(self, llm_client) -> None:
        self.llm = llm_client

    def analyze_and_suggest(
        self,
        template: PromptTemplate,
        eval_scores: dict,
        sample_outputs: list[str] | None = None,
    ) -> dict:
        """分析模板效果并生成优化建议。

        Args:
            template: 当前 Prompt 模板
            eval_scores: 评测分数（如 {"faithfulness": 0.7, ...}）
            sample_outputs: 使用该模板生成的样本输出

        Returns:
            {
                "analysis": str,
                "suggestions": [str, ...],
                "improved_template": str,
                "expected_improvement": dict,
            }
        """
        samples_text = ""
        if sample_outputs:
            samples_text = "\n".join(
                f"样本{i+1}: {s[:300]}..." for i, s in enumerate(sample_outputs[:3])
            )

        messages = [
            {"role": "system", "content": (
                "你是 Prompt 工程专家。请分析给定 Prompt 模板的不足，"
                "并提出具体的优化建议和改进后的模板。输出 JSON。"
            )},
            {"role": "user", "content": f"""
当前 Prompt 模板：
{template.template[:2000]}

评测分数：
{json.dumps(eval_scores, ensure_ascii=False, indent=2)}

{f"使用该模板的输出样本：{samples_text}" if samples_text else ""}

请分析模板的不足并给出优化建议。重点关注评测分数低的维度。

输出 JSON：
{{
    "analysis": "问题分析",
    "suggestions": ["建议1", "建议2", ...],
    "improved_template": "改进后的完整 Prompt 模板",
    "expected_improvement": {{"faithfulness": "+0.1", "relevance": "+0.05"}}
}}"""},
        ]

        try:
            response = self.llm.chat(
                messages=messages,
                response_format={"type": "json_object"},
            )
            content = response.get("content", "")
            if content:
                return json.loads(content)
        except Exception as exc:
            logger.warning(f"[PromptOptimizer] 优化分析失败: {exc}")

        return {
            "analysis": "分析失败",
            "suggestions": [],
            "improved_template": template.template,
            "expected_improvement": {},
        }
