"""对比分析 Skill — 处理多法规、多条款之间的差异对比。

适用场景：
- 不同法规对同一事项的规定差异
- 新旧版本法规的变化对比
- 不同类别无人机的要求差异
"""

from __future__ import annotations

from typing import Callable

from core.skills.base_skill import BaseSkill, SkillResult
from core.skills.utils import emit_agent_step, stream_checked_answer, unique_source_files, validate_citations

EVTOL_UAV_CORE_SOURCES = [
    "EASA-SC-VTOL-02-small-category-VTOL-capable-aircraft-2024.pdf",
    "FAA-Integration-of-Powered-Lift-Final-Rule-2024.pdf",
    "FAA-Urban-Air-Mobility-Concept-of-Operations-2.0-2023.pdf",
    "CAAC-CCAR-92-民用无人驾驶航空器运行安全管理规则-2024.pdf",
]


class ComparisonSkill(BaseSkill):
    """对比分析 Skill：多法规/多条款的结构化对比。"""

    def __init__(self, llm_client, retriever) -> None:
        self._llm = llm_client
        self._retriever = retriever

    @property
    def name(self) -> str:
        return "comparison"

    @property
    def description(self) -> str:
        return "对比分析不同法规、条款、类别之间的差异和异同"

    @property
    def keywords(self) -> list[str]:
        return [
            "对比", "比较", "区别", "差异", "不同", "异同",
            "相同", "相似", "变化", "修改", "新旧", "vs",
            "哪个", "优劣", "各自", "分别",
        ]

    def execute(
        self,
        question: str,
        chat_history: list[dict] | None = None,
        stop_event=None,
        on_step: Callable | None = None,
        on_token: Callable | None = None,
    ) -> SkillResult:
        emit_agent_step(on_step, "comparison_retrieve", "正在检索对比相关的法规条款...")

        # eVTOL 载人运行 vs 传统无人机是展示型核心问题：
        # 只从四份核心资料中取片段，避免 CCAR-27、Vertiport Design 等邻近资料污染答案。
        if self._retriever.is_evtol_uav_comparison_query(question):
            chunks = self._retriever.retrieve_from_sources(
                question,
                EVTOL_UAV_CORE_SOURCES,
                per_source=3,
            )
        else:
            # 多维度检索 — 对比类问题需要更多上下文
            chunks = self._retriever.retrieve(question, top_k=8, deduplicate=True)

        if not chunks:
            return SkillResult(
                answer="未找到可对比的相关法规内容。",
                sources=[],
                skill_name=self.name,
                confidence=0.2,
            )

        context = self._retriever.format_context_grouped(chunks)

        emit_agent_step(on_step, "comparison_analyze", "正在进行结构化对比分析...")

        system_prompt = (
            "你是民航法规对比分析专家。请基于参考资料对用户问题中涉及的对象进行系统性对比。\n\n"
            "要求：\n"
            "1. 如果用户指定了对比维度，必须严格按用户指定维度组织回答，不要自行改成其他维度。若用户问 eVTOL 载人运行与传统无人机在适航审定、运行安全、路径规划上的不同，默认按「风险对象、审定重点、运行环境、导航路径规划影响」四个维度回答。\n"
            "2. 使用 **Markdown 表格** 呈现核心对比。对 eVTOL / powered-lift / VCA 与传统无人机分别说明。\n"
            "3. 表格列必须包含：维度、eVTOL 载人运行、传统无人机、法规/官方资料明文要求、工程影响。\n"
            "4. 每个对比结论必须标注来源引用编号 [n]。\n"
            "5. 必须明确区分「法规/官方资料明文要求」与「基于官方资料得出的工程影响」。工程影响不能写成法规强制条文。\n"
            "6. 如果用户点名了具体资料，应优先使用这些点名资料；不要用相邻但未点名的资料（如 CCAR-27、CCAR-29、Vertiport Design、U-space、UTM）替代点名资料，除非用户明确要求补充。\n"
            "7. 回答开头先简短说明已检索到哪些点名资料；如某份点名资料确实未出现在参考资料中，再标注「资料未覆盖」。\n"
            "8. 在表格后给出简要总结分析。\n"
            "9. 不要编造内容，严格基于参考资料。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"参考资料：\n{context}\n\n问题：{question}"},
        ]

        answer = self._llm.chat(messages)
        answer, citation_result = validate_citations(answer, chunks, self._llm, question)
        emit_agent_step(on_step, "citation_check", f"引用校验: {citation_result.valid_citations}/{citation_result.total_citations}", citation_result.__dict__)
        stream_checked_answer(answer, on_token, stop_event)

        sources = unique_source_files(chunks)

        return SkillResult(
            answer=answer,
            sources=sources,
            skill_name=self.name,
            confidence=0.8,
            metadata={"chunks_used": len(chunks), "citation_check": citation_result.__dict__},
        )
