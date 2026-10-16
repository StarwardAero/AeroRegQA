"""问答接口：SSE 流式 + 同步 — 基于 Skills + Router 架构"""
import asyncio
import json
import time
import threading
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from api.schemas import ChatRequest, ChatSyncResponse
from api.dependencies import get_services

router = APIRouter(prefix="/api", tags=["Chat"])


async def _sse_generator(question: str, conversation_id: str | None, services: dict):
    """SSE 事件生成器：通过 Intent Router 分发到合适的 Skill 执行"""
    intent_router = services["intent_router"]
    skill_registry = services["skill_registry"]
    conversation_manager = services["conversation_manager"]
    redis_client = services["redis_client"]
    mysql_client = services["mysql_client"]

    # 如果没有提供 conversation_id，自动创建
    if not conversation_id:
        conv = conversation_manager.create_conversation(model_name="default")
        conversation_id = conv.conversation_id

    # 获取对话历史
    chat_history = conversation_manager.get_chat_history(conversation_id)

    # 保存用户消息
    conversation_manager.add_message(conversation_id, "user", question)

    # 使用 asyncio.Queue 在同步回调和异步生成器之间传递数据
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def on_step(step):
        """Agent 步骤回调"""
        event_data = {
            "type": step.step_type if hasattr(step, 'step_type') else str(step),
            "detail": step.output_data if hasattr(step, 'output_data') else str(step),
        }
        loop.call_soon_threadsafe(queue.put_nowait, ("step", event_data))

    def on_token(token: str):
        """逐 token 回调"""
        loop.call_soon_threadsafe(queue.put_nowait, ("token", {"content": token}))

    stop_event = threading.Event()

    def run_skill():
        try:
            start_time = time.time()

            # ── Redis 缓存检查 ──
            cached = redis_client.get_cached_answer(question)
            if cached:
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    ("step", {"type": "cache_hit", "detail": "命中缓存，直接返回"}),
                )
                answer = cached["answer"]
                if on_token:
                    for char in answer:
                        if stop_event.is_set():
                            break
                        on_token(char)
                done_data = {
                    "sources": cached.get("sources", []),
                    "iterations": 0,
                    "conversation_id": conversation_id,
                    "skill_name": cached.get("skill_name", "cache"),
                    "cached": True,
                }
                loop.call_soon_threadsafe(queue.put_nowait, ("done", done_data))
                conversation_manager.add_message(
                    conversation_id, "assistant", answer,
                    metadata={"sources": cached.get("sources", []), "cached": True}
                )
                conversation_manager.auto_generate_title(conversation_id)
                return

            # ── Intent Router 分发 ──
            routing_decision = intent_router.route(question, chat_history)
            loop.call_soon_threadsafe(
                queue.put_nowait,
                ("step", {
                    "type": "routing",
                    "detail": f"路由至 Skill: {routing_decision.skill_name} "
                              f"(置信度: {routing_decision.confidence:.2f}, "
                              f"方式: {routing_decision.method})",
                }),
            )

            # ── 执行 Skill ──
            skill = skill_registry.get(routing_decision.skill_name)
            if not skill:
                skill = skill_registry.get(skill_registry.default_skill_name)

            result = skill.execute(
                question=question,
                chat_history=chat_history,
                stop_event=stop_event,
                on_step=on_step,
                on_token=on_token,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # ── Fallback：如果答案为空且有备选 Skill ──
            if not result.answer.strip() and routing_decision.fallback_skills:
                for fallback_name in routing_decision.fallback_skills:
                    fb_skill = skill_registry.get(fallback_name)
                    if fb_skill:
                        loop.call_soon_threadsafe(
                            queue.put_nowait,
                            ("step", {"type": "fallback", "detail": f"切换到备选 Skill: {fallback_name}"}),
                        )
                        result = fb_skill.execute(
                            question=question,
                            chat_history=chat_history,
                            stop_event=stop_event,
                            on_step=on_step,
                            on_token=on_token,
                        )
                        if result.answer.strip():
                            break

            # ── 缓存结果到 Redis ──
            if result.answer.strip() and result.skill_name != "chitchat":
                redis_client.cache_answer(
                    question, result.answer, result.sources, result.skill_name
                )

            # ── 记录 Skill 调用日志到 MySQL ──
            try:
                mysql_client.log_skill_call(
                    skill_name=result.skill_name or routing_decision.skill_name,
                    question_preview=question[:500],
                    confidence=routing_decision.confidence,
                    routing_method=routing_decision.method,
                    duration_ms=duration_ms,
                    success=bool(result.answer.strip()),
                    conversation_id=conversation_id,
                )
            except Exception:
                pass  # 日志记录失败不影响主流程

            # ── 发送完成事件 ──
            done_data = {
                "sources": result.sources,
                "iterations": result.iterations,
                "conversation_id": conversation_id,
                "skill_name": result.skill_name,
                "routing_confidence": routing_decision.confidence,
            }
            loop.call_soon_threadsafe(queue.put_nowait, ("done", done_data))

            # 保存 AI 回复
            conversation_manager.add_message(
                conversation_id, "assistant", result.answer,
                metadata={
                    "sources": result.sources,
                    "skill_name": result.skill_name,
                }
            )
            conversation_manager.auto_generate_title(conversation_id)

        except Exception as e:
            error_data = {"error": str(e)}
            loop.call_soon_threadsafe(queue.put_nowait, ("error", error_data))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, (None, None))

    # 在后台线程中运行
    thread = threading.Thread(target=run_skill, daemon=True)
    thread.start()

    # 异步生成 SSE 事件
    while True:
        event_type, event_data = await queue.get()
        if event_type is None:
            break
        yield f"event: {event_type}\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat_stream(request: ChatRequest):
    """SSE 流式问答接口（Skills + Router 架构）"""
    services = get_services()
    return StreamingResponse(
        _sse_generator(request.question, request.conversation_id, services),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/sync", response_model=ChatSyncResponse)
async def chat_sync(request: ChatRequest):
    """同步问答接口（非流式，Skills + Router 架构）"""
    services = get_services()
    intent_router = services["intent_router"]
    skill_registry = services["skill_registry"]
    conversation_manager = services["conversation_manager"]
    redis_client = services["redis_client"]
    mysql_client = services["mysql_client"]

    # 如果没有提供 conversation_id，自动创建
    conversation_id = request.conversation_id
    if not conversation_id:
        conv = conversation_manager.create_conversation(model_name="default")
        conversation_id = conv.conversation_id

    # 获取对话历史
    chat_history = conversation_manager.get_chat_history(conversation_id)

    # 保存用户消息
    conversation_manager.add_message(conversation_id, "user", request.question)

    # Redis 缓存检查
    cached = redis_client.get_cached_answer(request.question)
    if cached:
        conversation_manager.add_message(
            conversation_id, "assistant", cached["answer"],
            metadata={"cached": True}
        )
        return ChatSyncResponse(
            answer=cached["answer"],
            sources=cached.get("sources", []),
            conversation_id=conversation_id,
            iterations=0,
        )

    # 路由
    routing_decision = intent_router.route(request.question, chat_history)
    skill = skill_registry.get(routing_decision.skill_name) or skill_registry.get("rag")

    # 执行
    start_time = time.time()
    stop_event = threading.Event()
    result = await asyncio.to_thread(
        skill.execute,
        question=request.question,
        chat_history=chat_history,
        stop_event=stop_event,
    )
    duration_ms = int((time.time() - start_time) * 1000)

    # 缓存
    if result.answer.strip() and result.skill_name != "chitchat":
        redis_client.cache_answer(
            request.question, result.answer, result.sources, result.skill_name
        )

    # 日志
    try:
        mysql_client.log_skill_call(
            skill_name=result.skill_name,
            question_preview=request.question[:500],
            confidence=routing_decision.confidence,
            routing_method=routing_decision.method,
            duration_ms=duration_ms,
            success=True,
            conversation_id=conversation_id,
        )
    except Exception:
        pass

    # 保存 AI 回复
    conversation_manager.add_message(
        conversation_id, "assistant", result.answer,
        metadata={"sources": result.sources, "skill_name": result.skill_name}
    )
    conversation_manager.auto_generate_title(conversation_id)

    return ChatSyncResponse(
        answer=result.answer,
        sources=result.sources,
        conversation_id=conversation_id,
        iterations=result.iterations,
    )
