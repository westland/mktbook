"""
Configuration for mktbook_5: Bayesian A/B Testing Framework
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """Central configuration for mktbook_5."""
    
    def __init__(self):
        """Initialize configuration from environment and defaults."""
        
        # API Keys
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        
        # Discord
        self.discord_token = os.getenv("DISCORD_TOKEN_MKTBOOK5", "")
        self.discord_guild_id = int(os.getenv("DISCORD_GUILD_ID_MKTBOOK5", "0"))
        
        # Database
        self.db_path = os.getenv(
            "MKTBOOK_DB_PATH",
            "/opt/mktbook/mktbook.db"
        )
        
        # A/B Testing configuration
        self.default_test_duration_hours = int(os.getenv("TEST_DURATION_HOURS", "24"))
        self.default_significance_level = float(os.getenv("SIGNIFICANCE_LEVEL", "0.05"))
        self.sample_size_target = int(os.getenv("SAMPLE_SIZE_TARGET", "500"))
        
        # Bayesian priors
        self.bayesian_prior_mean = float(os.getenv("BAYESIAN_PRIOR_MEAN", "50.0"))
        self.bayesian_prior_variance = float(os.getenv("BAYESIAN_PRIOR_VARIANCE", "100.0"))
        
        # Ports
        self.web_port = 8004
        self.web_host = "0.0.0.0"
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Sample strategies (for students to use as template)
        self.sample_strategies = {
            "aggressive_visual": {
                "name": "Aggressive + Visual",
                "description": "Hard-sell with eye-catching imagery"
            },
            "passive_textual": {
                "name": "Passive + Textual",
                "description": "Soft-touch relationship-building"
            },
            "technical_data": {
                "name": "Technical + Data-Driven",
                "description": "Spec-focused transparent approach"
            },
            "emotional_lifestyle": {
                "name": "Emotional + Lifestyle",
                "description": "Aspirational identity alignment"
            }
        }
        
        self._validate()
    
    def _validate(self):
        """Validate critical configuration."""
        
        issues = []
        
        if not self.openai_api_key:
            issues.append("OPENAI_API_KEY not set")
        
        if not self.discord_token:
            issues.append("DISCORD_TOKEN_MKTBOOK5 not set")
        
        if self.discord_guild_id == 0:
            issues.append("DISCORD_GUILD_ID_MKTBOOK5 not set")
        
        if issues:
            logger.warning(f"Configuration issues: {', '.join(issues)}")
        else:
            logger.info("Configuration validated successfully")
    
    def is_production(self) -> bool:
        """Check if running in production."""
        return os.getenv("ENVIRONMENT", "development") == "production"


def get_config() -> Config:
    """Get global config instance."""
    return _config


# Global config instance
_config = Config()
