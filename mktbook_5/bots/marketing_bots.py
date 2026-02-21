"""
Marketing Bots for mktbook_5: A/B Testing Framework

Sample bot implementations with different strategies.
Each student creates 2+ bots with different marketing philosophies.
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime
import random

import discord
from discord.ext import commands

from models import (
    StrategyType, EcosystemLabel, MarketingStrategy, ProductListing,
    BotInteraction, EngagementMetrics
)

logger = logging.getLogger(__name__)


class MarketingBot(commands.Cog):
    """Base marketing bot class."""
    
    def __init__(self, bot: commands.Bot, config, db, name: str,
                 strategy: MarketingStrategy, ecosystem: EcosystemLabel):
        """
        Args:
            bot: Discord bot instance
            config: Configuration
            db: Database connection
            name: Bot name
            strategy: MarketingStrategy object
            ecosystem: ECOSYSTEM_A or ECOSYSTEM_B
        """
        self.bot = bot
        self.config = config
        self.db = db
        self.name = name
        self.strategy = strategy
        self.ecosystem = ecosystem
        
        # Tracking
        self.interactions: List[BotInteraction] = []
        self.current_metrics = EngagementMetrics(
            session_id=f"{name}_{datetime.now().isoformat()}",
            bot_name=name,
            ecosystem=ecosystem,
            metric_timestamp=datetime.now()
        )
    
    async def pitch_product(self, product: ProductListing, channel) -> BotInteraction:
        """
        Generate marketing message for product based on strategy.
        """
        raise NotImplementedError
    
    async def respond_to_inquiry(self, inquiry: str) -> str:
        """Generate response to customer inquiry."""
        raise NotImplementedError
    
    def log_interaction(self, interaction: BotInteraction):
        """Log an interaction."""
        self.interactions.append(interaction)
        
        # Update metrics
        if interaction.engagement_type == "view":
            self.current_metrics.impressions += 1
        elif interaction.engagement_type == "click":
            self.current_metrics.clicks += 1
        elif interaction.engagement_type == "inquire":
            self.current_metrics.inquiries += 1
        elif interaction.engagement_type == "buy":
            self.current_metrics.conversions += 1
        
        # Update rates
        if self.current_metrics.impressions > 0:
            self.current_metrics.engagement_rate = (
                self.current_metrics.clicks / self.current_metrics.impressions
            )
            self.current_metrics.conversion_rate = (
                self.current_metrics.conversions / self.current_metrics.impressions
            )


class AggressiveVisualBot(MarketingBot):
    """
    Strategy: AGGRESSIVE + VISUAL
    
    Hard-sell approach with eye-catching imagery.
    Direct CTAs, urgency, limited-time offers.
    High energy, bold claims.
    """
    
    async def pitch_product(self, product: ProductListing, channel) -> BotInteraction:
        """Aggressive visual pitch."""
        
        # Build aggressive message with urgency
        urgency_phrases = [
            "🚨 **LIMITED TIME ONLY!**",
            "⏰ **ENDS TODAY!**",
            "🔥 **EXCLUSIVE OFFER!**",
            "💥 **DON'T MISS OUT!**"
        ]
        
        call_to_action = [
            "**→ BUY NOW** before it's gone!",
            "**→ GRAB YOURS** at this amazing price!",
            "**→ CLICK HERE** to claim your deal!",
            "**→ ACT NOW** or lose this offer forever!"
        ]
        
        message = f"""
{random.choice(urgency_phrases)}

**{product.name}** - {product.category}

{product.description}

💰 **NOW ONLY:** ${product.price}
"""
        
        if product.discount_available and product.discount_percent:
            message += f"🎉 **{product.discount_percent}% OFF** the regular price!\n"
        
        message += f"""
✨ **Why you need this:**
"""
        for usp in product.unique_selling_points[:2]:
            message += f"  ✓ {usp}\n"
        
        message += f"\n{random.choice(call_to_action)}\n"
        message += "\n*Supply is limited - act fast!*"
        
        # Track interaction
        interaction = BotInteraction(
            interaction_id=f"{self.name}_{datetime.now().isoformat()}",
            bot_name=self.name,
            ecosystem=self.ecosystem,
            timestamp=datetime.now(),
            user_id="channel_broadcast",
            message_content=message,
            product_shown=product.product_id,
            engagement_type="view",
            sentiment_score=0.8,
            user_reaction="🔥"
        )
        
        self.log_interaction(interaction)
        
        return interaction
    
    async def respond_to_inquiry(self, inquiry: str) -> str:
        """Aggressive response focusing on closing the sale."""
        
        responses = [
            "I'm so glad you're interested! 🎉 This deal is moving FAST. Should I grab it for you right now?",
            "Smart choice asking! This is our best seller - want me to process your order immediately? ⚡",
            "Perfect timing! Lots of people are checking this out TODAY. Ready to secure yours?",
            "I LOVE your interest! 🙌 This price won't last long. Can I complete your purchase now?"
        ]
        
        return random.choice(responses)


class PassiveTextualBot(MarketingBot):
    """
    Strategy: PASSIVE + TEXTUAL
    
    Soft-sell approach with story-driven narratives.
    Builds relationships, no pressure.
    Thoughtful, informative, engaging.
    """
    
    async def pitch_product(self, product: ProductListing, channel) -> BotInteraction:
        """Passive textual pitch."""
        
        story_openers = [
            "I thought you might enjoy learning about something special:",
            "Wanted to share something I find genuinely interesting:",
            "Came across this and thought of you:",
            "Here's something that might resonate with you:",
            "Discovered something worth exploring:"
        ]
        
        message = f"""
{random.choice(story_openers)}

**{product.name}**

{product.description}

What makes this special:
"""
        
        for usp in product.unique_selling_points:
            message += f"• {usp}\n"
        
        message += f"""
**Price:** ${product.price}
"""
        
        if product.discount_available and product.discount_percent:
            message += f"*Currently {product.discount_percent}% off*\n"
        
        message += """
No pressure whatsoever – just thought this aligned with what matters to you.
Feel free to ask if you'd like to know more! 😊
"""
        
        interaction = BotInteraction(
            interaction_id=f"{self.name}_{datetime.now().isoformat()}",
            bot_name=self.name,
            ecosystem=self.ecosystem,
            timestamp=datetime.now(),
            user_id="channel_broadcast",
            message_content=message,
            product_shown=product.product_id,
            engagement_type="view",
            sentiment_score=0.7,
            user_reaction="👍"
        )
        
        self.log_interaction(interaction)
        
        return interaction
    
    async def respond_to_inquiry(self, inquiry: str) -> str:
        """Passive response focusing on relationship."""
        
        responses = [
            "Great question! I'd love to help you think through this. What matters most to you?",
            "That's exactly the kind of curiosity that makes this worth exploring. Tell me what you're looking for.",
            "I appreciate you asking. Let's find the right fit for you – no rush. What's on your mind?",
            "This is the best part – getting to know what you really need. What would make this perfect for you?"
        ]
        
        return random.choice(responses)


class TechnicalDataBot(MarketingBot):
    """
    Strategy: TECHNICAL + TEXTUAL
    
    Data-driven approach with detailed specs and comparisons.
    Transparent, factual, educational.
    Builds trust through information.
    """
    
    async def pitch_product(self, product: ProductListing, channel) -> BotInteraction:
        """Technical spec-focused pitch."""
        
        message = f"""
**{product.name}** - Product Overview

{product.description}

**Specifications:**
• Brand: {product.brand}
• Category: {product.category}
• Price: ${product.price}
"""
        
        if product.discount_available and product.discount_percent:
            message += f"• Current Discount: {product.discount_percent}%\n"
        
        message += "\n**Key Benefits:**\n"
        for usp in product.unique_selling_points:
            message += f"→ {usp}\n"
        
        message += """
**Why This Matters:**
Based on market analysis and customer feedback, here's what data shows:
• 92% customer satisfaction rating
• 4.8/5 average review score
• Outperforms 3 competitor alternatives

**Value Proposition:**
This delivers measurable ROI through [specific metrics].

Questions? I'm here with detailed answers. 📊
"""
        
        interaction = BotInteraction(
            interaction_id=f"{self.name}_{datetime.now().isoformat()}",
            bot_name=self.name,
            ecosystem=self.ecosystem,
            timestamp=datetime.now(),
            user_id="channel_broadcast",
            message_content=message,
            product_shown=product.product_id,
            engagement_type="view",
            sentiment_score=0.75,
            user_reaction="📈"
        )
        
        self.log_interaction(interaction)
        
        return interaction
    
    async def respond_to_inquiry(self, inquiry: str) -> str:
        """Technical response with data."""
        
        responses = [
            "Excellent question. Here's what the data shows: [statistical support]. Based on this, I'd recommend...",
            "That's a common question. Research indicates: [comparative analysis]. This means...",
            "Smart to ask. Here are the metrics that matter: [performance benchmarking]. Bottom line:",
            "Data-driven answer: Comparative testing shows [specific results]. This translates to..."
        ]
        
        return random.choice(responses)


class EmotionalInfluencerBot(MarketingBot):
    """
    Strategy: EMOTIONAL + VISUAL
    
    Connection-driven approach with aspirational imagery.
    Lifestyle marketing, identity alignment.
    Makes users feel part of something bigger.
    """
    
    async def pitch_product(self, product: ProductListing, channel) -> BotInteraction:
        """Emotional lifestyle pitch."""
        
        aspirational_frames = [
            "Imagine yourself with [product]...",
            "Picture this: You're someone who values [product]...",
            "Join the people who've discovered...",
            "This is for the person who believes in...",
            "Meet your new favorite [category]..."
        ]
        
        lifestyle_angles = [
            "confidence and self-expression",
            "quality and intention",
            "tradition and innovation",
            "community and belonging",
            "authenticity and purpose"
        ]
        
        message = f"""
{random.choice(aspirational_frames)}

**{product.name}**

{product.description}

This isn't just a {product.category}. It's about living with {random.choice(lifestyle_angles)}.

🌟 **Join thousands who've made this choice:**
"""
        
        for usp in product.unique_selling_points:
            message += f"✓ {usp}\n"
        
        message += f"""
**Invest in yourself:** ${product.price}
"""
        
        if product.discount_available and product.discount_percent:
            message += f"*Special today: {product.discount_percent}% off*\n"
        
        message += """
This is more than a purchase. It's a statement about who you are.

Ready to join? 💫
"""
        
        interaction = BotInteraction(
            interaction_id=f"{self.name}_{datetime.now().isoformat()}",
            bot_name=self.name,
            ecosystem=self.ecosystem,
            timestamp=datetime.now(),
            user_id="channel_broadcast",
            message_content=message,
            product_shown=product.product_id,
            engagement_type="view",
            sentiment_score=0.85,
            user_reaction="✨"
        )
        
        self.log_interaction(interaction)
        
        return interaction
    
    async def respond_to_inquiry(self, inquiry: str) -> str:
        """Emotional response building connection."""
        
        responses = [
            "I LOVE that you're interested! You're exactly the type of person this resonates with. Tell me your vision.",
            "YES! Your instinct is spot-on. People like you are transforming how we think about [category].",
            "This is what excites me about this community – people who GET it. What drew you in?",
            "Perfect. You're thinking just like our best customers – person-first, impact-driven. Let's make this real."
        ]
        
        return random.choice(responses)
