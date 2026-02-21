"""mktbook_3: The Agentic Economy - Bot-to-Bot Hard Selling"""

__version__ = "0.1.0"
__author__ = "CLAUDE"

from .models import (
    NegotiationPersona,
    DealState,
    NegotiationContext,
    BotProfile,
    GradeMetrics,
)
from .bots.fleet import BotFleet
from .scheduler.loop import ConversationScheduler
from .grading.evaluator import DealEvaluator

__all__ = [
    "NegotiationPersona",
    "DealState",
    "NegotiationContext",
    "BotProfile",
    "GradeMetrics",
    "BotFleet",
    "ConversationScheduler",
    "DealEvaluator",
]
