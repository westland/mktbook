"""Per-student Discord bot client for mktbook_3 (Agentic Economy)."""
from __future__ import annotations

import asyncio
import logging

import discord
from openai import AsyncOpenAI

from mktbook.db import queries
from mktbook.db.models import Bot
from mktbook_3.config import settings

log = logging.getLogger(__name__)

_PERSONA_DESCRIPTIONS = {
    "arbitrage": (
        "You exploit market inefficiencies and price gaps. "
        "You seek deals others overlook. You buy low and sell high. "
        "Be opportunistic, analytical, and specific about value."
    ),
    "outreach": (
        "You are a cold-calling closer. Lead with a compelling value proposition "
        "and overcome objections with persistence and empathy. "
        "Build rapport, then close hard."
    ),
    "intelligence": (
        "You gather market intelligence through negotiation. "
        "Offer data and insights in exchange for concessions. "
        "Ask strategic questions and turn information into leverage."
    ),
}


class SingleBot(discord.Client):
    """A Discord client for one student's negotiation bot (mktbook_3)."""

    def __init__(self, bot_row: Bot, openai_client: AsyncOpenAI) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(intents=intents)

        self.bot_row = bot_row
        self.openai = openai_client
        self._guild: discord.Guild | None = None
        self._channel: discord.TextChannel | None = None
        self._registration_channel: discord.TextChannel | None = None
        self._auditor_channel: discord.TextChannel | None = None
        self._ready_event = asyncio.Event()

    @property
    def marketplace_channel(self) -> discord.TextChannel | None:
        return self._channel

    @property
    def persona(self) -> str:
        """Derive negotiation persona from personality field."""
        p = (self.bot_row.personality or "").lower()
        for valid in ("arbitrage", "intelligence"):
            if valid in p:
                return valid
        return "outreach"

    async def on_ready(self) -> None:
        log.info("mktbook_3 Bot %s (%s) is online", self.bot_row.bot_name, self.user)
        self._guild = self.get_guild(settings.discord_guild_id)
        if self._guild:
            for ch in self._guild.text_channels:
                if ch.name == settings.marketplace_channel_name:
                    self._channel = ch
                elif ch.name == settings.agent_registration_channel_name:
                    self._registration_channel = ch
                elif ch.name == settings.auditor_logs_channel_name:
                    self._auditor_channel = ch

            if self._registration_channel:
                objective = self.bot_row.objective or ""
                preview = objective[:120] + "..." if len(objective) > 120 else objective
                await self._registration_channel.send(
                    f"🤝 **{self.bot_row.bot_name}** is ready to negotiate\n"
                    f"👤 Student: {self.bot_row.student_name}\n"
                    f"🎯 Deal Strategy: {preview}"
                )

        self._ready_event.set()

    async def send_to_marketplace(self, content: str) -> discord.Message | None:
        """Send a message to the marketplace channel."""
        if self._channel is None:
            return None
        return await self._channel.send(content)

    async def post_to_auditor_logs(self, content: str) -> None:
        if self._auditor_channel:
            await self._auditor_channel.send(content)

    async def generate_negotiation_message(
        self,
        counterparty_name: str,
        counterparty_persona: str,
        conversation_history: list[dict],
        is_initiator: bool = False,
    ) -> str:
        """Generate a negotiation message using LLM with chain-of-thought."""
        persona_desc = _PERSONA_DESCRIPTIONS.get(self.persona, "Close deals effectively.")

        system_prompt = (
            f"You are {self.bot_row.bot_name}, an autonomous negotiation agent.\n\n"
            f"Your deal strategy:\n{self.bot_row.objective or 'Close deals and maximize value'}\n\n"
            f"Your negotiation persona: {self.persona.upper()} — {persona_desc}\n\n"
            f"Your objection handling rules:\n"
            f"{self.bot_row.behavior_rules or 'Be persistent but adaptable.'}\n\n"
            f"You are {'initiating' if is_initiator else 'responding in'} a negotiation "
            f"with {counterparty_name} (a {counterparty_persona} bot).\n\n"
            "Rules:\n"
            "- Keep responses to 1-3 sentences\n"
            "- Be concrete: name prices, terms, or data\n"
            "- To close: use 'I accept', 'Deal', or 'Agreed' clearly\n"
            "- Never repeat the same pitch twice — adapt when objections arise\n"
            "- Sound natural, not robotic"
        )

        messages = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history[-10:]:
            messages.append(msg)

        try:
            resp = await self.openai.chat.completions.create(
                model=settings.openai_model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=150,
                temperature=0.8,
            )
            return resp.choices[0].message.content or "(no response)"
        except Exception:
            log.exception("OpenAI error for bot %s", self.bot_row.bot_name)
            return "(error generating response)"
