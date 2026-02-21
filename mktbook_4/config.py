"""
Configuration for mktbook_4: Synthetic Studio Economy
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """Central configuration for mktbook_4."""
    
    def __init__(self):
        """Initialize configuration from environment and defaults."""
        
        # API Keys
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        
        # Discord
        self.discord_token = os.getenv("DISCORD_TOKEN_MKTBOOK4", "")
        self.discord_guild_id = int(os.getenv("DISCORD_GUILD_ID_MKTBOOK4", "0"))
        
        # Database
        self.db_path = os.getenv(
            "MKTBOOK_DB_PATH",
            "/opt/mktbook/mktbook.db"
        )
        
        # Image generation
        self.image_generation_model = "dall-e-3"
        self.image_size = "1024x1024"
        self.image_quality = "hd"
        
        # Image storage
        self.image_storage_path = Path(
            os.getenv("IMAGE_STORAGE_PATH", "/opt/mktbook/generated_images")
        )
        self.image_storage_path.mkdir(exist_ok=True, parents=True)
        
        # Bot configuration
        self.bot_names = [
            "Arbitrage",     # Trend hunter, seeks novelty
            "Outreach",      # Community builder, seeks adoption
            "Intelligence",  # Analyst, seeks pattern
            "Trendsetter"    # Tastemaker, seeks influence
        ]
        
        self.bot_personalities = {
            "Arbitrage": "Seeks unique fashion opportunities, value hunter, early adopter",
            "Outreach": "Community-focused, inclusive, wants fashion for everyone",
            "Intelligence": "Analytical, data-driven, seeks patterns in trend adoption",
            "Trendsetter": "Aspirational, luxury-focused, defines high fashion"
        }
        
        # Grading weights
        self.grading_weights = {
            "creativity": 0.35,      # Novel imagery generation
            "influence": 0.35,       # Miranda Priestly index (adoption by peers)
            "aesthetic_quality": 0.20,  # Technical execution (color, silhouette, etc)
            "ethics": 0.10           # IP compliance, diversity, sustainability
        }
        
        # Evaluation styles
        self.evaluation_styles = {
            "Arbitrage": "critical_expert",
            "Outreach": "pragmatist",
            "Intelligence": "trend_evangelist",
            "Trendsetter": "cultural_analyst"
        }
        
        # Scheduler
        self.trend_cycle_interval = 300  # Seconds between trend cycles
        self.max_proposals_per_cycle = 4  # Max proposals from bots per cycle
        
        # Ports
        self.web_port = 8003
        self.web_host = "0.0.0.0"
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        self._validate()
    
    def _validate(self):
        """Validate critical configuration."""
        
        issues = []
        
        if not self.openai_api_key:
            issues.append("OPENAI_API_KEY not set")
        
        if not self.discord_token:
            issues.append("DISCORD_TOKEN_MKTBOOK4 not set")
        
        if self.discord_guild_id == 0:
            issues.append("DISCORD_GUILD_ID_MKTBOOK4 not set")
        
        if issues:
            logger.warning(f"Configuration issues: {', '.join(issues)}")
        else:
            logger.info("Configuration validated successfully")
    
    def get_bot_config(self, bot_name: str) -> dict:
        """Get configuration for specific bot."""
        
        return {
            "name": bot_name,
            "personality": self.bot_personalities.get(bot_name, ""),
            "evaluation_style": self.evaluation_styles.get(bot_name, "critical_expert")
        }
    
    def is_production(self) -> bool:
        """Check if running in production."""
        return os.getenv("ENVIRONMENT", "development") == "production"


def get_config() -> Config:
    """Get global config instance."""
    return _config


# Global config instance
_config = Config()
