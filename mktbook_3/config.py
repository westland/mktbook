"""
Configuration for mktbook_3

Loads settings from environment file (.env_3) to avoid hardcoding credentials.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for mktbook_3."""
    
    def __init__(self, env_file: str = ".env_3"):
        """Load configuration from .env file."""
        self.env_file = env_file
        self.load_from_file()
    
    def load_from_file(self):
        """Load variables from .env_3 file."""
        if os.path.exists(self.env_file):
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"\'')
    
    @property
    def openai_api_key(self) -> str:
        """OpenAI API key for mktbook_3."""
        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            logger.warning("OPENAI_API_KEY not set in environment")
        return key
    
    @property
    def discord_guild_id(self) -> int:
        """Discord Guild ID for mktbook_3."""
        guild_id_str = os.getenv("DISCORD_GUILD_ID_3", "1474787626450948211")
        try:
            return int(guild_id_str)
        except ValueError:
            logger.error(f"Invalid DISCORD_GUILD_ID_3: {guild_id_str}")
            return 1474787626450948211
    
    @property
    def discord_bot_tokens(self) -> dict:
        """
        Discord bot tokens for bots in fleet.
        Format in .env_3: DISCORD_BOT_TOKENS_3=token1,token2,token3
        """
        tokens_str = os.getenv("DISCORD_BOT_TOKENS_3", "")
        if not tokens_str:
            logger.warning("DISCORD_BOT_TOKENS_3 not set")
            return {}
        
        tokens = tokens_str.split(',')
        return {f"bot_{i}": token.strip() for i, token in enumerate(tokens)}
    
    @property
    def database_path(self) -> str:
        """Path to SQLite database."""
        return os.getenv("DATABASE_PATH", "/opt/mktbook/mktbook.db")
    
    @property
    def port(self) -> int:
        """Port for web API (if used)."""
        port_str = os.getenv("PORT_3", "8002")
        try:
            return int(port_str)
        except ValueError:
            return 8002
    
    @property
    def max_bots_in_fleet(self) -> int:
        """Maximum number of bots in fleet."""
        max_bots_str = os.getenv("MAX_BOTS_3", "10")
        try:
            return int(max_bots_str)
        except ValueError:
            return 10
    
    @property
    def negotiation_max_turns(self) -> int:
        """Max turns per negotiation (Red Queen enforcement)."""
        max_turns_str = os.getenv("MAX_TURNS_3", "15")
        try:
            return int(max_turns_str)
        except ValueError:
            return 15
    
    @property
    def negotiation_cooldown(self) -> int:
        """Seconds between negotiation initiations."""
        cooldown_str = os.getenv("NEGOTIATION_COOLDOWN_3", "30")
        try:
            return int(cooldown_str)
        except ValueError:
            return 30
    
    @property
    def log_level(self) -> str:
        """Logging level."""
        return os.getenv("LOG_LEVEL", "INFO")
    
    def to_dict(self) -> dict:
        """Export configuration as dictionary."""
        return {
            "openai_api_key": "***" if self.openai_api_key else "NOT SET",
            "discord_guild_id": self.discord_guild_id,
            "discord_bot_tokens": f"{len(self.discord_bot_tokens)} bots configured",
            "database_path": self.database_path,
            "port": self.port,
            "max_bots": self.max_bots_in_fleet,
            "max_turns": self.negotiation_max_turns,
            "cooldown_seconds": self.negotiation_cooldown,
            "log_level": self.log_level,
        }


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = Config()
        logger.info("Configuration loaded")
        logger.info(f"Settings: {_config.to_dict()}")
    return _config


def reset_config():
    """Reset global config (useful for testing)."""
    global _config
    _config = None
