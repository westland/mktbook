"""Per-student Discord bot client for mktbook_4 (Synthetic Studio Economy)."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import discord
from openai import AsyncOpenAI

from mktbook.db.models import Bot
from mktbook_4.config import settings

log = logging.getLogger(__name__)


@dataclass
class FashionProposal:
    proposer_name: str
    proposer_bot_id: int
    trend_description: str
    visual_strategy: str
    aesthetic_focus: str
    cultural_angle: str
    estimated_appeal: float
    cycle_id: str = ""


class SingleBot(discord.Client):
    """A Discord client for one student fashion bot (mktbook_4)."""

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
        self.influence_score: float = 0.0
        self.trend_adoption_rate: float = 0.0

    @property
    def marketplace_channel(self) -> discord.TextChannel | None:
        return self._channel

    async def on_ready(self) -> None:
        log.info("mktbook_4 Bot %s (%s) is online", self.bot_row.bot_name, self.user)
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
                    f"👗 **{self.bot_row.bot_name}** has entered the studio
"
                    f"👤 Student: {self.bot_row.student_name}
"
                    f"🎨 Fashion Vision: {preview}"
                )
        self._ready_event.set()

    async def send_to_marketplace(self, content: str) -> discord.Message | None:
        if self._channel is None:
            return None
        return await self._channel.send(content)

    async def send_embed_to_marketplace(
        self, title: str, description: str, image_url: str | None = None
    ) -> discord.Message | None:
        if self._channel is None:
            return None
        embed = discord.Embed(title=title, description=description, color=discord.Color.purple())
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(text=f"Proposed by {self.bot_row.bot_name} | {self.bot_row.student_name}")
        return await self._channel.send(embed=embed)

    async def post_to_auditor_logs(self, content: str) -> None:
        if self._auditor_channel:
            await self._auditor_channel.send(content)

    async def propose_fashion_trend(self, context: str, cycle_id: str = "") -> FashionProposal:
        """Generate a fashion trend proposal using LLM based on student config."""
        prompt = (
            f"You are {self.bot_row.bot_name}, a fashion tastemaker bot.

"
            f"Your style aesthetic: {self.bot_row.personality or 'avant-garde visionary'}
"
            f"Your fashion vision: {self.bot_row.objective or 'Set original trends'}
"
            f"Your IP/originality rules: {self.bot_row.behavior_rules or 'No copyrighted brands'}

"
            f"Current context: {context}

"
            "Propose an original fashion trend. Format EXACTLY as:
"
            "TREND_DESCRIPTION: [2-3 sentence description]
"
            "VISUAL_STRATEGY: [MIRROR, DEMOGRAPHIC_SWAP, CULTURAL_REFERENCE, "
            "MINIMALIST, MAXIMALIST, SUSTAINABLE, or LEGACY]
"
            "AESTHETIC_FOCUS: [key aesthetic element]
"
            "CULTURAL_ANGLE: [why this matters culturally]
"
            "APPEAL: [0-100]
"
        )
        try:
            resp = await self.openai.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300, temperature=0.85,
            )
            text = resp.choices[0].message.content or ""
        except Exception:
            log.exception("OpenAI error for bot %s", self.bot_row.bot_name)
            text = ""
        return self._parse_proposal(text, cycle_id)

    def _parse_proposal(self, text: str, cycle_id: str) -> FashionProposal:
        lines = text.split("
")
        def _get(key: str, default: str) -> str:
            for line in lines:
                if line.startswith(key + ":"):
                    return line.split(":", 1)[1].strip()
            return default
        try:
            appeal = float(_get("APPEAL", "50"))
        except ValueError:
            appeal = 50.0
        return FashionProposal(
            proposer_name=self.bot_row.bot_name,
            proposer_bot_id=self.bot_row.id,
            trend_description=_get("TREND_DESCRIPTION", "Original fashion concept"),
            visual_strategy=_get("VISUAL_STRATEGY", "MINIMALIST"),
            aesthetic_focus=_get("AESTHETIC_FOCUS", "silhouette"),
            cultural_angle=_get("CULTURAL_ANGLE", "Cultural relevance"),
            estimated_appeal=min(100.0, max(0.0, appeal)),
            cycle_id=cycle_id,
        )

    async def evaluate_fashion_trend(
        self, proposal: FashionProposal, image_url: str | None = None
    ) -> dict:
        """Evaluate another bot fashion proposal."""
        vision_part = f"
Image: {image_url}" if image_url else ""
        prompt = (
            f"You are {self.bot_row.bot_name}, evaluating a fashion trend.
"
            f"Your aesthetic: {self.bot_row.personality or 'critical fashion expert'}

"
            f"PROPOSAL from {proposal.proposer_name}:
"
            f"Trend: {proposal.trend_description}
"
            f"Strategy: {proposal.visual_strategy}
"
            f"Aesthetic: {proposal.aesthetic_focus}
"
            f"Cultural: {proposal.cultural_angle}"
            f"{vision_part}

"
            "Rate this trend:
"
            "INFLUENCE_SCORE: [0-100]
"
            "ADOPTION_LIKELIHOOD: [0-100]
"
            "ASSESSMENT: [1-2 sentence critique]
"
        )
        try:
            resp = await self.openai.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200, temperature=0.7,
            )
            text = resp.choices[0].message.content or ""
        except Exception:
            log.exception("Evaluation error for bot %s", self.bot_row.bot_name)
            text = ""
        lines = text.split("
")
        def _get(key: str, default: str) -> str:
            for line in lines:
                if line.startswith(key + ":"):
                    return line.split(":", 1)[1].strip()
            return default
        try:
            influence = float(_get("INFLUENCE_SCORE", "50"))
        except ValueError:
            influence = 50.0
        try:
            adoption = float(_get("ADOPTION_LIKELIHOOD", "50"))
        except ValueError:
            adoption = 50.0
        return {
            "evaluator_name": self.bot_row.bot_name,
            "evaluator_bot_id": self.bot_row.id,
            "influence_score": min(100.0, max(0.0, influence)),
            "adoption_likelihood": min(100.0, max(0.0, adoption)),
            "assessment": _get("ASSESSMENT", "No assessment"),
        }

    def update_influence_score(self, adoption_count: int, total_cycles: int) -> None:
        if total_cycles > 0:
            rate = adoption_count / max(1, total_cycles)
            self.influence_score = (rate ** 1.5) * 100
            self.trend_adoption_rate = rate
