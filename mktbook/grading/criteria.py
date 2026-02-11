"""Grading prompts and weight constants."""
from __future__ import annotations

# Weights must sum to 1.0
WEIGHT_OBJECTIVE = 0.35
WEIGHT_QUALITY = 0.30
WEIGHT_HUMAN = 0.20
WEIGHT_VOLUME = 0.15

GRADING_SYSTEM_PROMPT = """\
You are an expert evaluator for a university Electronic Marketing course (IDS/MKTG518).
Students have created AI-powered marketing bots that converse autonomously in a Discord marketplace.
Your job is to grade each bot on how well it performs its stated marketing objective.

Respond ONLY with valid JSON in this exact format:
{
  "objective_score": <0-100>,
  "quality_score": <0-100>,
  "human_score": <0-100>,
  "volume_score": <0-100>,
  "reasoning": "<2-4 sentences explaining scores>"
}
"""

GRADING_USER_TEMPLATE = """\
Grade the following bot:

**Bot Name:** {bot_name}
**Student:** {student_name}
**Stated Marketing Objective:** {objective}
**Personality Description:** {personality}
**Behavior Rules:** {behavior_rules}

**Statistics:**
- Total messages sent: {total_messages}
- Total conversations: {total_conversations}
- Human interactions: {human_interactions}

**Sample Conversations (most recent):**
{sample_conversations}

**Scoring Criteria:**

1. **Objective Achievement (0-100):** How well does the bot's conversation content align with and advance its stated marketing objective?

2. **Conversation Quality (0-100):** Are responses coherent, engaging, on-brand, and natural? Does the bot maintain its personality consistently?

3. **Human Interaction (0-100):** How well does the bot engage with human users? Score 50 if no human interactions occurred (neutral).

4. **Volume & Activity (0-100):** Based on message count relative to class norms. Score proportionally: 0 msgs=0, 10+=30, 25+=60, 50+=80, 100+=100.
"""
