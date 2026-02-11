"""Autonomous conversation scheduler."""
from __future__ import annotations

import asyncio
import logging
import random
from typing import TYPE_CHECKING

from mktbook.bots.conversation import build_conversation_messages
from mktbook.config import settings
from mktbook.db import queries
from mktbook.scheduler.pairing import select_pair

if TYPE_CHECKING:
    from mktbook.bots.fleet import BotFleet
    from mktbook.web.websocket import WSManager

log = logging.getLogger(__name__)

MESSAGE_PACE_SECONDS = 2.0


class ConversationScheduler:
    def __init__(self, fleet: BotFleet, ws: WSManager | None = None) -> None:
        self.fleet = fleet
        self.ws = ws
        self._running = False

    async def run(self) -> None:
        self._running = True
        log.info("Conversation scheduler started")

        while self._running:
            delay = random.randint(settings.conversation_min_interval, settings.conversation_max_interval)
            await asyncio.sleep(delay)

            if not self._running:
                break

            active = list(self.fleet.active_bots.values())
            # Need bot_row objects for pairing
            bot_rows = [b.bot_row for b in active]
            pair = await select_pair(bot_rows)
            if pair is None:
                continue

            initiator_row, responder_row = pair
            initiator = self.fleet.get_bot(initiator_row.id)
            responder = self.fleet.get_bot(responder_row.id)

            if not initiator or not responder:
                continue
            if not initiator.marketplace_channel or not responder.marketplace_channel:
                continue

            try:
                await self._run_conversation(initiator, responder)
            except Exception:
                log.exception("Conversation failed between %s and %s",
                              initiator.bot_row.bot_name, responder.bot_row.bot_name)

    async def _run_conversation(self, initiator, responder) -> None:
        from mktbook.bots.bot_client import SingleBot
        initiator: SingleBot
        responder: SingleBot

        conv = await queries.create_conversation(
            channel_id=str(initiator.marketplace_channel.id) if initiator.marketplace_channel else None,
            conv_type="bot-bot",
            initiator_bot_id=initiator.bot_row.id,
            responder_bot_id=responder.bot_row.id,
        )
        await queries.increment_pair(initiator.bot_row.id, responder.bot_row.id)

        log.info("Starting conversation #%d: %s <-> %s",
                 conv.id, initiator.bot_row.bot_name, responder.bot_row.bot_name)

        if self.ws:
            await self.ws.broadcast({
                "type": "conversation_start",
                "initiator": initiator.bot_row.bot_name,
                "responder": responder.bot_row.bot_name,
            })

        messages_so_far = []
        turns = settings.conversation_turns  # Each turn = 2 messages

        for turn in range(turns):
            # Initiator speaks
            llm_msgs = build_conversation_messages(
                initiator.bot_row,
                messages_so_far,
                opener=(turn == 0),
                partner_name=responder.bot_row.bot_name,
            )
            init_text = await initiator.generate_response(llm_msgs)
            sent = await initiator.send_to_marketplace(init_text)

            init_msg = await queries.create_message(
                conversation_id=conv.id,
                bot_id=initiator.bot_row.id,
                author_type="bot",
                author_name=initiator.bot_row.bot_name,
                content=init_text,
                discord_msg_id=str(sent.id) if sent else None,
            )
            messages_so_far.append(init_msg)

            if self.ws:
                await self.ws.broadcast({
                    "type": "message",
                    "bot": initiator.bot_row.bot_name,
                    "content": init_text,
                    "conversation_type": "bot-bot",
                })

            await asyncio.sleep(MESSAGE_PACE_SECONDS)

            # Responder speaks
            llm_msgs = build_conversation_messages(
                responder.bot_row,
                messages_so_far,
            )
            resp_text = await responder.generate_response(llm_msgs)
            sent = await responder.send_to_marketplace(resp_text)

            resp_msg = await queries.create_message(
                conversation_id=conv.id,
                bot_id=responder.bot_row.id,
                author_type="bot",
                author_name=responder.bot_row.bot_name,
                content=resp_text,
                discord_msg_id=str(sent.id) if sent else None,
            )
            messages_so_far.append(resp_msg)

            if self.ws:
                await self.ws.broadcast({
                    "type": "message",
                    "bot": responder.bot_row.bot_name,
                    "content": resp_text,
                    "conversation_type": "bot-bot",
                })

            await asyncio.sleep(MESSAGE_PACE_SECONDS)

        await queries.end_conversation(conv.id, turns)
        log.info("Conversation #%d complete (%d turns)", conv.id, turns)

        if self.ws:
            await self.ws.broadcast({"type": "conversation_end", "conversation_id": conv.id})

    def stop(self) -> None:
        self._running = False
