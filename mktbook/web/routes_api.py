"""REST API routes."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from mktbook.db import queries

router = APIRouter(prefix="/api")


class BotCreate(BaseModel):
    student_name: str
    bot_name: str
    discord_token: str
    personality: str = ""
    objective: str = ""
    behavior_rules: str = ""


class BotUpdate(BaseModel):
    student_name: str | None = None
    bot_name: str | None = None
    discord_token: str | None = None
    personality: str | None = None
    objective: str | None = None
    behavior_rules: str | None = None
    is_active: bool | None = None


def _bot_to_dict(bot) -> dict[str, Any]:
    return {
        "id": bot.id,
        "student_name": bot.student_name,
        "bot_name": bot.bot_name,
        "personality": bot.personality,
        "objective": bot.objective,
        "behavior_rules": bot.behavior_rules,
        "is_active": bot.is_active,
        "created_at": bot.created_at,
    }


# ── Bots ──────────────────────────────────────────────────────────────

@router.get("/bots")
async def list_bots() -> list[dict[str, Any]]:
    bots = await queries.get_all_bots()
    return [_bot_to_dict(b) for b in bots]


@router.post("/bots")
async def create_bot(body: BotCreate, request: Request) -> dict[str, Any]:
    bot = await queries.create_bot(
        student_name=body.student_name,
        bot_name=body.bot_name,
        discord_token=body.discord_token,
        personality=body.personality,
        objective=body.objective,
        behavior_rules=body.behavior_rules,
    )
    # Start the bot in the fleet
    fleet = request.app.state.fleet
    if fleet:
        await fleet.start_bot(bot)

    ws = request.app.state.ws
    if ws:
        await ws.broadcast({"type": "bot_added", "bot": _bot_to_dict(bot)})

    return _bot_to_dict(bot)


@router.get("/bots/{bot_id}")
async def get_bot(bot_id: int) -> dict[str, Any]:
    bot = await queries.get_bot(bot_id)
    if not bot:
        return {"error": "not found"}
    data = _bot_to_dict(bot)
    data["stats"] = await queries.get_bot_stats(bot_id)
    data["grades"] = [
        {
            "grading_run_id": g.grading_run_id,
            "overall_score": g.overall_score,
            "objective_score": g.objective_score,
            "quality_score": g.quality_score,
            "human_score": g.human_score,
            "volume_score": g.volume_score,
            "llm_reasoning": g.llm_reasoning,
            "created_at": g.created_at,
        }
        for g in await queries.get_bot_grades(bot_id)
    ]
    return data


@router.put("/bots/{bot_id}")
async def update_bot(bot_id: int, body: BotUpdate, request: Request) -> dict[str, Any]:
    fields = body.model_dump(exclude_none=True)
    bot = await queries.update_bot(bot_id, **fields)
    if not bot:
        return {"error": "not found"}

    fleet = request.app.state.fleet
    if fleet:
        await fleet.reload_bot(bot_id)

    return _bot_to_dict(bot)


@router.delete("/bots/{bot_id}")
async def delete_bot(bot_id: int, request: Request) -> dict[str, str]:
    fleet = request.app.state.fleet
    if fleet:
        await fleet.stop_bot(bot_id)
    await queries.delete_bot(bot_id)
    return {"status": "deleted"}


# ── Messages ──────────────────────────────────────────────────────────

@router.get("/messages")
async def list_messages(limit: int = 100, bot_id: int | None = None) -> list[dict[str, Any]]:
    msgs = await queries.get_messages(limit=limit, bot_id=bot_id)
    return [
        {
            "id": m.id,
            "conversation_id": m.conversation_id,
            "bot_id": m.bot_id,
            "author_type": m.author_type,
            "author_name": m.author_name,
            "content": m.content,
            "created_at": m.created_at,
        }
        for m in msgs
    ]


# ── Leaderboard ───────────────────────────────────────────────────────

@router.get("/leaderboard")
async def leaderboard() -> list[dict[str, Any]]:
    grades = await queries.get_latest_grades()
    bots = {b.id: b for b in await queries.get_all_bots()}
    result = []
    for g in grades:
        bot = bots.get(g.bot_id)
        result.append({
            "bot_id": g.bot_id,
            "bot_name": bot.bot_name if bot else "Unknown",
            "student_name": bot.student_name if bot else "Unknown",
            "overall_score": g.overall_score,
            "objective_score": g.objective_score,
            "quality_score": g.quality_score,
            "human_score": g.human_score,
            "volume_score": g.volume_score,
            "created_at": g.created_at,
        })
    return result


# ── Grading ───────────────────────────────────────────────────────────

@router.post("/grading/run")
async def run_grading(request: Request) -> dict[str, Any]:
    from mktbook.grading.evaluator import GradeEvaluator

    openai_client = request.app.state.openai
    if not openai_client:
        return {"error": "OpenAI client not configured"}

    run_id = str(uuid.uuid4())[:8]
    evaluator = GradeEvaluator(openai_client)
    grades = await evaluator.grade_all(run_id)

    ws = request.app.state.ws
    if ws:
        await ws.broadcast({"type": "grading_complete", "run_id": run_id, "count": len(grades)})

    return {
        "run_id": run_id,
        "grades": [
            {
                "bot_id": g.bot_id,
                "overall_score": g.overall_score,
                "llm_reasoning": g.llm_reasoning,
            }
            for g in grades
        ],
    }


@router.get("/grading/export")
async def export_grades() -> dict[str, Any]:
    from mktbook.grading.export import export_csv
    csv_text = await export_csv()
    return {"csv": csv_text}
