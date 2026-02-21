"""
mktbook_3 Main Entry Point: The Agentic Economy

Autonomous bot-to-bot hard selling negotiation system.
Focus: Deal closing, not engagement. Success metric: Semantic agreement tokens.

Startup sequence:
1. Load configuration from .env_3
2. Initialize OpenAI client
3. Create bot fleet
4. Register bots for Discord
5. Start fleet and scheduler
6. Run web API for monitoring
"""

import asyncio
import logging
import sys
from datetime import datetime

from openai import AsyncOpenAI
from .config import get_config
from .bots.fleet import BotFleet
from .scheduler.loop import ConversationScheduler
from .grading.evaluator import DealEvaluator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("mktbook_3")


class MktBook3Manager:
    """Main application manager."""
    
    def __init__(self):
        """Initialize mktbook_3."""
        self.config = get_config()
        self.openai_client = AsyncOpenAI(api_key=self.config.openai_api_key)
        self.fleet: BotFleet = None
        self.scheduler: ConversationScheduler = None
        self.evaluator: DealEvaluator = None
        self.start_time = datetime.now()
    
    async def initialize(self):
        """Initialize all components."""
        logger.info("=" * 60)
        logger.info("mktbook_3: The Agentic Economy - Initializing")
        logger.info("=" * 60)
        
        # Validate configuration
        if not self.config.openai_api_key:
            logger.error("OPENAI_API_KEY not configured!")
            raise ValueError("Missing OpenAI API key")
        
        logger.info(f"Discord Guild ID: {self.config.discord_guild_id}")
        logger.info(f"Available bot tokens: {len(self.config.discord_bot_tokens)}")
        
        # Initialize fleet
        self.fleet = BotFleet(self.config.discord_guild_id)
        logger.info("Bot fleet created")
        
        # Register bots from environment
        await self._register_bots()
        
        # Initialize scheduler
        self.scheduler = ConversationScheduler(self.fleet, self.openai_client, self.config)
        logger.info("Negotiation scheduler created")
        
        # Initialize evaluator
        self.evaluator = DealEvaluator(self.openai_client)
        logger.info("Deal evaluator initialized")
        
        logger.info("Initialization complete")
    
    async def _register_bots(self):
        """Register bots from configuration."""
        tokens = self.config.discord_bot_tokens
        personas = ["arbitrage", "outreach", "intelligence"]
        
        if not tokens:
            logger.warning("No Discord bot tokens configured!")
            return
        
        for i, (bot_id, token) in enumerate(tokens.items()):
            persona = personas[i % len(personas)]
            bot_name = f"IDS518_3_Bot_{i+1}_{persona.upper()}"
            
            try:
                self.fleet.register_bot(
                    bot_id=bot_id,
                    bot_name=bot_name,
                    persona=persona,
                    discord_token=token
                )
                logger.info(f"Registered {bot_name}")
            except Exception as e:
                logger.error(f"Failed to register bot {i}: {e}")
    
    async def start(self):
        """Start mktbook_3."""
        logger.info("Starting mktbook_3...")
        
        try:
            # Start fleet
            asyncio.create_task(self.fleet.start_fleet())
            logger.info(f"Fleet started with {len(self.fleet.bots)} bots")
            
            # Wait for bots to connect
            await asyncio.sleep(5)
            
            # Start scheduler
            asyncio.create_task(self.scheduler.start())
            logger.info("Negotiation scheduler started")
            
            # Log startup
            logger.info("=" * 60)
            logger.info("mktbook_3 RUNNING - Autonomous negotiations active")
            logger.info(f"Fleet Stats: {self.fleet.get_fleet_stats()}")
            logger.info("=" * 60)
            
            # Keep running
            while True:
                await asyncio.sleep(30)
                stats = self.fleet.get_fleet_stats()
                sched_stats = self.scheduler.get_negotiation_stats()
                
                logger.info(f"Fleet: {stats['active_bots']}/{stats['total_bots']} active | "
                           f"Deals: {stats['closed_deals']}/{stats['total_negotiations']} | "
                           f"Active Negotiations: {sched_stats['active_negotiations']}")
        
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            await self.shutdown()
        
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down mktbook_3...")
        
        if self.scheduler:
            await self.scheduler.stop()
        
        if self.fleet:
            await self.fleet.stop_fleet()
        
        # Final statistics
        uptime = datetime.now() - self.start_time
        logger.info("=" * 60)
        logger.info(f"mktbook_3 Shutdown Complete (uptime: {uptime})")
        logger.info(f"Final Stats: {self.fleet.get_fleet_stats() if self.fleet else 'N/A'}")
        logger.info("=" * 60)


async def main():
    """Main entry point."""
    manager = MktBook3Manager()
    
    try:
        await manager.initialize()
        await manager.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    logger.info("mktbook_3 Startup: The Agentic Economy")
    asyncio.run(main())
