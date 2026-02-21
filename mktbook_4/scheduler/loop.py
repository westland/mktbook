"""
Trend Cycle Scheduler for mktbook_4

Orchestrates the full pipeline:
1. Bot proposals
2. DALL-E 3 image generation
3. Multi-bot evaluation (with vision AI)
4. Adoption tracking
5. GradeBot scoring
"""

import logging
import asyncio
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TrendScheduler:
    """Orchestrates fashion trend cycles."""
    
    def __init__(self, config, db, bot_fleet, image_generator, evaluator, grade_bot):
        """
        Args:
            config: Configuration manager
            db: Database connection
            bot_fleet: BotFleet instance
            image_generator: ImageGenerator instance
            evaluator: ImageEvaluator instance
            grade_bot: GradeBot instance for scoring
        """
        self.config = config
        self.db = db
        self.bot_fleet = bot_fleet
        self.image_generator = image_generator
        self.evaluator = evaluator
        self.grade_bot = grade_bot
        
        self.is_running = False
        self.cycle_count = 0
        self.cycle_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        logger.info("Starting trend scheduler")
        self.is_running = True
        self.cycle_task = asyncio.create_task(self._run_scheduler_loop())
    
    async def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping trend scheduler")
        self.is_running = False
        
        if self.cycle_task:
            self.cycle_task.cancel()
            try:
                await self.cycle_task
            except asyncio.CancelledError:
                pass
    
    async def _run_scheduler_loop(self):
        """Main scheduler loop."""
        
        while self.is_running:
            try:
                await self._run_trend_cycle()
                
                # Wait for next cycle
                await asyncio.sleep(self.config.trend_cycle_interval)
            
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(10)  # Wait before retry
    
    async def _run_trend_cycle(self):
        """Execute one complete trend proposal → generation → evaluation → grading cycle."""
        
        self.cycle_count += 1
        cycle_id = f"cycle_{self.cycle_count}_{datetime.now().isoformat()}"
        
        logger.info(f"Starting trend cycle {self.cycle_count}")
        
        try:
            # Step 1: Collect proposals from all bots
            proposals = await self._collect_proposals(cycle_id)
            logger.info(f"Collected {len(proposals)} proposals")
            
            if not proposals:
                logger.warning("No proposals generated this cycle")
                return
            
            # Step 2: Generate images for each proposal
            proposal_images = []
            for proposal in proposals[:self.config.max_proposals_per_cycle]:
                image_data = await self._generate_proposal_image(proposal, cycle_id)
                if image_data:
                    proposal_images.append((proposal, image_data))
            
            logger.info(f"Generated images for {len(proposal_images)} proposals")
            
            # Step 3: Post proposals to Discord with images
            for proposal, image_data in proposal_images:
                await self._post_to_discord(proposal, image_data, cycle_id)
            
            # Step 4: Collect evaluations from other bots
            evaluations = []
            for proposal, image_data in proposal_images:
                proposal_evals = await self._collect_evaluations(
                    proposal, image_data, cycle_id
                )
                evaluations.append((proposal, image_data, proposal_evals))
            
            logger.info(f"Collected evaluations for {len(evaluations)} proposals")
            
            # Step 5: Track adoption decisions
            for proposal, image_data, proposal_evals in evaluations:
                await self._track_adoptions(proposal, proposal_evals, cycle_id)
            
            # Step 6: Grade all proposals
            for proposal, image_data, proposal_evals in evaluations:
                await self._grade_proposal(proposal, image_data, proposal_evals, cycle_id)
            
            # Step 7: Update bot influence scores
            await self._update_influence_scores(cycle_id)
            
            logger.info(f"Trend cycle {self.cycle_count} complete")
        
        except Exception as e:
            logger.error(f"Error in trend cycle: {e}", exc_info=True)
    
    async def _collect_proposals(self, cycle_id: str) -> list:
        """Have all bots propose trends."""
        
        proposals = []
        context = "Current fashion context: Sustainability meets innovation, inclusive luxury, cultural relevance"
        
        for bot_name, bot in self.bot_fleet.bots.items():
            try:
                proposal = await bot.propose_trend(context)
                if proposal.trend_description:
                    proposal.cycle_id = cycle_id
                    proposals.append(proposal)
            except Exception as e:
                logger.error(f"Error collecting proposal from {bot_name}: {e}")
        
        return proposals
    
    async def _generate_proposal_image(self, proposal, cycle_id: str) -> Optional[dict]:
        """Generate DALL-E 3 image for proposal."""
        
        try:
            # Check IP compliance first
            is_compliant, flagged = self.image_generator.check_ip_compliance(
                proposal.trend_description,
                proposal.aesthetic_focus
            )
            
            if not is_compliant:
                logger.warning(f"IP compliance issue in proposal: {flagged}")
            
            # Generate image
            image_url, local_path = await self.image_generator.generate_fashion_image(
                proposal.trend_description,
                f"{proposal.aesthetic_focus} - {proposal.cultural_angle}",
                proposal.visual_strategy
            )
            
            if image_url:
                return {
                    "url": image_url,
                    "local_path": local_path,
                    "compliant": is_compliant,
                    "flagged_items": flagged,
                    "cycle_id": cycle_id
                }
        
        except Exception as e:
            logger.error(f"Error generating image: {e}")
        
        return None
    
    async def _post_to_discord(self, proposal, image_data: dict, cycle_id: str):
        """Post proposal and image to Discord."""
        
        try:
            proposer_bot = self.bot_fleet.bots.get(proposal.proposer_name)
            if proposer_bot:
                await proposer_bot.post_trend_to_discord(
                    self.config.discord_guild_id,
                    proposal,
                    image_data["url"]
                )
                logger.info(f"Posted {proposal.proposer_name}'s trend to Discord")
        except Exception as e:
            logger.error(f"Error posting to Discord: {e}")
    
    async def _collect_evaluations(self, proposal, image_data: dict, cycle_id: str) -> list:
        """Have other bots evaluate the image."""
        
        critiques = []
        
        for eval_bot_name, eval_bot in self.bot_fleet.bots.items():
            if eval_bot_name == proposal.proposer_name:
                continue  # Skip self
            
            try:
                critique = await self.evaluator.evaluate_fashion_image(
                    image_data["url"],
                    eval_bot_name,
                    fashion_context=f"Evaluating {proposal.proposer_name}'s trend: {proposal.trend_description}"
                )
                critiques.append(critique)
            except Exception as e:
                logger.error(f"Error evaluating with {eval_bot_name}: {e}")
        
        return critiques
    
    async def _track_adoptions(self, proposal, critiques: list, cycle_id: str):
        """Track which bots adopt the trend."""
        
        try:
            aggregated_evals = await self.evaluator.aggregate_evaluations(critiques)
            
            # Have each evaluating bot decide adoption
            adoption_count = 0
            for critique in critiques:
                eval_bot = self.bot_fleet.bots.get(critique.evaluator_name)
                if eval_bot:
                    adoption_prob = await eval_bot.evaluate_and_adopt(
                        proposal.trend_description,
                        aggregated_evals
                    )
                    
                    if adoption_prob > 0.6:
                        adoption_count += 1
                        logger.info(
                            f"{critique.evaluator_name} adopts {proposal.proposer_name}'s trend "
                            f"(probability: {adoption_prob:.1%})"
                        )
            
            # Update proposer's influence
            proposer_bot = self.bot_fleet.bots.get(proposal.proposer_name)
            if proposer_bot:
                proposer_bot.update_influence_score(
                    adoption_count,
                    self.cycle_count
                )
        
        except Exception as e:
            logger.error(f"Error tracking adoptions: {e}")
    
    async def _grade_proposal(self, proposal, image_data: dict, critiques: list, cycle_id: str):
        """Grade proposal using GradeBot."""
        
        try:
            grade = await self.grade_bot.grade_fashion_proposal(
                proposal=proposal,
                image_data=image_data,
                evaluations=critiques,
                cycle_id=cycle_id
            )
            
            logger.info(
                f"Graded {proposal.proposer_name}'s trend: "
                f"creativity={grade['creativity']:.1f}, "
                f"influence={grade['influence']:.1f}, "
                f"aesthetic={grade['aesthetic']:.1f}, "
                f"ethics={grade['ethics']:.1f} | "
                f"TOTAL={grade['total']:.1f}"
            )
        
        except Exception as e:
            logger.error(f"Error grading proposal: {e}")
    
    async def _update_influence_scores(self, cycle_id: str):
        """Update Miranda Priestly influence indices for all bots."""
        
        for bot_name, bot in self.bot_fleet.bots.items():
            logger.info(f"{bot_name} | Influence: {bot.influence_score:.1f} | Adoption Rate: {bot.trend_adoption_rate:.1%}")
