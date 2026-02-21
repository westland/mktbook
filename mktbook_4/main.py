"""
mktbook_4: The Synthetic Studio Economy

Main entry point for the fashion economy system where:
- Bots propose fashion trends with DALL-E 3 generated images
- Other bots evaluate images using vision AI
- Adoption is tracked and influence scored
- GradeBot scores proposals on creativity, influence, quality, ethics
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

import discord
from discord.ext import commands
from openai import AsyncOpenAI
import aiosqlite

# Add mktbook_4 to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config
from image_generator import ImageGenerator
from evaluator import ImageEvaluator, EvaluationStyle
from bots.bot_client import FashionBot, BotFleet
from scheduler.loop import TrendScheduler
from grading.evaluator import GradeBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MktBook4:
    """Main application class for mktbook_4."""
    
    def __init__(self):
        """Initialize mktbook_4 system."""
        
        self.config = get_config()
        logger.info(f"Loaded configuration (environment: {self.config.log_level})")
        
        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(api_key=self.config.openai_api_key)
        
        # Initialize Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        self.discord_bot = commands.Bot(
            command_prefix="!",
            intents=intents
        )
        
        # Initialize components
        self.db: Optional[aiosqlite.Connection] = None
        self.image_generator: Optional[ImageGenerator] = None
        self.evaluator: Optional[ImageEvaluator] = None
        self.bot_fleet: Optional[BotFleet] = None
        self.grade_bot: Optional[GradeBot] = None
        self.scheduler: Optional[TrendScheduler] = None
    
    async def initialize(self):
        """Initialize all components."""
        
        logger.info("Initializing mktbook_4 components...")
        
        try:
            # Initialize database
            if not os.path.exists(self.config.db_path):
                logger.warning(f"Database not found at {self.config.db_path}, creating...")
                os.makedirs(os.path.dirname(self.config.db_path), exist_ok=True)
            
            self.db = await aiosqlite.connect(self.config.db_path)
            await self._initialize_db_schema()
            logger.info("Database initialized")
            
            # Initialize generators and evaluators
            self.image_generator = ImageGenerator(self.openai_client, self.config)
            logger.info("Image generator initialized")
            
            self.evaluator = ImageEvaluator(self.openai_client, self.config)
            logger.info("Image evaluator initialized")
            
            # Initialize bot fleet
            self.bot_fleet = BotFleet(self.discord_bot, self.config, self.db)
            
            for bot_name in self.config.bot_names:
                personality = self.config.bot_personalities.get(bot_name, "")
                self.bot_fleet.add_bot(bot_name, personality)
            
            logger.info(f"Bot fleet initialized with {len(self.config.bot_names)} bots")
            
            # Initialize grade bot
            self.grade_bot = GradeBot(self.config, self.db)
            logger.info("Grade bot initialized")
            
            # Initialize scheduler
            self.scheduler = TrendScheduler(
                self.config,
                self.db,
                self.bot_fleet,
                self.image_generator,
                self.evaluator,
                self.grade_bot
            )
            logger.info("Trend scheduler initialized")
            
            logger.info("✓ All components initialized successfully")
        
        except Exception as e:
            logger.error(f"Error during initialization: {e}", exc_info=True)
            raise
    
    async def _initialize_db_schema(self):
        """Create database tables if they don't exist."""
        
        sql_commands = [
            # Proposals table
            """
            CREATE TABLE IF NOT EXISTS proposals (
                id INTEGER PRIMARY KEY,
                cycle_id TEXT,
                proposer TEXT,
                trend_description TEXT,
                visual_strategy TEXT,
                aesthetic_focus TEXT,
                cultural_angle TEXT,
                estimated_appeal REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Images table
            """
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY,
                proposal_id INTEGER,
                image_url TEXT,
                local_path TEXT,
                compliant INTEGER,
                flagged_items TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(proposal_id) REFERENCES proposals(id)
            )
            """,
            
            # Evaluations table
            """
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY,
                image_id INTEGER,
                evaluator TEXT,
                aesthetic_assessment TEXT,
                influence_score REAL,
                adoption_likelihood REAL,
                aesthetic_scores TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(image_id) REFERENCES images(id)
            )
            """,
            
            # Grades table
            """
            CREATE TABLE IF NOT EXISTS grades (
                id INTEGER PRIMARY KEY,
                proposal_id INTEGER,
                cycle_id TEXT,
                proposer TEXT,
                creativity REAL,
                influence REAL,
                aesthetic REAL,
                ethics REAL,
                total REAL,
                feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(proposal_id) REFERENCES proposals(id)
            )
            """,
            
            # Bot influence tracking
            """
            CREATE TABLE IF NOT EXISTS bot_influence (
                id INTEGER PRIMARY KEY,
                bot_name TEXT UNIQUE,
                influence_score REAL,
                adoption_rate REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        try:
            for sql in sql_commands:
                await self.db.execute(sql)
            await self.db.commit()
            logger.info("Database schema initialized")
        except Exception as e:
            logger.error(f"Error initializing database schema: {e}")
    
    async def run(self):
        """Run the mktbook_4 system."""
        
        logger.info("Starting mktbook_4 system...")
        
        try:
            # Initialize components
            await self.initialize()
            
            # Set up Discord event handlers
            @self.discord_bot.event
            async def on_ready():
                logger.info(f"Discord bot connected as {self.discord_bot.user}")
                
                # Start scheduler when bot is ready
                if not self.scheduler.is_running:
                    await self.scheduler.start()
            
            @self.discord_bot.command(name="start_trends")
            async def start_trends(ctx):
                """Command to start trend cycle manually."""
                if self.scheduler.is_running:
                    await ctx.send("Trend scheduler is already running")
                else:
                    await self.scheduler.start()
                    await ctx.send("Trend scheduler started")
            
            @self.discord_bot.command(name="stop_trends")
            async def stop_trends(ctx):
                """Command to stop trend cycle."""
                if self.scheduler.is_running:
                    await self.scheduler.stop()
                    await ctx.send("Trend scheduler stopped")
                else:
                    await ctx.send("Trend scheduler is not running")
            
            @self.discord_bot.command(name="stats")
            async def stats(ctx):
                """Show bot influence statistics."""
                
                embed = discord.Embed(
                    title="🎨 Fashion Bot Statistics",
                    color=discord.Color.purple()
                )
                
                for bot_name, bot in self.bot_fleet.bots.items():
                    embed.add_field(
                        name=bot_name,
                        value=(
                            f"Influence: {bot.influence_score:.1f}\n"
                            f"Adoption Rate: {bot.trend_adoption_rate:.1%}\n"
                            f"Proposals: {len(bot.proposals)}"
                        ),
                        inline=True
                    )
                
                embed.set_footer(text=f"Trends Cycles: {self.scheduler.cycle_count}")
                await ctx.send(embed=embed)
            
            # Start Discord bot
            logger.info(f"Connecting to Discord with guild {self.config.discord_guild_id}...")
            await self.discord_bot.start(self.config.discord_token)
        
        except Exception as e:
            logger.error(f"Error running mktbook_4: {e}", exc_info=True)
            raise
        finally:
            # Cleanup
            if self.scheduler and self.scheduler.is_running:
                await self.scheduler.stop()
            
            if self.db:
                await self.db.close()


async def main():
    """Main entry point."""
    
    app = MktBook4()
    await app.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down mktbook_4")
        sys.exit(0)
