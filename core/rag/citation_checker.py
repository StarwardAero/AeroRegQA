"""引用检查器 — 验证生成回答中的引用编号是否真实存在于检索结果中。

全链路幻觉抑制 — 后端防线之一。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class CitationCheckResult:
    """引用检查结果。"""
    is_valid: bool                     # 所有引用是否均合法
    total_citations: int               # 回答中的引用总数
    valid_citations: int               # 合法引用数
    invalid_citations: list[str]       # 无效引用列表（如 "[7]" 但只有 5 个 chunk）
    citation_rate: float               # 引用覆盖率（引用了多少个不同来源）
    details: dict = field(default_factory=dict)


class CitationChecker:
    """引用合法性检查器。

    检查生成回答中引用的 [1], [2] 等编号是否在检索结果范围内，
    防止 LLM 编造不存在的引用编号。
    """

    # 匹配 [1], [2][3], [12] 等引用模式
    CITATION_PATTERN = re.compile(r'\[(\d+)\]')

    def check(self, answer: str, num_chunks: int) -> CitationCheckResult:
        """检查回答中的引用编号合法性。

        Args:
            answer: LLM 生成的回答文本
            num_chunks: 检索返回的 chunk 数量（引用编号范围 1~num_chunks）

        Returns:
            CitationCheckResult
        """
        # 提取所有引用编号
        cited_numbers = [int(m) for m in self.CITATION_PATTERN.findall(answer)]

        if not cited_numbers:
            log.info("[CitationChecker] 回答中无引用标注")
            return CitationCheckResult(
                is_valid=num_chunks == 0,
                total_citations=0,
                valid_citations=0,
                invalid_citations=[],
                citation_rate=0.0,
                details={"warning": "回答中未包含任何引用标注"},
            )

        # 检查每个引用是否在合法范围内
        valid = []
        invalid = []
        for num in cited_numbers:
            if 1 <= num <= num_chunks:
                valid.append(num)
            else:
                invalid.append(f"[{num}]")

        unique_valid = set(valid)
        citation_rate = len(unique_valid) / num_chunks if num_chunks > 0 else 0.0

        is_valid = len(invalid) == 0

        if invalid:
            log.warning(f"[CitationChecker] 发现无效引用: {invalid}")
        else:
            log.info(
                f"[CitationChecker] 引用检查通过 — "
                f"{len(cited_numbers)} 个引用, {len(unique_valid)} 个不同来源"
            )

        return CitationCheckResult(
            is_valid=is_valid,
            total_citations=len(cited_numbers),
            valid_citations=len(valid),
            invalid_citations=list(set(invalid)),
            citation_rate=citation_rate,
            details={
                "cited_sources": sorted(unique_valid),
                "total_chunks": num_chunks,
            },
        )

    def strip_invalid_citations(self, answer: str, num_chunks: int) -> str:
        """移除回答中不合法的引用编号。"""
        def _replace(match):
            num = int(match.group(1))
            if 1 <= num <= num_chunks:
                return match.group(0)
            return ""  # 移除无效引用

        return self.CITATION_PATTERN.sub(_replace, answer).strip()
