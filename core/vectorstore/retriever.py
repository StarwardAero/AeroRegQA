from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from typing import Optional

from utils.logger import get_logger
from core.chunker.chunk_models import DocumentChunk
from .chroma_store import ChromaStore

log = get_logger(__name__)


class HybridRetriever:
    """混合检索器：向量搜索 + BM25 关键词检索 + RRF 融合 + 语义去重 + 冲突预检 + 可选 Rerank"""

    def __init__(
        self,
        chroma_store: ChromaStore,
        reranker=None,
    ):
        self.chroma_store = chroma_store
        self.reranker = reranker

        # BM25 相关状态（延迟构建）
        self._bm25 = None
        self._bm25_chunks: list[DocumentChunk] = []
        self._bm25_corpus: list[list[str]] = []

        # 常见面试/法规问法会直接点名文件、规则或缩写。
        # 这些英文缩写在中文问题里容易被向量检索稀释，因此做一层轻量来源锚定。
        self._source_aliases: dict[str, list[str]] = {
            "EASA-SC-VTOL-02-small-category-VTOL-capable-aircraft-2024.pdf": [
                "sc-vtol",
                "sc vtol",
                "special condition vtol",
                "easa sc-vtol",
                "easa sc vtol",
            ],
            "EASA-MOC-4-SC-VTOL-Issue-2-FINAL-2025.pdf": [
                "moc",
                "means of compliance",
                "moc-4",
                "sc-vtol moc",
            ],
            "FAA-Integration-of-Powered-Lift-Final-Rule-2024.pdf": [
                "powered-lift",
                "powered lift",
                "faa powered-lift",
                "动力升力",
            ],
            "FAA-Urban-Air-Mobility-Concept-of-Operations-2.0-2023.pdf": [
                "uam concept of operations",
                "uam conops",
                "urban air mobility",
                "faa uam",
            ],
            "FAA-Advanced-Air-Mobility-Implementation-Plan-Innovate28.pdf": [
                "aam implementation",
                "advanced air mobility",
                "innovate28",
                "faa aam",
            ],
            "FAA-UTM-Concept-of-Operations-v2-2020.pdf": [
                "utm concept",
                "utm conops",
                "faa utm",
                "无人机交通管理",
            ],
            "FAA-EB-105A-Vertiport-Design-2024.pdf": [
                "vertiport",
                "vertiport design",
                "eb-105a",
                "垂直起降场",
            ],
            "EASA-Easy-Access-Rules-U-space-Regulation-EU-2021-664.pdf": [
                "u-space",
                "u space",
                "easa u-space",
            ],
            "EASA-Easy-Access-Rules-Unmanned-Aircraft-Systems.pdf": [
                "uas regulation",
                "unmanned aircraft systems",
                "easa uas",
            ],
            "CAAC-CCAR-92-民用无人驾驶航空器运行安全管理规则-2024.pdf": [
                "ccar-92",
                "ccar 92",
                "民用无人驾驶航空器运行安全管理规则",
                "运行安全管理规则",
            ],
        }

    # ------------------------------------------------------------------
    # BM25 索引管理
    # ------------------------------------------------------------------

    def _build_bm25_index(self) -> None:
        """从 ChromaStore 获取所有文档，构建 BM25 索引"""
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            log.warning("rank_bm25 not installed. BM25 search disabled.")
            return

        # 从 Chroma 获取全部文档
        all_data = self.chroma_store.collection.get(
            include=["documents", "metadatas"]
        )

        ids = all_data.get("ids", [])
        documents = all_data.get("documents", [])
        metadatas = all_data.get("metadatas", [])

        if not documents:
            log.info("No documents in ChromaStore, BM25 index is empty.")
            self._bm25 = None
            self._bm25_chunks = []
            self._bm25_corpus = []
            return

        # 重建 chunk 对象列表
        self._bm25_chunks = []
        self._bm25_corpus = []
        for i, doc in enumerate(documents):
            chunk = DocumentChunk(
                chunk_id=ids[i],
                content=doc,
                metadata=metadatas[i] if i < len(metadatas) else {},
            )
            self._bm25_chunks.append(chunk)
            # 中文按字符分割（避免 jieba 依赖）
            self._bm25_corpus.append(list(doc))

        self._bm25 = BM25Okapi(self._bm25_corpus)
        log.info(f"BM25 index built with {len(self._bm25_chunks)} documents")

    def refresh_bm25_index(self) -> None:
        """知识库变更后重建 BM25 索引"""
        log.info("Refreshing BM25 index...")
        self._build_bm25_index()

    # ------------------------------------------------------------------
    # BM25 搜索
    # ------------------------------------------------------------------

    def _bm25_search(self, query: str, top_k: int = 20) -> list[DocumentChunk]:
        """使用 BM25 进行关键词检索"""
        if self._bm25 is None or not self._bm25_chunks:
            return []

        tokenized_query = list(query)
        scores = self._bm25.get_scores(tokenized_query)

        # 按分数降序取 top_k
        scored_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:top_k]

        results = []
        for idx in scored_indices:
            if scores[idx] > 0:
                results.append(self._bm25_chunks[idx])

        return results

    # ------------------------------------------------------------------
    # 点名来源锚定
    # ------------------------------------------------------------------

    def _detect_source_hints(self, query: str) -> list[str]:
        """从用户问题中识别被点名的法规/文件来源。"""
        q = query.lower()
        matched: list[str] = []
        for source, aliases in self._source_aliases.items():
            if any(alias.lower() in q for alias in aliases):
                matched.append(source)

        # 自然语言主题锚定：用户不一定会点名四份文件。
        # 当问题同时讨论 eVTOL 载人运行与传统无人机，并涉及适航/运行/路径规划差异时，
        # 默认拉取国际 eVTOL / powered-lift / UAM 与中国 CCAR-92 这组核心对比资料。
        mentions_evtol = any(term in q for term in ["evtol", "vca", "powered-lift", "powered lift", "载人运行", "载人"])
        mentions_uav = any(term in q for term in ["传统无人机", "无人机", "无人驾驶航空器", "uas"])
        mentions_comparison_scope = any(term in q for term in ["适航", "审定", "运行安全", "路径规划", "导航", "不同", "差异", "区别"])
        if mentions_evtol and mentions_uav and mentions_comparison_scope:
            default_sources = [
                "EASA-SC-VTOL-02-small-category-VTOL-capable-aircraft-2024.pdf",
                "FAA-Integration-of-Powered-Lift-Final-Rule-2024.pdf",
                "FAA-Urban-Air-Mobility-Concept-of-Operations-2.0-2023.pdf",
                "CAAC-CCAR-92-民用无人驾驶航空器运行安全管理规则-2024.pdf",
            ]
            for source in default_sources:
                if source not in matched:
                    matched.append(source)
        return matched

    @staticmethod
    def is_evtol_uav_comparison_query(query: str) -> bool:
        """识别 eVTOL 载人运行 vs 传统无人机的自然语言对比问题。"""
        q = query.lower()
        mentions_evtol = any(term in q for term in ["evtol", "vca", "powered-lift", "powered lift", "载人运行", "载人"])
        mentions_uav = any(term in q for term in ["传统无人机", "无人机", "无人驾驶航空器", "uas"])
        mentions_comparison_scope = any(term in q for term in ["适航", "审定", "运行安全", "路径规划", "导航", "不同", "差异", "区别"])
        return mentions_evtol and mentions_uav and mentions_comparison_scope

    @staticmethod
    def _keyword_score(query: str, text: str) -> float:
        """对指定来源内部的片段做轻量相关性排序。"""
        q = query.lower()
        t = text.lower()
        ascii_terms = set(re.findall(r"[a-z][a-z0-9-]{2,}", q))
        cjk_terms = set(re.findall(r"[\u4e00-\u9fff]{2,}", q))
        terms = ascii_terms | cjk_terms
        term_hits = sum(1 for term in terms if term in t)
        char_overlap = len(set(query) & set(text[:600])) / max(len(set(query)), 1)
        return term_hits * 2.0 + char_overlap

    def _source_hint_search(
        self,
        query: str,
        per_source: int = 2,
    ) -> list[DocumentChunk]:
        """当问题点名资料时，从对应来源补召回若干片段。"""
        hinted_sources = self._detect_source_hints(query)
        if not hinted_sources:
            return []

        hinted_chunks: list[DocumentChunk] = []
        for source in hinted_sources:
            try:
                data = self.chroma_store.collection.get(
                    where={"source_file": source},
                    include=["documents", "metadatas"],
                )
            except Exception as exc:
                log.warning(f"Source hint lookup failed for {source}: {exc}")
                continue

            ids = data.get("ids", [])
            docs = data.get("documents", [])
            metas = data.get("metadatas", [])
            scored: list[tuple[float, DocumentChunk]] = []
            for i, doc in enumerate(docs):
                chunk = DocumentChunk(
                    chunk_id=ids[i],
                    content=doc,
                    metadata=metas[i] if i < len(metas) else {},
                )
                scored.append((self._keyword_score(query, doc), chunk))

            scored.sort(key=lambda item: item[0], reverse=True)
            hinted_chunks.extend(chunk for score, chunk in scored[:per_source] if score > 0)

        if hinted_chunks:
            log.info(
                "Source hints added {} chunks from {}",
                len(hinted_chunks),
                ", ".join(hinted_sources),
            )
        return hinted_chunks

    def retrieve_from_sources(
        self,
        query: str,
        sources: list[str],
        per_source: int = 3,
    ) -> list[DocumentChunk]:
        """只从指定来源中检索片段，用于展示级多文件对比，避免相邻资料污染。"""
        chunks: list[DocumentChunk] = []
        for source in sources:
            try:
                data = self.chroma_store.collection.get(
                    where={"source_file": source},
                    include=["documents", "metadatas"],
                )
            except Exception as exc:
                log.warning(f"Source-scoped lookup failed for {source}: {exc}")
                continue

            ids = data.get("ids", [])
            docs = data.get("documents", [])
            metas = data.get("metadatas", [])
            scored: list[tuple[float, DocumentChunk]] = []
            for i, doc in enumerate(docs):
                chunk = DocumentChunk(
                    chunk_id=ids[i],
                    content=doc,
                    metadata=metas[i] if i < len(metas) else {},
                )
                scored.append((self._keyword_score(query, doc), chunk))

            scored.sort(key=lambda item: item[0], reverse=True)
            selected = [chunk for score, chunk in scored[:per_source] if score > 0]
            chunks.extend(selected)

        if chunks:
            log.info(
                "Source-scoped retrieve returned {} chunks from {}",
                len(chunks),
                ", ".join(sources),
            )
        return self._mark_conflicts(self._deduplicate(chunks))

    # ------------------------------------------------------------------
    # RRF 融合
    # ------------------------------------------------------------------

    @staticmethod
    def _rrf_fusion(
        vector_results: list[DocumentChunk],
        bm25_results: list[DocumentChunk],
        k: int = 60,
    ) -> list[DocumentChunk]:
        """
        Reciprocal Rank Fusion — 将两路检索结果融合。

        RRF 公式: score(d) = Σ 1/(k + rank_i)
        """
        scores: dict[str, float] = {}
        chunk_map: dict[str, DocumentChunk] = {}

        for rank, chunk in enumerate(vector_results, start=1):
            cid = chunk.chunk_id
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            chunk_map[cid] = chunk

        for rank, chunk in enumerate(bm25_results, start=1):
            cid = chunk.chunk_id
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            chunk_map[cid] = chunk

        # 按 RRF 分数降序排列
        sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
        return [chunk_map[cid] for cid in sorted_ids]

    # ------------------------------------------------------------------
    # 语义去重
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate(
        chunks: list[DocumentChunk],
        similarity_threshold: float = 0.85,
    ) -> list[DocumentChunk]:
        """基于文本相似度的语义去重，保留排名靠前的版本。

        使用 SequenceMatcher 做近似去重，避免高度重叠的文档片段
        同时占据多个结果位。
        """
        if not chunks:
            return []

        deduped: list[DocumentChunk] = []
        seen_hashes: set[str] = set()

        for chunk in chunks:
            # 1. 精确去重（内容 MD5）
            content_hash = hashlib.md5(chunk.content.encode()).hexdigest()
            if content_hash in seen_hashes:
                continue
            seen_hashes.add(content_hash)

            # 2. 近似去重（与已保留片段做相似度比较）
            is_duplicate = False
            for kept in deduped:
                # 只比较前 500 字符以提升性能
                ratio = SequenceMatcher(
                    None,
                    chunk.content[:500],
                    kept.content[:500],
                ).ratio()
                if ratio >= similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduped.append(chunk)

        removed = len(chunks) - len(deduped)
        if removed > 0:
            log.info(f"Deduplication removed {removed} near-duplicate chunks")
        return deduped

    # ------------------------------------------------------------------
    # 相关性过滤
    # ------------------------------------------------------------------

    @staticmethod
    def _relevance_filter(
        chunks: list[DocumentChunk],
        query: str,
        min_overlap_ratio: float = 0.05,
    ) -> list[DocumentChunk]:
        """基本相关性过滤 — 剔除与 query 完全无关的低质量片段。

        使用 query 字符集合与 chunk 内容的字符重叠比例做粗筛。
        """
        if not chunks:
            return []

        query_chars = set(query)
        filtered: list[DocumentChunk] = []

        for chunk in chunks:
            content_chars = set(chunk.content[:300])
            if not query_chars:
                filtered.append(chunk)
                continue
            overlap = len(query_chars & content_chars) / len(query_chars)
            if overlap >= min_overlap_ratio:
                filtered.append(chunk)

        removed = len(chunks) - len(filtered)
        if removed > 0:
            log.info(f"Relevance filter removed {removed} low-relevance chunks")
        # 如果粗筛全部失败，说明 query 与候选文本可能存在语言/格式差异。
        # 此时保留上游检索排序，避免把可用召回结果误删到只剩 1 条。
        return filtered if filtered else chunks

    # ------------------------------------------------------------------
    # 冲突预检标记
    # ------------------------------------------------------------------

    @staticmethod
    def _mark_conflicts(chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """对来源不同但内容区间重叠的片段标记潜在冲突。

        在 chunk.metadata 中添加 'potential_conflict' 布尔标记，
        供下游 ConflictDetector 做进一步校验。
        """
        for i, chunk_a in enumerate(chunks):
            src_a = chunk_a.metadata.get("source_file", "")
            for j in range(i + 1, len(chunks)):
                chunk_b = chunks[j]
                src_b = chunk_b.metadata.get("source_file", "")
                if src_a == src_b:
                    continue  # 同源不算冲突
                # 判断是否讨论相似主题（标题路径重叠）
                header_a = chunk_a.metadata.get("header_path", "")
                header_b = chunk_b.metadata.get("header_path", "")
                if header_a and header_b:
                    overlap = SequenceMatcher(None, header_a, header_b).ratio()
                    if overlap > 0.5:
                        chunk_a.metadata["potential_conflict"] = True
                        chunk_b.metadata["potential_conflict"] = True
        return chunks

    # ------------------------------------------------------------------
    # 主检索入口
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        use_hybrid: bool = True,
        deduplicate: bool = True,
    ) -> list[DocumentChunk]:
        """
        检索入口。

        流程:
            1. 向量搜索 + BM25 各召回 top_k*4
            2. RRF 融合
            3. 语义去重（去除近似重复片段）
            4. 相关性过滤（剔除低质量片段）
            5. Rerank（如有）→ 返回 top_k
            6. 冲突预检标记
        """
        recall_k = top_k * 6

        if use_hybrid:
            # 若 BM25 索引尚未构建则自动构建
            if self._bm25 is None:
                self._build_bm25_index()

            log.info(
                f"Hybrid retrieve: query='{query}', recall_k={recall_k}, top_k={top_k}"
            )

            # 两路并行召回
            vector_results = self.chroma_store.similarity_search(query, recall_k)
            bm25_results = self._bm25_search(query, recall_k)

            log.info(
                f"Vector returned {len(vector_results)}, BM25 returned {len(bm25_results)}"
            )

            # RRF 融合
            fused = self._rrf_fusion(vector_results, bm25_results)
        else:
            log.info(f"Vector-only retrieve: query='{query}', top_k={recall_k}")
            fused = self.chroma_store.similarity_search(query, recall_k)

        source_hint_results = self._source_hint_search(query)
        if source_hint_results:
            fused = source_hint_results + fused

        # 语义去重
        if deduplicate:
            fused = self._deduplicate(fused)

        # 相关性过滤
        fused = self._relevance_filter(fused, query)

        # Rerank 阶段
        if self.reranker is not None:
            reranked = self.reranker.rerank(query, fused, top_n=top_k)
        else:
            reranked = fused[:top_k]

        # 显式点名来源的查询必须保留这些来源的片段。
        # 否则 reranker 可能把 SC-VTOL / UAM / CCAR-92 等点名文件挤掉，
        # 造成回答误以为“资料未检索到”，或转而引用邻近但偏题的文件。
        if source_hint_results:
            protected: list[DocumentChunk] = []
            seen_sources: set[str] = set()
            for chunk in source_hint_results:
                source = chunk.metadata.get("source_file", "")
                if source and source not in seen_sources:
                    protected.append(chunk)
                    seen_sources.add(source)

            results = []
            seen_ids: set[str] = set()
            for chunk in protected + reranked:
                if chunk.chunk_id in seen_ids:
                    continue
                results.append(chunk)
                seen_ids.add(chunk.chunk_id)
                if len(results) >= top_k:
                    break
        else:
            results = reranked

        # 冲突预检标记
        results = self._mark_conflicts(results)

        log.info(f"Final results: {len(results)} chunks")
        return results

    # ------------------------------------------------------------------
    # 上下文格式化（保持向后兼容）
    # ------------------------------------------------------------------

    def format_context(self, chunks: list[DocumentChunk]) -> str:
        """格式化带引用编号的上下文，包含冲突标记。"""
        if not chunks:
            return "无相关上下文。"

        formatted_parts = []
        for idx, chunk in enumerate(chunks, 1):
            source = chunk.metadata.get("source_file", "Unknown")
            chapter = chunk.metadata.get("header_path", "Global")
            conflict_tag = " ⚠️潜在冲突" if chunk.metadata.get("potential_conflict") else ""

            part = f"[{idx}] (来源: {source}, 章节: {chapter}{conflict_tag})\n{chunk.content}"
            formatted_parts.append(part)

        return "\n\n".join(formatted_parts)

    def format_context_grouped(self, chunks: list[DocumentChunk]) -> str:
        """按来源分组格式化上下文，减少信息混乱。"""
        if not chunks:
            return "无相关上下文。"

        # 按来源文件分组
        groups: dict[str, list[tuple[int, DocumentChunk]]] = {}
        for idx, chunk in enumerate(chunks, 1):
            source = chunk.metadata.get("source_file", "Unknown")
            groups.setdefault(source, []).append((idx, chunk))

        parts = []
        for source, items in groups.items():
            parts.append(f"━━━ 来源: {source} ━━━")
            for idx, chunk in items:
                chapter = chunk.metadata.get("header_path", "Global")
                conflict_tag = " ⚠️潜在冲突" if chunk.metadata.get("potential_conflict") else ""
                parts.append(f"[{idx}] (章节: {chapter}{conflict_tag})\n{chunk.content}")
            parts.append("")

        return "\n\n".join(parts)
