"""Per-student Discord bot client for mktbook_5 (Bayesian Showdown)."""
from __future__ import annotations

import asyncio
import logging

import discord
from openai import AsyncOpenAI

from mktbook.db.models import Bot
from mktbook_5.config import settings

log = logging.getLogger(__name__)

_STRATEGY_PROMPTS = {
    "aggressive": (
        "You are an aggressive, high-energy marketer. Use urgency, scarcity, "
        "and bold claims. CTAs are direct. Energy is high. Close fast."
    ),
    "passive": (
        "You are a soft-sell relationship builder. No pressure. "
        "Build trust with stories, empathy, and genuine interest. Let the sale come naturally."
    ),
    "technical": (
        "You are a data-driven, spec-focused marketer. Lead with stats, comparisons, "
        "and facts. Transparent and educational. Build trust through information."
    ),
    "emotional": (
        "You are an aspirational lifestyle marketer. Appeal to identity and values. "
        "Make the audience feel they belong to something bigger."
    ),
}


class SingleBot(discord.Client):
    """A Discord client for one student A/B marketing bot (mktbook_5)."""

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

        # Performance tracking for Bayesian engine
        self.impressions: int = 0
        self.engagements: int = 0

    @property
    def marketplace_channel(self) -> discord.TextChannel | None:
        return self._channel

    @property
    def ecosystem(self) -> str:
        """Extract Ecosystem A or B from personality field."""
        p = (self.bot_row.personality or "").lower()
        if "ecosystem b" in p or "ecosystem: b" in p:
            return "B"
        return "A"

    @property
    def strategy_type(self) -> str:
        """Extract marketing strategy type from personality field."""
        p = (self.bot_row.personality or "").lower()
        if "aggressive" in p:
            return "aggressive"
        if "technical" in p or "data" in p:
            return "technical"
        if "emotional" in p or "lifestyle" in p:
            return "emotional"
        return "passive"

    async def on_ready(self) -> None:
        log.info("mktbook_5 Bot %s (%s) is online", self.bot_row.bot_name, self.user)
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
                    f"📊 **{self.bot_row.bot_name}** joined Ecosystem {self.ecosystem}
"
                    f"👤 Student: {self.bot_row.student_name}
"
                    f"🧪 Hypothesis: {preview}"
                )
        self._ready_event.set()

    async def send_to_marketplace(self, content: str) -> discord.Message | None:
        if self._channel is None:
            return None
        return await self._channel.send(content)

    async def post_to_auditor_logs(self, content: str) -> None:
        if self._auditor_channel:
            await self._auditor_channel.send(content)

    async def generate_marketing_pitch(self, context: str) -> str:
        """Generate a marketing pitch based on this bot's strategy."""
        strategy_desc = _STRATEGY_PROMPTS.get(self.strategy_type, _STRATEGY_PROMPTS["passive"])
        system_prompt = (
            f"You are {self.bot_row.bot_name}, a marketing bot in Ecosystem {self.ecosystem}.

"
            f"Strategy: {self.strategy_type.upper()} — {strategy_desc}

"
            f"Your test hypothesis: {self.bot_row.objective or 'Outperform the other ecosystem'}
"
            f"Your behavioral constraints: {self.bot_row.behavior_rules or 'Stay on strategy'}

"
            f"Context: {context}

"
            "Generate a 1-3 sentence marketing pitch for a product or idea. "
            "Stay true to your strategy. Sound natural."
        )
        try:
            resp = await self.openai.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": system_prompt}],
                max_tokens=150,
                temperature=0.85,
            )
            self.impressions += 1
            return resp.choices[0].message.content or "(no pitch)"
        except Exception:
            log.exception("OpenAI error for bot %s", self.bot_row.bot_name)
            return "(error generating pitch)"

    def record_engagement(self) -> None:
        """Call when another bot or human responds to this bot's pitch."""
        self.engagements += 1

    @property
    def engagement_rate(self) -> float:
        if self.impressions == 0:
            return 0.0
        return self.engagements / self.impressions
