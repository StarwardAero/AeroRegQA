"""导出报告 Skill — 将法规分析结果整理为结构化报告。

适用场景：
- 用户需要某个主题的综合分析报告
- 法规合规性审查报告
- 多文档联合分析报告
"""

from __future__ import annotations

from typing import Callable

from core.skills.base_skill import BaseSkill, SkillResult
from core.skills.utils import emit_agent_step, stream_checked_answer, unique_source_files, validate_citations


class ExportSkill(BaseSkill):
    """导出报告 Skill：生成结构化的法规分析报告。"""

    def __init__(self, llm_client, retriever) -> None:
        self._llm = llm_client
        self._retriever = retriever

    @property
    def name(self) -> str:
        return "export"

    @property
    def description(self) -> str:
        return "生成结构化的法规分析报告、综合评估报告"

    @property
    def keywords(self) -> list[str]:
        return [
            "报告", "总结报告", "分析报告", "综合分析", "生成报告",
            "导出", "整理", "汇总", "评估报告", "审查报告",
        ]

    def execute(
        self,
        question: str,
        chat_history: list[dict] | None = None,
        stop_event=None,
        on_step: Callable | None = None,
        on_token: Callable | None = None,
    ) -> SkillResult:
        emit_agent_step(on_step, "export_retrieve", "正在检索报告相关资料...")

        # 报告类需要更广泛的上下文
        chunks = self._retriever.retrieve(question, top_k=10, deduplicate=True)
        if not chunks:
            return SkillResult(
                answer="未找到足够的资料来生成报告。",
                sources=[],
                skill_name=self.name,
                confidence=0.2,
            )

        context = self._retriever.format_context_grouped(chunks)

        emit_agent_step(on_step, "export_generate", "正在生成结构化报告...")

        system_prompt = (
            "你是民航法规高级分析师。请根据参考资料，为用户问题生成一份结构化分析报告。\n\n"
            "报告结构要求：\n"
            "# 分析报告：{主题}\n\n"
            "## 摘要\n"
            "（200字以内概述核心结论）\n\n"
            "## 1. 背景\n"
            "（问题背景与分析范围）\n\n"
            "## 2. 核心内容\n"
            "（分点论述，每点标注引用 [n]）\n\n"
            "## 3. 关键发现\n"
            "（列出重要发现和注意事项）\n\n"
            "## 4. 结论与建议\n"
            "（总结性结论和可操作建议）\n\n"
            "## 参考来源\n"
            "（列出引用的文件来源）\n\n"
            "要求：\n"
            "- 论述严谨，引用明确。\n"
            "- 不编造内容，所有结论基于参考资料。\n"
            "- 对资料未覆盖的方面明确说明。\n"
            "- 适当使用表格和列表增强可读性。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"参考资料：\n{context}\n\n报告主题：{question}"},
        ]

        answer = self._llm.chat(messages)
        answer, citation_result = validate_citations(answer, chunks)
        emit_agent_step(on_step, "citation_check", f"引用校验: {citation_result.valid_citations}/{citation_result.total_citations}", citation_result.__dict__)
        stream_checked_answer(answer, on_token, stop_event)

        sources = unique_source_files(chunks)

        return SkillResult(
            answer=answer,
            sources=sources,
            skill_name=self.name,
            confidence=0.85,
            metadata={"chunks_used": len(chunks), "report_type": "analysis", "citation_check": citation_result.__dict__},
        )
