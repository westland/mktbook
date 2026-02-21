"""
mktbook_5: Bayesian A/B Testing Framework for Marketing Ecosystems

Main entry point for the final Workout - comparing two marketing strategies
using Westland's Bayesian statistical framework.

Students act as "Manager of AI Agents" designing A/B test hypotheses.
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

# Add mktbook_5 to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config
from models import (
    StrategyType, EcosystemLabel, MarketingStrategy, StudentExperiment
)
from ab_testing.manager import ABTestManager
from bayesian.engine import BayesianABEngine
from grading.grade_bot import ComparativeGradeBot
from bots.marketing_bots import (
    AggressiveVisualBot, PassiveTextualBot,
    TechnicalDataBot, EmotionalInfluencerBot
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MktBook5:
    """Main application class for mktbook_5."""
    
    def __init__(self):
        """Initialize mktbook_5 system."""
        
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
        self.test_manager: Optional[ABTestManager] = None
        self.bayesian_engine: Optional[BayesianABEngine] = None
        self.grade_bot: Optional[ComparativeGradeBot] = None
        
        # Active experiments
        self.experiments: dict = {}
    
    async def initialize(self):
        """Initialize all components."""
        
        logger.info("Initializing mktbook_5 components...")
        
        try:
            # Initialize database
            if not os.path.exists(self.config.db_path):
                logger.warning(f"Database not found at {self.config.db_path}, creating...")
                os.makedirs(os.path.dirname(self.config.db_path), exist_ok=True)
            
            self.db = await aiosqlite.connect(self.config.db_path)
            await self._initialize_db_schema()
            logger.info("Database initialized")
            
            # Initialize manager and engines
            self.test_manager = ABTestManager(self.config, self.db)
            logger.info("A/B Test Manager initialized")
            
            self.bayesian_engine = BayesianABEngine(
                prior_mean=self.config.bayesian_prior_mean,
                prior_variance=self.config.bayesian_prior_variance
            )
            logger.info(f"Bayesian Engine initialized (priors: μ={self.config.bayesian_prior_mean}, σ²={self.config.bayesian_prior_variance})")
            
            self.grade_bot = ComparativeGradeBot(self.config, self.db)
            logger.info("Comparative Grade Bot initialized")
            
            logger.info("✓ All components initialized successfully")
        
        except Exception as e:
            logger.error(f"Error during initialization: {e}", exc_info=True)
            raise
    
    async def _initialize_db_schema(self):
        """Create database tables if they don't exist."""
        
        sql_commands = [
            # Experiments table
            """
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY,
                experiment_id TEXT UNIQUE,
                student_name TEXT,
                guild_id INTEGER,
                strategy_a TEXT,
                strategy_b TEXT,
                hypothesis_a TEXT,
                notes TEXT,
                test_duration_hours INTEGER,
                significance_level REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Interactions table
            """
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY,
                experiment_id TEXT,
                interaction_id TEXT,
                bot_name TEXT,
                ecosystem TEXT,
                timestamp TIMESTAMP,
                engagement_type TEXT,
                sentiment_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id)
            )
            """,
            
            # Metrics table
            """
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY,
                experiment_id TEXT,
                bot_name TEXT,
                ecosystem TEXT,
                timestamp TIMESTAMP,
                impressions INTEGER,
                clicks INTEGER,
                inquiries INTEGER,
                conversions INTEGER,
                engagement_rate REAL,
                conversion_rate REAL,
                revenue_generated REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id)
            )
            """,
            
            # Bayesian observations table
            """
            CREATE TABLE IF NOT EXISTS bayesian_observations (
                id INTEGER PRIMARY KEY,
                experiment_id TEXT,
                observation_id TEXT,
                ecosystem TEXT,
                bot_name TEXT,
                metric_type TEXT,
                observed_value REAL,
                variance REAL,
                timestamp TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id)
            )
            """,
            
            # Comparisons table
            """
            CREATE TABLE IF NOT EXISTS comparisons (
                id INTEGER PRIMARY KEY,
                experiment_id TEXT,
                comparison_id TEXT,
                test_metric TEXT,
                mean_diff REAL,
                effect_size REAL,
                p_value REAL,
                prob_a_better REAL,
                prob_b_better REAL,
                recommendation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id)
            )
            """,
            
            # Grades table
            """
            CREATE TABLE IF NOT EXISTS experiment_grades (
                id INTEGER PRIMARY KEY,
                experiment_id TEXT UNIQUE,
                student_name TEXT,
                final_grade REAL,
                trajectory_grade REAL,
                rigor_grade REAL,
                strategy_grade REAL,
                winner_grade REAL,
                winner_ecosystem TEXT,
                winner_confidence REAL,
                feedback TEXT,
                graded_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id)
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
        """Run the mktbook_5 system."""
        
        logger.info("Starting mktbook_5 system...")
        
        try:
            # Initialize components
            await self.initialize()
            
            # Set up Discord event handlers
            @self.discord_bot.event
            async def on_ready():
                logger.info(f"Discord bot connected as {self.discord_bot.user}")
            
            @self.discord_bot.command(name="create_experiment")
            async def create_experiment(ctx, student_name: str):
                """
                Student creates a new A/B experiment.
                Usage: !create_experiment "Your Name"
                """
                try:
                    # Create experiment with sample strategies
                    strategy_a = MarketingStrategy(
                        name="Strategy A",
                        primary_strategy=StrategyType.AGGRESSIVE,
                        secondary_strategy=StrategyType.VISUAL,
                        hypothesis="Aggressive marketing will drive higher conversion",
                        target_audience="Early adopters, high-energy segment",
                        value_proposition="Limited exclusive offer",
                        engagement_prediction=75.0,
                        conversion_prediction=12.0
                    )
                    
                    strategy_b = MarketingStrategy(
                        name="Strategy B",
                        primary_strategy=StrategyType.PASSIVE,
                        secondary_strategy=StrategyType.TEXTUAL,
                        hypothesis="Passive relationship-building will drive loyalty",
                        target_audience="Thoughtful audience seeking value",
                        value_proposition="Aligned with your values",
                        engagement_prediction=60.0,
                        conversion_prediction=8.0
                    )
                    
                    experiment = await self.test_manager.create_experiment(
                        student_name=student_name,
                        guild_id=ctx.guild.id,
                        strategy_a=strategy_a,
                        strategy_b=strategy_b,
                        primary_hypothesis="Aggressive strategy will outperform passive",
                        alternative_hypothesis="Passive strategy will build more loyalty",
                        success_criteria=[
                            "5%+ engagement rate",
                            "2%+ conversion rate",
                            "Clear statistical winner (p < 0.05)"
                        ]
                    )
                    
                    self.experiments[experiment.experiment_id] = experiment
                    
                    embed = discord.Embed(
                        title="📊 A/B Experiment Created",
                        description=f"Manager: {student_name}",
                        color=discord.Color.blue()
                    )
                    
                    embed.add_field(
                        name="Strategy A",
                        value=f"{strategy_a.name}\n*{strategy_a.hypothesis[:50]}...*",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Strategy B",
                        value=f"{strategy_b.name}\n*{strategy_b.hypothesis[:50]}...*",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Experiment ID",
                        value=f"`{experiment.experiment_id}`",
                        inline=False
                    )
                    
                    embed.set_footer(text="Experiment is now live. Bots will begin pitching products.")
                    
                    await ctx.send(embed=embed)
                
                except Exception as e:
                    logger.error(f"Error creating experiment: {e}")
                    await ctx.send(f"Error: {str(e)}")
            
            @self.discord_bot.command(name="experiment_status")
            async def experiment_status(ctx):
                """Show status of all active experiments."""
                
                if not self.experiments:
                    await ctx.send("No active experiments")
                    return
                
                embed = discord.Embed(
                    title="📈 Active Experiments",
                    color=discord.Color.gold()
                )
                
                for exp_id, experiment in self.experiments.items():
                    summary = await self.test_manager.get_experiment_summary(exp_id)
                    
                    if summary:
                        embed.add_field(
                            name=f"{summary['student']} - {exp_id[:8]}...",
                            value=(
                                f"**A:** {summary['strategy_a']['name']}\n"
                                f"**B:** {summary['strategy_b']['name']}\n"
                                f"Status: RUNNING"
                            ),
                            inline=True
                        )
                
                await ctx.send(embed=embed)
            
            @self.discord_bot.command(name="bayesian_summary")
            async def bayesian_summary(ctx):
                """Show Bayesian posterior estimates."""
                
                if not self.bayesian_engine:
                    await ctx.send("Bayesian engine not initialized")
                    return
                
                stats = self.bayesian_engine.get_summary_stats()
                
                embed = discord.Embed(
                    title="🔬 Bayesian Analysis",
                    color=discord.Color.purple()
                )
                
                embed.add_field(
                    name="Prior",
                    value=f"μ={stats['prior']['mean']}, σ²={stats['prior']['variance']}",
                    inline=False
                )
                
                if stats['ecosystem_a']['posterior']:
                    a_post = stats['ecosystem_a']['posterior']
                    embed.add_field(
                        name="Ecosystem A Posterior",
                        value=f"μ={a_post['mean']:.2f}±{a_post['std']:.2f}\nCI=[{a_post['credible_interval'][0]:.1f}, {a_post['credible_interval'][1]:.1f}]",
                        inline=True
                    )
                
                if stats['ecosystem_b']['posterior']:
                    b_post = stats['ecosystem_b']['posterior']
                    embed.add_field(
                        name="Ecosystem B Posterior",
                        value=f"μ={b_post['mean']:.2f}±{b_post['std']:.2f}\nCI=[{b_post['credible_interval'][0]:.1f}, {b_post['credible_interval'][1]:.1f}]",
                        inline=True
                    )
                
                if stats['last_comparison']:
                    comp = stats['last_comparison']
                    embed.add_field(
                        name="Comparison",
                        value=f"P(A>B): {comp['prob_a_better']*100:.0f}%\nP(B>A): {comp['prob_b_better']*100:.0f}%\n{comp['recommendation']}",
                        inline=False
                    )
                
                await ctx.send(embed=embed)
            
            # Start Discord bot
            logger.info(f"Connecting to Discord with guild {self.config.discord_guild_id}...")
            await self.discord_bot.start(self.config.discord_token)
        
        except Exception as e:
            logger.error(f"Error running mktbook_5: {e}", exc_info=True)
            raise
        finally:
            # Cleanup
            if self.db:
                await self.db.close()


async def main():
    """Main entry point."""
    
    app = MktBook5()
    await app.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down mktbook_5")
        sys.exit(0)
