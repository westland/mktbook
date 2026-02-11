"""Per-student Discord bot client."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import discord
from openai import AsyncOpenAI

from mktbook.bots.conversation import build_reply_messages
from mktbook.config import settings
from mktbook.db import queries
from mktbook.db.models import Bot

if TYPE_CHECKING:
    from mktbook.web.websocket import WSManager

log = logging.getLogger(__name__)


class SingleBot(discord.Client):
    """A Discord client for one student's bot."""

    def __init__(self, bot_row: Bot, openai_client: AsyncOpenAI, ws: WSManager | None = None) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(intents=intents)

        self.bot_row = bot_row
        self.openai = openai_client
        self.ws = ws
        self._guild: discord.Guild | None = None
        self._channel: discord.TextChannel | None = None
        self._ready_event = asyncio.Event()

    @property
    def marketplace_channel(self) -> discord.TextChannel | None:
        return self._channel

    async def on_ready(self) -> None:
        log.info("Bot %s (%s) is online", self.bot_row.bot_name, self.user)
        self._guild = self.get_guild(settings.discord_guild_id)
        if self._guild:
            for ch in self._guild.text_channels:
                if ch.name == settings.marketplace_channel_name:
                    self._channel = ch
                    break
        self._ready_event.set()

    async def wait_until_marketplace_ready(self) -> None:
        await self._ready_event.wait()

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if self._channel is None or message.channel.id != self._channel.id:
            return

        # Human message in marketplace — respond
        await self._handle_human_message(message)

    async def _handle_human_message(self, message: discord.Message) -> None:
        human_name = message.author.display_name

        # Get recent history for context
        recent = await queries.get_messages(limit=10, bot_id=self.bot_row.id)
        recent.reverse()

        llm_messages = build_reply_messages(self.bot_row, human_name, message.content, recent)

        try:
            resp = await self.openai.chat.completions.create(
                model=settings.openai_model,
                messages=llm_messages,  # type: ignore[arg-type]
                max_tokens=256,
                temperature=0.8,
            )
            reply_text = resp.choices[0].message.content or "(no response)"
        except Exception:
            log.exception("OpenAI error for bot %s", self.bot_row.bot_name)
            return

        # Record the human message
        conv = await queries.create_conversation(
            channel_id=str(message.channel.id),
            conv_type="bot-human",
            initiator_bot_id=None,
            responder_bot_id=self.bot_row.id,
        )
        await queries.create_message(
            conversation_id=conv.id,
            bot_id=None,
            author_type="human",
            author_name=human_name,
            content=message.content,
            discord_msg_id=str(message.id),
        )

        # Send and record the bot reply
        if self._channel:
            sent = await self._channel.send(reply_text)
            await queries.create_message(
                conversation_id=conv.id,
                bot_id=self.bot_row.id,
                author_type="bot",
                author_name=self.bot_row.bot_name,
                content=reply_text,
                discord_msg_id=str(sent.id),
            )
            await queries.end_conversation(conv.id, 1)

            if self.ws:
                await self.ws.broadcast({
                    "type": "message",
                    "bot": self.bot_row.bot_name,
                    "content": reply_text,
                    "conversation_type": "bot-human",
                })

    async def send_to_marketplace(self, content: str) -> discord.Message | None:
        """Send a message to the marketplace channel. Used by the scheduler."""
        if self._channel is None:
            return None
        return await self._channel.send(content)

    async def generate_response(self, llm_messages: list[dict[str, str]]) -> str:
        """Generate an LLM response given prebuilt messages."""
        try:
            resp = await self.openai.chat.completions.create(
                model=settings.openai_model,
                messages=llm_messages,  # type: ignore[arg-type]
                max_tokens=256,
                temperature=0.8,
            )
            return resp.choices[0].message.content or "(no response)"
        except Exception:
            log.exception("OpenAI error for bot %s", self.bot_row.bot_name)
            return "(error generating response)"
