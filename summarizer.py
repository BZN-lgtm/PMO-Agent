"""Turns the day's KPIs into a short management narrative.

Uses the Claude API when ANTHROPIC_API_KEY is set; otherwise falls back to a
deterministic template so the pipeline never blocks on the LLM.
"""
from __future__ import annotations

import json
import os

MODEL = os.getenv("AGENT_MODEL", "claude-sonnet-5-5")

PROMPT = """You are a telecom PMO analyst. Write a 4-sentence daily progress
brief for senior management from these KPIs. Lead with completion %, call out
SLA breaches by site ID, and end with one recommended action.

KPIs:
{kpis}"""


def template_summary(k: dict) -> str:
    breaches = ", ".join(k["breach_sites"]) or "none"
    regions = ", ".join(f"{r}: {n}" for r, n in k["by_region"].items())
    action = ("Escalate breached sites to their team leads today."
              if k["sla_breaches"] else "Maintain current deployment plan.")
    return (f"{k['sites_reported']} sites reported on {k['date']}, "
            f"{k['completed']} completed ({k['completion_pct']}%). "
            f"Regional spread — {regions}. "
            f"SLA breaches: {k['sla_breaches']} ({breaches}). {action}")


def summarize(kpis: dict, use_llm: bool = True) -> str:
    if not (use_llm and os.getenv("ANTHROPIC_API_KEY")):
        return template_summary(kpis)
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=MODEL, max_tokens=400,
            messages=[{"role": "user",
                       "content": PROMPT.format(kpis=json.dumps(kpis, default=str))}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:  # network / quota issues should not stop the DPR
        return template_summary(kpis) + f" [LLM fallback: {type(exc).__name__}]"
