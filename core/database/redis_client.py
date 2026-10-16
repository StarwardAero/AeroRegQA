"""Redis 客户端 — 高频问题缓存、会话上下文缓存、检索结果缓存。"""

from __future__ import annotations

import json
import hashlib
from typing import Optional, Any

from utils.logger import get_logger

log = get_logger(__name__)


class RedisClient:
    """Redis 缓存客户端封装。

    用途:
    - 高频问题缓存：相同/相似问题直接返回缓存结果
    - 会话上下文缓存：替代内存/文件存储，提供快速读写
    - 检索结果缓存：相同 query 的向量检索结果短期缓存
    - Rate limiting：API 调用频率控制
    """

    # Key 前缀常量
    PREFIX_QUERY_CACHE = "qa:query:"
    PREFIX_SESSION = "qa:session:"
    PREFIX_RETRIEVAL = "qa:retrieval:"
    PREFIX_RATE_LIMIT = "qa:ratelimit:"
    # 缓存统计计数器（持久化在 Redis 中）
    COUNTER_HITS = "qa:stats:cache_hits"
    COUNTER_MISSES = "qa:stats:cache_misses"

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str = "",
        default_ttl: int = 3600,
    ) -> None:
        self.default_ttl = default_ttl
        self._client = None
        try:
            import redis
            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password or None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # 验证连接
            self._client.ping()
            log.info(f"Redis 连接成功: {host}:{port}/{db}")
        except ImportError:
            log.warning("redis 库未安装，Redis 缓存功能禁用。请执行: pip install redis")
        except Exception as e:
            log.warning(f"Redis 连接失败: {e}。缓存功能将被禁用。")
            self._client = None

    @property
    def is_available(self) -> bool:
        """Redis 是否可用。"""
        return self._client is not None

    # ── 通用操作 ──────────────────────────────────────────────────────

    def get(self, key: str) -> Optional[str]:
        if not self.is_available:
            return None
        try:
            return self._client.get(key)
        except Exception as e:
            log.warning(f"Redis GET 失败: {e}")
            return None

    def set(self, key: str, value: str, ttl: int = None) -> bool:
        if not self.is_available:
            return False
        try:
            self._client.set(key, value, ex=ttl or self.default_ttl)
            return True
        except Exception as e:
            log.warning(f"Redis SET 失败: {e}")
            return False

    def delete(self, key: str) -> bool:
        if not self.is_available:
            return False
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            log.warning(f"Redis DELETE 失败: {e}")
            return False

    # ── 缓存统计 ──────────────────────────────────────────────────────
    def _incr_hit(self) -> None:
        """原子递增缓存命中计数器。"""
        if self.is_available:
            try:
                self._client.incr(self.COUNTER_HITS)
            except Exception:
                pass

    def _incr_miss(self) -> None:
        """原子递增缓存未命中计数器。"""
        if self.is_available:
            try:
                self._client.incr(self.COUNTER_MISSES)
            except Exception:
                pass

    def get_cache_stats(self) -> dict:
        """获取缓存命中率统计。

        Returns:
            {"hits": int, "misses": int, "hit_rate": float, "total": int}
        """
        if not self.is_available:
            return {"hits": 0, "misses": 0, "hit_rate": 0.0, "total": 0}
        try:
            hits = int(self._client.get(self.COUNTER_HITS) or 0)
            misses = int(self._client.get(self.COUNTER_MISSES) or 0)
            total = hits + misses
            hit_rate = round(hits / max(total, 1), 4)
            return {"hits": hits, "misses": misses, "hit_rate": hit_rate, "total": total}
        except Exception:
            return {"hits": 0, "misses": 0, "hit_rate": 0.0, "total": 0}

    def reset_cache_stats(self) -> bool:
        """重置缓存统计计数器。"""
        if not self.is_available:
            return False
        try:
            self._client.delete(self.COUNTER_HITS, self.COUNTER_MISSES)
            return True
        except Exception:
            return False

    # ── 高频问题缓存 ─────────────────────────────────────────────────

    @staticmethod
    def _query_hash(question: str) -> str:
        """对问题进行哈希，作为缓存 key。"""
        normalized = question.strip().lower()
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()

    def get_cached_answer(self, question: str) -> Optional[dict]:
        """查询缓存，命中则返回 {answer, sources, skill_name}。"""
        key = self.PREFIX_QUERY_CACHE + self._query_hash(question)
        raw = self.get(key)
        if raw:
            try:
                data = json.loads(raw)
                log.info(f"[Redis] 问题缓存命中: {question[:40]}...")
                self._incr_hit()
                return data
            except json.JSONDecodeError:
                pass
        self._incr_miss()
        return None

    def cache_answer(
        self, question: str, answer: str, sources: list, skill_name: str, ttl: int = 1800
    ) -> bool:
        """缓存问答结果（默认 30 分钟过期）。"""
        key = self.PREFIX_QUERY_CACHE + self._query_hash(question)
        data = json.dumps({
            "answer": answer,
            "sources": sources,
            "skill_name": skill_name,
            "cached": True,
        }, ensure_ascii=False)
        return self.set(key, data, ttl=ttl)

    # ── 会话上下文缓存 ───────────────────────────────────────────────

    def get_session_context(self, conversation_id: str) -> Optional[list[dict]]:
        """获取缓存的会话上下文。"""
        key = self.PREFIX_SESSION + conversation_id
        raw = self.get(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        return None

    def set_session_context(
        self, conversation_id: str, messages: list[dict], ttl: int = 7200
    ) -> bool:
        """缓存会话上下文（默认 2 小时过期）。"""
        key = self.PREFIX_SESSION + conversation_id
        data = json.dumps(messages, ensure_ascii=False)
        return self.set(key, data, ttl=ttl)

    def clear_session(self, conversation_id: str) -> bool:
        """清除指定会话缓存。"""
        return self.delete(self.PREFIX_SESSION + conversation_id)

    # ── 检索结果缓存 ─────────────────────────────────────────────────

    def get_cached_retrieval(self, query: str) -> Optional[list[dict]]:
        """获取缓存的检索结果。"""
        key = self.PREFIX_RETRIEVAL + self._query_hash(query)
        raw = self.get(key)
        if raw:
            try:
                log.info(f"[Redis] 检索缓存命中: {query[:40]}...")
                self._incr_hit()
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        self._incr_miss()
        return None

    def cache_retrieval(self, query: str, chunks_data: list[dict], ttl: int = 600) -> bool:
        """缓存检索结果（默认 10 分钟过期）。"""
        key = self.PREFIX_RETRIEVAL + self._query_hash(query)
        data = json.dumps(chunks_data, ensure_ascii=False)
        return self.set(key, data, ttl=ttl)

    # ── Rate Limiting ────────────────────────────────────────────────

    def check_rate_limit(self, client_id: str, max_requests: int = 60, window: int = 60) -> bool:
        """检查是否超过速率限制。返回 True 表示允许访问。"""
        if not self.is_available:
            return True  # Redis 不可用时不限流
        try:
            key = self.PREFIX_RATE_LIMIT + client_id
            current = self._client.incr(key)
            if current == 1:
                self._client.expire(key, window)
            return current <= max_requests
        except Exception as e:
            log.warning(f"Redis 限流检查失败: {e}")
            return True
