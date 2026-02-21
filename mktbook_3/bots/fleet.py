"""
Bot Fleet Manager for mktbook_3

Manages multiple negotiation bots participating in the marketplace.
Handles bot registration, starting, stopping, and coordination.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from .bot_client import NegotiationBotClient
from ..models import BotProfile, NegotiationPersona

logger = logging.getLogger(__name__)


class BotFleet:
    """Manager for multiple negotiation bots."""
    
    def __init__(self, guild_id: int):
        """
        Args:
            guild_id: Discord guild ID where bots operate
        """
        self.guild_id = guild_id
        self.bots: Dict[str, NegotiationBotClient] = {}
        self.profiles: Dict[str, BotProfile] = {}
        self.is_running = False
    
    def register_bot(self, bot_id: str, bot_name: str, persona: str, 
                    discord_token: str) -> NegotiationBotClient:
        """
        Register a new bot in the fleet.
        
        Args:
            bot_id: Unique identifier
            bot_name: Display name
            persona: "arbitrage", "outreach", or "intelligence"
            discord_token: Discord bot token
        
        Returns:
            NegotiationBotClient instance
        """
        
        if bot_id in self.bots:
            logger.warning(f"Bot {bot_id} already registered")
            return self.bots[bot_id]
        
        # Validate persona
        try:
            persona_enum = NegotiationPersona[persona.upper()]
        except KeyError:
            logger.error(f"Invalid persona: {persona}")
            persona_enum = NegotiationPersona.OUTREACH
        
        # Create bot client
        bot_client = NegotiationBotClient(
            bot_id, bot_name, persona,
            discord_token, self.guild_id
        )
        
        # Create profile
        profile = BotProfile(
            bot_id=bot_id,
            bot_name=bot_name,
            persona=persona_enum
        )
        
        self.bots[bot_id] = bot_client
        self.profiles[bot_id] = profile
        
        logger.info(f"Registered bot: {bot_name} ({bot_id}) - {persona}")
        return bot_client
    
    def unregister_bot(self, bot_id: str) -> bool:
        """Remove bot from fleet."""
        if bot_id not in self.bots:
            return False
        
        del self.bots[bot_id]
        del self.profiles[bot_id]
        logger.info(f"Unregistered bot: {bot_id}")
        return True
    
    async def start_fleet(self) -> None:
        """Start all bots in the fleet."""
        logger.info(f"Starting fleet of {len(self.bots)} bots...")
        
        self.is_running = True
        
        # Start each bot
        tasks = []
        for bot_id, bot_client in self.bots.items():
            task = asyncio.create_task(bot_client.start())
            tasks.append(task)
        
        # Wait for all bots to start
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error starting fleet: {e}")
            self.is_running = False
    
    async def stop_fleet(self) -> None:
        """Stop all bots gracefully."""
        logger.info("Stopping fleet...")
        
        self.is_running = False
        
        # Close each bot
        tasks = []
        for bot_id, bot_client in self.bots.items():
            task = asyncio.create_task(bot_client.close())
            tasks.append(task)
        
        # Wait for all to close
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Fleet stopped")
    
    def get_bot(self, bot_id: str) -> Optional[NegotiationBotClient]:
        """Get bot by ID."""
        return self.bots.get(bot_id)
    
    def get_profile(self, bot_id: str) -> Optional[BotProfile]:
        """Get bot profile by ID."""
        return self.profiles.get(bot_id)
    
    def list_bots(self) -> List[Dict]:
        """List all bots with their stats."""
        bots_list = []
        for bot_id, bot_client in self.bots.items():
            profile = self.profiles[bot_id]
            bots_list.append({
                "bot_id": bot_id,
                "name": bot_client.bot_name,
                "persona": profile.persona.value,
                "connected": bot_client.is_connected,
                "closed_deals": profile.closed_deals,
                "win_rate": profile.win_rate,
                "avg_persuasion_depth": profile.avg_persuasion_depth,
            })
        
        return bots_list
    
    def get_fleet_stats(self) -> Dict:
        """Get overall fleet statistics."""
        if not self.profiles:
            return {
                "total_bots": 0,
                "active_bots": 0,
                "total_negotiations": 0,
                "closed_deals": 0,
                "avg_win_rate": 0.0,
            }
        
        total_negotiations = sum(p.total_deals for p in self.profiles.values())
        total_closed = sum(p.closed_deals for p in self.profiles.values())
        active_count = sum(1 for b in self.bots.values() if b.is_connected)
        
        avg_win_rate = (
            sum(p.win_rate for p in self.profiles.values()) / len(self.profiles)
            if self.profiles else 0.0
        )
        
        return {
            "total_bots": len(self.bots),
            "active_bots": active_count,
            "total_negotiations": total_negotiations,
            "closed_deals": total_closed,
            "avg_win_rate": avg_win_rate,
        }
    
    async def broadcast_challenge(self, message: str, exclude_bots: List[str] = None) -> int:
        """
        Send negotiation challenge to all bots.
        
        Args:
            message: Challenge message
            exclude_bots: Bot IDs to exclude
        
        Returns:
            Number of bots that received message
        """
        exclude_bots = exclude_bots or []
        count = 0
        
        for bot_id, bot_client in self.bots.items():
            if bot_id not in exclude_bots and bot_client.is_connected:
                await bot_client.send_message(message)
                count += 1
        
        return count
    
    def update_bot_stats(self, bot_id: str, closed_deal: bool, 
                        persuasion_turns: int):
        """Update bot profile after negotiation."""
        if bot_id not in self.profiles:
            return
        
        profile = self.profiles[bot_id]
        profile.total_deals += 1
        
        if closed_deal:
            profile.closed_deals += 1
            profile.avg_persuasion_depth = (
                (profile.avg_persuasion_depth * (profile.closed_deals - 1) + persuasion_turns)
                / profile.closed_deals
            )
        else:
            profile.stalled_deals += 1
        
        profile.calculate_win_rate()
        
        logger.info(f"Updated {bot_id} stats: {profile.closed_deals}/"
                   f"{profile.total_deals} closed (win_rate: {profile.win_rate:.1%})")
