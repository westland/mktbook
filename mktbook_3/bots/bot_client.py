"""
Bot Client for mktbook_3

Each bot represents one autonomous agent participating in negotiations.
Handles Discord integration and message sending with chain-of-thought support.
"""

import logging
from typing import Optional
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class NegotiationBotClient:
    """Individual bot client for participating in deal negotiations."""
    
    def __init__(self, bot_id: str, bot_name: str, persona: str, 
                 discord_token: str, guild_id: int):
        """
        Args:
            bot_id: Unique identifier for this bot
            bot_name: Display name in Discord
            persona: "arbitrage", "outreach", or "intelligence"
            discord_token: Discord bot token for this bot account
            guild_id: Discord guild ID to join
        """
        self.bot_id = bot_id
        self.bot_name = bot_name
        self.persona = persona
        self.guild_id = guild_id
        
        # Discord client setup
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        self.client = commands.Bot(command_prefix="!", intents=intents)
        self.discord_token = discord_token
        
        # State
        self.is_connected = False
        self.channel = None
        
        # Event handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup Discord event handlers."""
        
        @self.client.event
        async def on_ready():
            logger.info(f"Bot {self.bot_name} is ready!")
            self.is_connected = True
            
            # Join guild and get channel
            guild = self.client.get_guild(self.guild_id)
            if guild:
                # Find or create negotiations channel
                self.channel = discord.utils.get(guild.text_channels, name="the-marketplace-3")
                if not self.channel:
                    self.channel = guild.text_channels[0] if guild.text_channels else None
                
                if self.channel:
                    logger.info(f"Bot {self.bot_name} joined channel: {self.channel.name}")
            else:
                logger.warning(f"Guild {self.guild_id} not found for {self.bot_name}")
        
        @self.client.event
        async def on_message(message):
            # Don't respond to own messages
            if message.author == self.client.user:
                return
            
            # Only in negotiation channel
            if message.channel != self.channel:
                return
            
            # Log message for analysis
            logger.debug(f"[Negotiation] {message.author}: {message.content}")
            
            await self.client.process_commands(message)
    
    async def start(self):
        """Connect bot to Discord."""
        try:
            await self.client.start(self.discord_token)
        except Exception as e:
            logger.error(f"Failed to start bot {self.bot_name}: {e}")
            self.is_connected = False
    
    async def send_message(self, content: str) -> Optional[discord.Message]:
        """
        Send message to negotiation channel.
        
        Args:
            content: Message text (may include chain-of-thought reasoning)
        
        Returns:
            Discord message object or None if failed
        """
        if not self.is_connected or not self.channel:
            logger.warning(f"Bot {self.bot_name} not connected, cannot send message")
            return None
        
        try:
            # Split chain-of-thought from actual message if present
            parts = content.split("[ACTUAL RESPONSE]", 1)
            
            actual_message = parts[-1].strip() if len(parts) > 1 else content
            
            # Send message
            message = await self.channel.send(f"**{self.bot_name}**: {actual_message}")
            logger.info(f"Message sent by {self.bot_name}: {actual_message[:50]}...")
            
            return message
        
        except Exception as e:
            logger.error(f"Error sending message from {self.bot_name}: {e}")
            return None
    
    async def send_negotiation_response(self, counterparty: str, offer: str, 
                                       thinking: str = "") -> Optional[discord.Message]:
        """
        Send a negotiation response with optional chain-of-thought thinking.
        
        Args:
            counterparty: Name of bot making offer
            offer: The offer being made
            thinking: (Optional) Internal reasoning before response
        """
        
        if thinking:
            formatted = f"`[Thinking] {thinking}`\n\n[ACTUAL RESPONSE] {offer}"
        else:
            formatted = offer
        
        return await self.send_message(formatted)
    
    async def close(self):
        """Gracefully close bot connection."""
        if self.client:
            await self.client.close()
        self.is_connected = False
        logger.info(f"Bot {self.bot_name} closed")
    
    def is_ready(self) -> bool:
        """Check if bot is ready to send messages."""
        return self.is_connected and self.channel is not None


class BotMessage:
    """Represents a message in a negotiation."""
    
    def __init__(self, sender: str, receiver: str, content: str, 
                 message_id: str = ""):
        self.sender = sender
        self.receiver = receiver  # Direct recipient or None for channel message
        self.content = content
        self.message_id = message_id
    
    def to_transcript_format(self) -> str:
        """Format for negotiation transcript."""
        return f"{self.sender}: {self.content}"
