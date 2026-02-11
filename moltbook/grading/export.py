"""CSV export for grading results."""
from __future__ import annotations

import csv
import io

from moltbook.db import queries


async def export_csv() -> str:
    """Export latest grades for all bots as CSV text."""
    grades = await queries.get_latest_grades()
    bots = {b.id: b for b in await queries.get_all_bots()}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Bot Name",
        "Student Name",
        "Overall Score",
        "Objective Score (35%)",
        "Quality Score (30%)",
        "Human Score (20%)",
        "Volume Score (15%)",
        "Total Messages",
        "Total Conversations",
        "Human Interactions",
        "Reasoning",
        "Graded At",
    ])

    for g in grades:
        bot = bots.get(g.bot_id)
        writer.writerow([
            bot.bot_name if bot else "Unknown",
            bot.student_name if bot else "Unknown",
            f"{g.overall_score:.1f}",
            f"{g.objective_score:.1f}",
            f"{g.quality_score:.1f}",
            f"{g.human_score:.1f}",
            f"{g.volume_score:.1f}",
            g.total_messages,
            g.total_conversations,
            g.human_interactions,
            g.llm_reasoning,
            g.created_at,
        ])

    return output.getvalue()
