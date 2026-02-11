from __future__ import annotations

from typing import Any

from mktbook.db.connection import get_db
from mktbook.db.models import Bot, Conversation, Grade, Message


def _row_to_bot(row: Any) -> Bot:
    return Bot(
        id=row["id"],
        student_name=row["student_name"],
        bot_name=row["bot_name"],
        discord_token=row["discord_token"],
        personality=row["personality"],
        objective=row["objective"],
        behavior_rules=row["behavior_rules"],
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
    )


def _row_to_conversation(row: Any) -> Conversation:
    return Conversation(
        id=row["id"],
        channel_id=row["channel_id"],
        type=row["type"],
        initiator_bot_id=row["initiator_bot_id"],
        responder_bot_id=row["responder_bot_id"],
        turn_count=row["turn_count"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
    )


def _row_to_message(row: Any) -> Message:
    return Message(
        id=row["id"],
        conversation_id=row["conversation_id"],
        bot_id=row["bot_id"],
        author_type=row["author_type"],
        author_name=row["author_name"],
        content=row["content"],
        discord_msg_id=row["discord_msg_id"],
        created_at=row["created_at"],
    )


def _row_to_grade(row: Any) -> Grade:
    return Grade(
        id=row["id"],
        bot_id=row["bot_id"],
        grading_run_id=row["grading_run_id"],
        objective_score=row["objective_score"],
        quality_score=row["quality_score"],
        human_score=row["human_score"],
        volume_score=row["volume_score"],
        overall_score=row["overall_score"],
        llm_reasoning=row["llm_reasoning"],
        total_messages=row["total_messages"],
        total_conversations=row["total_conversations"],
        human_interactions=row["human_interactions"],
        created_at=row["created_at"],
    )


# ── Bots ──────────────────────────────────────────────────────────────

async def create_bot(
    student_name: str,
    bot_name: str,
    discord_token: str,
    personality: str = "",
    objective: str = "",
    behavior_rules: str = "",
) -> Bot:
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO bots (student_name, bot_name, discord_token, personality, objective, behavior_rules)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (student_name, bot_name, discord_token, personality, objective, behavior_rules),
    )
    await db.commit()
    row = await (await db.execute("SELECT * FROM bots WHERE id = ?", (cursor.lastrowid,))).fetchone()
    return _row_to_bot(row)


async def get_bot(bot_id: int) -> Bot | None:
    db = await get_db()
    row = await (await db.execute("SELECT * FROM bots WHERE id = ?", (bot_id,))).fetchone()
    return _row_to_bot(row) if row else None


async def get_bot_by_name(bot_name: str) -> Bot | None:
    db = await get_db()
    row = await (await db.execute("SELECT * FROM bots WHERE bot_name = ?", (bot_name,))).fetchone()
    return _row_to_bot(row) if row else None


async def get_all_bots() -> list[Bot]:
    db = await get_db()
    rows = await (await db.execute("SELECT * FROM bots ORDER BY created_at DESC")).fetchall()
    return [_row_to_bot(r) for r in rows]


async def get_active_bots() -> list[Bot]:
    db = await get_db()
    rows = await (await db.execute("SELECT * FROM bots WHERE is_active = 1 ORDER BY bot_name")).fetchall()
    return [_row_to_bot(r) for r in rows]


async def update_bot(bot_id: int, **fields: Any) -> Bot | None:
    if not fields:
        return await get_bot(bot_id)
    allowed = {"student_name", "bot_name", "discord_token", "personality", "objective", "behavior_rules", "is_active"}
    filtered = {k: v for k, v in fields.items() if k in allowed}
    if not filtered:
        return await get_bot(bot_id)
    sets = ", ".join(f"{k} = ?" for k in filtered)
    vals = list(filtered.values()) + [bot_id]
    db = await get_db()
    await db.execute(f"UPDATE bots SET {sets} WHERE id = ?", vals)
    await db.commit()
    return await get_bot(bot_id)


async def delete_bot(bot_id: int) -> None:
    db = await get_db()
    await db.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
    await db.commit()


# ── Conversations ─────────────────────────────────────────────────────

async def create_conversation(
    channel_id: str | None,
    conv_type: str,
    initiator_bot_id: int | None,
    responder_bot_id: int | None,
) -> Conversation:
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO conversations (channel_id, type, initiator_bot_id, responder_bot_id)
           VALUES (?, ?, ?, ?)""",
        (channel_id, conv_type, initiator_bot_id, responder_bot_id),
    )
    await db.commit()
    row = await (await db.execute("SELECT * FROM conversations WHERE id = ?", (cursor.lastrowid,))).fetchone()
    return _row_to_conversation(row)


async def end_conversation(conv_id: int, turn_count: int) -> None:
    db = await get_db()
    await db.execute(
        "UPDATE conversations SET ended_at = datetime('now'), turn_count = ? WHERE id = ?",
        (turn_count, conv_id),
    )
    await db.commit()


async def get_conversations(limit: int = 50) -> list[Conversation]:
    db = await get_db()
    rows = await (await db.execute(
        "SELECT * FROM conversations ORDER BY started_at DESC LIMIT ?", (limit,)
    )).fetchall()
    return [_row_to_conversation(r) for r in rows]


async def get_bot_conversations(bot_id: int, limit: int = 50) -> list[Conversation]:
    db = await get_db()
    rows = await (await db.execute(
        """SELECT * FROM conversations
           WHERE initiator_bot_id = ? OR responder_bot_id = ?
           ORDER BY started_at DESC LIMIT ?""",
        (bot_id, bot_id, limit),
    )).fetchall()
    return [_row_to_conversation(r) for r in rows]


# ── Messages ──────────────────────────────────────────────────────────

async def create_message(
    conversation_id: int | None,
    bot_id: int | None,
    author_type: str,
    author_name: str,
    content: str,
    discord_msg_id: str | None = None,
) -> Message:
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO messages (conversation_id, bot_id, author_type, author_name, content, discord_msg_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (conversation_id, bot_id, author_type, author_name, content, discord_msg_id),
    )
    await db.commit()
    row = await (await db.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,))).fetchone()
    return _row_to_message(row)


async def get_conversation_messages(conv_id: int) -> list[Message]:
    db = await get_db()
    rows = await (await db.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conv_id,)
    )).fetchall()
    return [_row_to_message(r) for r in rows]


async def get_messages(limit: int = 100, bot_id: int | None = None) -> list[Message]:
    db = await get_db()
    if bot_id is not None:
        rows = await (await db.execute(
            "SELECT * FROM messages WHERE bot_id = ? ORDER BY created_at DESC LIMIT ?",
            (bot_id, limit),
        )).fetchall()
    else:
        rows = await (await db.execute(
            "SELECT * FROM messages ORDER BY created_at DESC LIMIT ?", (limit,)
        )).fetchall()
    return [_row_to_message(r) for r in rows]


# ── Conversation Pairs ────────────────────────────────────────────────

async def get_pair_counts() -> dict[tuple[int, int], int]:
    db = await get_db()
    rows = await (await db.execute("SELECT * FROM conversation_pairs")).fetchall()
    return {(r["bot_a_id"], r["bot_b_id"]): r["conversation_count"] for r in rows}


async def increment_pair(bot_a_id: int, bot_b_id: int) -> None:
    a, b = min(bot_a_id, bot_b_id), max(bot_a_id, bot_b_id)
    db = await get_db()
    await db.execute(
        """INSERT INTO conversation_pairs (bot_a_id, bot_b_id, conversation_count, last_conversation_at)
           VALUES (?, ?, 1, datetime('now'))
           ON CONFLICT(bot_a_id, bot_b_id)
           DO UPDATE SET conversation_count = conversation_count + 1, last_conversation_at = datetime('now')""",
        (a, b),
    )
    await db.commit()


# ── Grades ────────────────────────────────────────────────────────────

async def create_grade(
    bot_id: int,
    grading_run_id: str,
    objective_score: float,
    quality_score: float,
    human_score: float,
    volume_score: float,
    overall_score: float,
    llm_reasoning: str,
    total_messages: int,
    total_conversations: int,
    human_interactions: int,
) -> Grade:
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO grades
           (bot_id, grading_run_id, objective_score, quality_score, human_score, volume_score,
            overall_score, llm_reasoning, total_messages, total_conversations, human_interactions)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (bot_id, grading_run_id, objective_score, quality_score, human_score, volume_score,
         overall_score, llm_reasoning, total_messages, total_conversations, human_interactions),
    )
    await db.commit()
    row = await (await db.execute("SELECT * FROM grades WHERE id = ?", (cursor.lastrowid,))).fetchone()
    return _row_to_grade(row)


async def get_bot_grades(bot_id: int) -> list[Grade]:
    db = await get_db()
    rows = await (await db.execute(
        "SELECT * FROM grades WHERE bot_id = ? ORDER BY created_at DESC", (bot_id,)
    )).fetchall()
    return [_row_to_grade(r) for r in rows]


async def get_latest_grades() -> list[Grade]:
    """Return the most recent grade for each bot."""
    db = await get_db()
    rows = await (await db.execute(
        """SELECT g.* FROM grades g
           INNER JOIN (
               SELECT bot_id, MAX(created_at) as max_created
               FROM grades GROUP BY bot_id
           ) latest ON g.bot_id = latest.bot_id AND g.created_at = latest.max_created
           ORDER BY g.overall_score DESC"""
    )).fetchall()
    return [_row_to_grade(r) for r in rows]


async def get_grades_by_run(grading_run_id: str) -> list[Grade]:
    db = await get_db()
    rows = await (await db.execute(
        "SELECT * FROM grades WHERE grading_run_id = ? ORDER BY overall_score DESC",
        (grading_run_id,),
    )).fetchall()
    return [_row_to_grade(r) for r in rows]


# ── Stats ─────────────────────────────────────────────────────────────

async def get_bot_stats(bot_id: int) -> dict[str, int]:
    db = await get_db()
    msg_count = (await (await db.execute(
        "SELECT COUNT(*) as c FROM messages WHERE bot_id = ?", (bot_id,)
    )).fetchone())["c"]
    conv_count = (await (await db.execute(
        "SELECT COUNT(*) as c FROM conversations WHERE initiator_bot_id = ? OR responder_bot_id = ?",
        (bot_id, bot_id),
    )).fetchone())["c"]
    human_count = (await (await db.execute(
        """SELECT COUNT(DISTINCT conversation_id) as c FROM messages
           WHERE conversation_id IN (
               SELECT id FROM conversations WHERE initiator_bot_id = ? OR responder_bot_id = ?
           ) AND author_type = 'human'""",
        (bot_id, bot_id),
    )).fetchone())["c"]
    return {"messages": msg_count, "conversations": conv_count, "human_interactions": human_count}
