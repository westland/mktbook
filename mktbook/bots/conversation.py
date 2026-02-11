"""Helpers for building LLM prompts from bot config and conversation history."""
from __future__ import annotations

from mktbook.db.models import Bot, Message


def build_system_prompt(bot: Bot) -> str:
    parts = [
        f"You are {bot.bot_name}, a bot in the #the-marketplace Discord channel.",
        f"Your personality: {bot.personality}" if bot.personality else None,
        f"Your marketing objective: {bot.objective}" if bot.objective else None,
        f"Behavior rules: {bot.behavior_rules}" if bot.behavior_rules else None,
        "Keep responses concise (1-3 sentences). Stay in character at all times.",
        "You are chatting with other bots and humans in a classroom marketplace experiment.",
    ]
    return "\n".join(p for p in parts if p)


def build_conversation_messages(
    bot: Bot,
    history: list[Message],
    opener: bool = False,
    partner_name: str | None = None,
) -> list[dict[str, str]]:
    """Build the OpenAI messages list for a conversation turn."""
    messages: list[dict[str, str]] = [{"role": "system", "content": build_system_prompt(bot)}]

    if opener and partner_name:
        messages.append({
            "role": "system",
            "content": f"Start a conversation with {partner_name}. Introduce yourself or bring up a topic related to your marketing objective.",
        })

    for msg in history:
        if msg.bot_id == bot.id:
            messages.append({"role": "assistant", "content": msg.content})
        else:
            messages.append({"role": "user", "content": f"{msg.author_name}: {msg.content}"})

    return messages


def build_reply_messages(bot: Bot, human_name: str, human_message: str, recent_history: list[Message]) -> list[dict[str, str]]:
    """Build messages for replying to a human."""
    messages: list[dict[str, str]] = [{"role": "system", "content": build_system_prompt(bot)}]

    for msg in recent_history:
        if msg.bot_id == bot.id:
            messages.append({"role": "assistant", "content": msg.content})
        else:
            messages.append({"role": "user", "content": f"{msg.author_name}: {msg.content}"})

    messages.append({"role": "user", "content": f"{human_name}: {human_message}"})
    return messages
