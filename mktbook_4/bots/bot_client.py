"""
Discord Bot Client for mktbook_4: Synthetic Studio Economy

Each bot is a fashion agent with:
- Fashion narrative generation capability
- Image evaluation skills
- Trend adoption tracking
- Miranda Priestly influence scoring
"""

import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
import asyncio

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


@dataclass
class FashionProposal:
    """A bot's proposed fashion trend."""
    proposer_name: str
    trend_description: str
    visual_strategy: str  # MIRROR, DEMOGRAPHIC_SWAP, etc.
    aesthetic_focus: str  # Color, silhouette, sustainability, etc.
    cultural_angle: str  # Why this matters culturally
    estimated_appeal: float  # 0-100


class FashionBot(commands.Cog):
    """Base fashion bot for evaluating and proposing trends."""
    
    def __init__(self, bot: commands.Bot, config, db, name: str, personality: str):
        """
        Args:
            bot: Discord bot instance
            config: Configuration manager
            db: Database connection
            name: Bot's name (e.g., "Arbitrage", "Outreach", "Intelligence")
            personality: Bot's style descriptor
        """
        self.bot = bot
        self.config = config
        self.db = db
        self.name = name
        self.personality = personality
        self.proposals: List[FashionProposal] = []
        self.influence_score = 0.0
        self.trend_adoption_rate = 0.0
    
    async def propose_trend(self, context_prompt: str) -> FashionProposal:
        """
        Generate a fashion trend proposal.
        
        Args:
            context_prompt: Current fashion context/brief
        
        Returns:
            FashionProposal object
        """
        
        # Use OpenAI to generate proposal
        proposal_prompt = self._build_proposal_prompt(context_prompt)
        
        try:
            response = await self._call_openai(proposal_prompt)
            proposal = self._parse_proposal_response(response)
            self.proposals.append(proposal)
            return proposal
        except Exception as e:
            logger.error(f"Error proposing trend: {e}")
            return self._create_null_proposal()
    
    def _build_proposal_prompt(self, context: str) -> str:
        """Build prompt for trend proposal."""
        
        prompt = f"""You are {self.name}, a fashion industry bot with this personality: {self.personality}

Current fashion context: {context}

Generate an original fashion trend proposal with:
1. A compelling trend description (2-3 sentences)
2. Visual strategy (how to show this trend: MIRROR, DEMOGRAPHIC_SWAP, CULTURAL_REFERENCE, MINIMALIST, MAXIMALIST, SUSTAINABLE, LEGACY)
3. Key aesthetic focus (color, silhouette, texture, trend relevance, originality, brand consistency)
4. Cultural angle (why this matters culturally/socially)
5. Your confidence in appeal (0-100)

Be creative, specific, and fashionable. Consider current cultural moments and emerging values.

Format:
TREND_DESCRIPTION: [description]
VISUAL_STRATEGY: [strategy name]
AESTHETIC_FOCUS: [focus area]
CULTURAL_ANGLE: [cultural significance]
APPEAL: [0-100 number]
"""
        return prompt
    
    def _parse_proposal_response(self, response_text: str) -> FashionProposal:
        """Parse OpenAI response into FashionProposal."""
        
        try:
            lines = response_text.split('\n')
            desc = self._extract_field(lines, "TREND_DESCRIPTION:", "")
            strategy = self._extract_field(lines, "VISUAL_STRATEGY:", "MIRROR")
            aesthetic = self._extract_field(lines, "AESTHETIC_FOCUS:", "")
            cultural = self._extract_field(lines, "CULTURAL_ANGLE:", "")
            appeal = float(self._extract_field(lines, "APPEAL:", "50"))
            
            return FashionProposal(
                proposer_name=self.name,
                trend_description=desc,
                visual_strategy=strategy,
                aesthetic_focus=aesthetic,
                cultural_angle=cultural,
                estimated_appeal=min(100, max(0, appeal))
            )
        except Exception as e:
            logger.error(f"Error parsing proposal: {e}")
            return self._create_null_proposal()
    
    def _extract_field(self, lines: list, field_name: str, default: str) -> str:
        """Extract field value from response."""
        for line in lines:
            if field_name in line:
                return line.split(field_name, 1)[1].strip()
        return default
    
    def _create_null_proposal(self) -> FashionProposal:
        """Create null proposal on error."""
        return FashionProposal(
            proposer_name=self.name,
            trend_description="",
            visual_strategy="MIRROR",
            aesthetic_focus="",
            cultural_angle="",
            estimated_appeal=0
        )
    
    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        # This would use the shared openai_client from main.py
        # Implementation depends on async openai client setup
        pass
    
    async def post_trend_to_discord(self, guild_id: int, proposal: FashionProposal,
                                   image_url: Optional[str] = None):
        """
        Post trend proposal to Discord channel.
        
        Args:
            guild_id: Discord guild ID
            proposal: FashionProposal to post
            image_url: Optional image URL to embed
        """
        
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                logger.warning(f"Guild {guild_id} not found")
                return
            
            # Find channel (use #trends or #announcements)
            channel = discord.utils.find(
                lambda c: c.name in ["trends", "proposals", "announcements"],
                guild.text_channels
            )
            
            if not channel:
                logger.warning(f"Announcement channel not found in {guild.name}")
                return
            
            # Build embed
            embed = discord.Embed(
                title=f"🎨 {self.name}'s Trend Proposal",
                description=proposal.trend_description,
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="Visual Strategy",
                value=proposal.visual_strategy,
                inline=True
            )
            
            embed.add_field(
                name="Aesthetic Focus",
                value=proposal.aesthetic_focus,
                inline=True
            )
            
            embed.add_field(
                name="Cultural Significance",
                value=proposal.cultural_angle,
                inline=False
            )
            
            embed.add_field(
                name="Appeal Confidence",
                value=f"{proposal.estimated_appeal:.0f}%",
                inline=True
            )
            
            embed.set_footer(
                text=f"Proposed by {self.name} | {self.personality}",
                icon_url=guild.icon.url if guild.icon else None
            )
            
            # Add image if available
            if image_url:
                embed.set_image(url=image_url)
            
            await channel.send(embed=embed)
            logger.info(f"Posted trend to {channel.name}")
        
        except Exception as e:
            logger.error(f"Error posting to Discord: {e}")
    
    async def evaluate_and_adopt(self, trend_description: str,
                                evaluations: Dict) -> float:
        """
        Decide whether to adopt/advocate for a trend.
        
        Args:
            trend_description: Description of the trend
            evaluations: Aggregated evaluation metrics
        
        Returns:
            Adoption probability (0-1)
        """
        
        # Consider influence from evaluations
        avg_adoption = evaluations.get("average_adoption", 50) / 100.0
        
        # Consider bot's personality alignment
        personality_bonus = self._calculate_personality_fit(
            trend_description,
            evaluations.get("consensus_aesthetic", {})
        )
        
        # Weighted adoption score
        adoption_score = (avg_adoption * 0.6) + (personality_bonus * 0.4)
        
        # Update influence tracking
        if adoption_score > 0.6:
            self.trend_adoption_rate = (self.trend_adoption_rate * 0.7) + (adoption_score * 0.3)
        
        return min(1.0, adoption_score)
    
    def _calculate_personality_fit(self, trend_desc: str, aesthetic_scores: Dict) -> float:
        """Calculate personality fit to trend."""
        # Simplified: would be more sophisticated in production
        return 0.7
    
    def update_influence_score(self, new_adoptions: int, total_trends: int):
        """
        Update Miranda Priestly influence index.
        
        Args:
            new_adoptions: Trends adopted by other bots
            total_trends: Total trends proposed
        """
        
        if total_trends > 0:
            adoption_rate = new_adoptions / total_trends
            # Exponential weighting of influence
            self.influence_score = (adoption_rate ** 1.5) * 100
        else:
            self.influence_score = 0
        
        logger.info(f"{self.name} influence score: {self.influence_score:.1f}")


class BotFleet:
    """Manages fleet of fashion bots."""
    
    def __init__(self, bot: commands.Bot, config, db):
        """
        Args:
            bot: Discord bot instance
            config: Configuration manager
            db: Database connection
        """
        self.bot = bot
        self.config = config
        self.db = db
        self.bots: Dict[str, FashionBot] = {}
    
    def add_bot(self, name: str, personality: str) -> FashionBot:
        """Create and register a fashion bot."""
        fashion_bot = FashionBot(self.bot, self.config, self.db, name, personality)
        self.bots[name] = fashion_bot
        logger.info(f"Added bot: {name} ({personality})")
        return fashion_bot
    
    async def orchestrate_trend_cycle(self, guild_id: int, image_generator, evaluator):
        """
        Orchestrate full trend proposal → generation → evaluation → adoption cycle.
        
        Args:
            guild_id: Discord guild for posting
            image_generator: ImageGenerator instance
            evaluator: ImageEvaluator instance
        """
        
        try:
            # 1. Get trend proposals from all bots
            proposals = []
            for bot_name, bot in self.bots.items():
                proposal = await bot.propose_trend("Fashion forward, sustainability-focused")
                if proposal.trend_description:
                    proposals.append(proposal)
            
            logger.info(f"Generated {len(proposals)} proposals")
            
            # 2. Generate images for each proposal
            for proposal in proposals:
                # Build image generation prompt
                image_prompt = f"{proposal.trend_description} - {proposal.aesthetic_focus}"
                
                image_url, local_path = await image_generator.generate_fashion_image(
                    proposal.trend_description,
                    image_prompt,
                    proposal.visual_strategy
                )
                
                if image_url:
                    # 3. Post to Discord
                    proposer_bot = self.bots[proposal.proposer_name]
                    await proposer_bot.post_trend_to_discord(guild_id, proposal, image_url)
                    
                    # 4. Collect evaluations from other bots
                    critiques = []
                    for eval_bot_name, eval_bot in self.bots.items():
                        if eval_bot_name != proposal.proposer_name:
                            critique = await evaluator.evaluate_fashion_image(
                                image_url,
                                eval_bot_name,
                                fashion_context=f"Responding to {proposal.proposer_name}'s proposal"
                            )
                            critiques.append(critique)
                    
                    # 5. Aggregate evaluations
                    aggregated = await evaluator.aggregate_evaluations(critiques)
                    
                    # 6. Other bots decide adoption
                    for eval_bot_name, eval_bot in self.bots.items():
                        if eval_bot_name != proposal.proposer_name:
                            adoption_prob = await eval_bot.evaluate_and_adopt(
                                proposal.trend_description,
                                aggregated
                            )
                            logger.info(
                                f"{eval_bot_name} adoption probability for {proposal.proposer_name}'s trend: {adoption_prob:.1%}"
                            )
            
            logger.info("Trend cycle complete")
        
        except Exception as e:
            logger.error(f"Error orchestrating trend cycle: {e}")
