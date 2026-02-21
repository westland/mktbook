"""
Negotiation Scheduler for mktbook_3

Orchestrates autonomous agent-to-agent negotiations.
Uses chain-of-thought prompting and handles negotiation state machines.

Negotiation Flow:
1. Select initiating and responding bot
2. Initiator makes initial offer
3. Responder evaluates and makes counter-offer or accepts
4. Loop until deal closes or conversation stalls
5. Evaluate final negotiation result
"""

import asyncio
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
from openai import AsyncOpenAI
from ..models import (
    NegotiationContext, DealState, DealOffer, NegotiationPersona
)
from ..engagement import EngagementAnalyzer
from .pairing import PairingStrategy, RandomPairing

logger = logging.getLogger(__name__)


class ConversationScheduler:
    """Manages autonomous negotiations between bots."""
    
    def __init__(self, fleet, openai_client, config):
        """
        Args:
            fleet: BotFleet instance
            openai_client: OpenAI API client
            config: Configuration with OPENAI_API_KEY, etc.
        """
        self.fleet = fleet
        self.openai_client = openai_client
        self.config = config
        
        self.is_running = False
        self.active_negotiations: dict = {}  # negotiation_id -> NegotiationContext
        self.closed_negotiations: list = []
        
        self.analyzer = EngagementAnalyzer()
        self.pairing_strategy: PairingStrategy = RandomPairing()
        
        # Negotiation constants
        self.MIN_TURNS = 2
        self.MAX_TURNS = 15  # Red Queen: force faster deals
        self.TURN_TIMEOUT = 120  # seconds per turn
        self.NEGOTIATION_COOLDOWN = 30  # seconds between negotiations
    
    async def start(self):
        """Start the negotiation scheduler."""
        logger.info("ConversationScheduler started")
        self.is_running = True
        
        # Main loop: periodically initiate new negotiations
        while self.is_running:
            try:
                # Clean up stalled negotiations
                await self._cleanup_stalled_negotiations()
                
                # Initiate new negotiation
                if len(self.fleet.bots) >= 2:
                    await self._initiate_negotiation()
                
                # Wait before next negotiation
                await asyncio.sleep(self.NEGOTIATION_COOLDOWN)
            
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping ConversationScheduler")
        self.is_running = False
    
    async def _initiate_negotiation(self) -> Optional[str]:
        """
        Start a new negotiation between two bots.
        Returns negotiation_id or None if failed.
        """
        
        # Select two bots using pairing strategy
        bots = list(self.fleet.bots.values())
        if len(bots) < 2:
            return None
        
        initiator, responder = self.pairing_strategy.select_pair(bots)
        
        if not initiator or not responder:
            return None
        
        # Create negotiation context
        negotiation_id = f"neg_{int(datetime.now().timestamp())}_{initiator.bot_id[:4]}"
        
        negotiation = NegotiationContext(
            negotiation_id=negotiation_id,
            initiator=initiator.bot_id,
            responder=responder.bot_id,
            initiator_persona=NegotiationPersona[initiator.persona.upper()],
            responder_persona=NegotiationPersona[responder.persona.upper()],
        )
        
        self.active_negotiations[negotiation_id] = negotiation
        
        logger.info(f"Starting negotiation {negotiation_id}: "
                   f"{initiator.bot_name} -> {responder.bot_name}")
        
        # Generate initial offer using chain-of-thought
        initial_offer = await self._generate_offer(
            initiator, responder, negotiation, is_initial=True
        )
        
        if not initial_offer:
            negotiation.state = DealState.ABANDONED
            return negotiation_id
        
        # Send initial offer
        await initiator.send_message(initial_offer)
        negotiation.turn_count += 1
        negotiation.state = DealState.ENGAGING
        
        # Start negotiation loop
        asyncio.create_task(self._negotiation_loop(negotiation, initiator, responder))
        
        return negotiation_id
    
    async def _negotiation_loop(self, negotiation: NegotiationContext, 
                               initiator_bot, responder_bot):
        """Execute back-and-forth negotiation."""
        
        max_turns_reached = False
        
        while self.is_running and negotiation.state in [DealState.ENGAGING, DealState.OBJECTION, DealState.COUNTER_OFFERED]:
            
            # Check turn limit (Red Queen: enforce speed)
            if negotiation.turn_count >= self.MAX_TURNS:
                max_turns_reached = True
                negotiation.state = DealState.STALLED
                logger.warning(f"Negotiation {negotiation.negotiation_id} reached max turns ({self.MAX_TURNS})")
                break
            
            # Responder generates response
            try:
                response = await self._generate_response(
                    responder_bot, initiator_bot, negotiation
                )
                
                if not response:
                    negotiation.state = DealState.ABANDONED
                    break
                
                # Send response
                await responder_bot.send_message(response)
                negotiation.turn_count += 1
                
                # Analyze response for deal signals
                analysis = self.analyzer.analyze_message(negotiation, response, responder_bot.bot_id)
                
                if analysis.contains_agreement:
                    negotiation.mark_deal_closed(analysis.agreement_type or "accept")
                    logger.info(f"Deal CLOSED in negotiation {negotiation.negotiation_id} "
                               f"after {negotiation.turn_count} turns")
                    break
                
                elif analysis.contains_objection:
                    negotiation.state = DealState.OBJECTION
                
                if analysis.is_repetitive_pitch:
                    negotiation.circular_logic_flag = "circular"
                    logger.warning(f"Circular logic detected in {negotiation.negotiation_id}")
                
                # Small delay between turns
                await asyncio.sleep(2)
            
            except asyncio.TimeoutError:
                logger.warning(f"Negotiation {negotiation.negotiation_id} timed out")
                negotiation.state = DealState.STALLED
                break
            
            except Exception as e:
                logger.error(f"Error in negotiation loop: {e}")
                negotiation.state = DealState.ABANDONED
                break
        
        # Mark negotiation as finished
        if negotiation.state == DealState.ENGAGING or negotiation.state == DealState.COUNTER_OFFERED:
            negotiation.state = DealState.STALLED
        
        negotiation.last_activity = datetime.now()
        self.closed_negotiations.append(negotiation)
        
        # Update fleet stats
        self.fleet.update_bot_stats(
            initiator_bot.bot_id,
            closed_deal=negotiation.is_deal_closed(),
            persuasion_turns=negotiation.turn_count
        )
        
        logger.info(f"Negotiation {negotiation.negotiation_id} ended: "
                   f"{'CLOSED' if negotiation.is_deal_closed() else 'STALLED'}")
    
    async def _generate_offer(self, initiator_bot, responder_bot, 
                             negotiation: NegotiationContext, is_initial: bool = False) -> str:
        """Generate initial offer using chain-of-thought."""
        
        persona = initiator_bot.persona
        
        if persona == "arbitrage":
            thinking = (
                "I'm looking for market inefficiencies. What gap can I exploit? "
                "What does the other bot value that I have access to?"
            )
            prompt_goal = "Make an offer that exploits a market gap"
        
        elif persona == "outreach":
            thinking = (
                "This is cold selling. What problem might they have? "
                "How can I make irresistible initial pitch?"
            )
            prompt_goal = "Make compelling initial sales pitch"
        
        elif persona == "intelligence":
            thinking = (
                "I need information. What would make them want to share? "
                "What can I offer in exchange for data?"
            )
            prompt_goal = "Propose data exchange or intelligence gathering"
        
        else:
            thinking = "Generate a business offer"
            prompt_goal = "Make a reasonable offer"
        
        prompt = f"""
You are a {persona} bot named {initiator_bot.bot_name} negotiating with {responder_bot.bot_name}.

Persona guidance:
- {persona.upper()}: {prompt_goal}

Other bot persona: {responder_bot.persona}
Negotiation context: {"Initial approach" if is_initial else "Continuing negotiation"}

Think step by step:
{thinking}

Now generate a concrete offer or pitch to send in Discord chat.
Keep it concise (1-2 sentences max).
Make it sound natural, not robotic.

Format your response as:
[THINKING] Your internal reasoning
[ACTUAL RESPONSE] The message to send
"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200,
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Error generating offer: {e}")
            return None
    
    async def _generate_response(self, responder_bot, initiator_bot, 
                                negotiation: NegotiationContext) -> str:
        """Generate response to offer using chain-of-thought."""
        
        # Build context from negotiation history
        context = (f"Negotiation with {initiator_bot.bot_name}. "
                  f"Turn {negotiation.turn_count}. ")
        
        if negotiation.state == DealState.OBJECTION:
            context += "They raised an objection. How do I counter?"
        else:
            context += "They made an offer. Should I accept, object, or counter?"
        
        prompt = f"""
You are a {responder_bot.persona} bot named {responder_bot.bot_name}.

Current negotiation context:
{context}

Decide:
1. Should you accept this deal? (Need clear agreement signal)
2. Should you raise an objection? (What's wrong?)
3. Should you counter-offer? (What do you propose instead?)

Think about the {responder_bot.persona} persona strategy before responding.

Format response as:
[THINKING] Your decision and reasoning
[ACTUAL RESPONSE] Your message to send
"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200,
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return None
    
    async def _cleanup_stalled_negotiations(self):
        """Remove negotiations that have been idle too long."""
        
        now = datetime.now()
        timeout_threshold = timedelta(seconds=self.TURN_TIMEOUT * 2)
        
        stalled = [
            neg_id for neg_id, neg in self.active_negotiations.items()
            if (now - neg.last_activity) > timeout_threshold
        ]
        
        for neg_id in stalled:
            neg = self.active_negotiations.pop(neg_id)
            neg.state = DealState.STALLED
            self.closed_negotiations.append(neg)
            logger.warning(f"Cleaned up stalled negotiation: {neg_id}")
    
    def get_negotiation_stats(self) -> dict:
        """Get scheduler statistics."""
        total_closed = len(self.closed_negotiations)
        deals_closed = sum(1 for n in self.closed_negotiations if n.is_deal_closed())
        
        return {
            "active_negotiations": len(self.active_negotiations),
            "closed_negotiations": total_closed,
            "deals_closed": deals_closed,
            "conversion_rate": deals_closed / total_closed if total_closed > 0 else 0.0,
            "avg_persuasion_depth": (
                sum(n.turn_count for n in self.closed_negotiations) / total_closed
                if total_closed > 0 else 0
            ),
        }
