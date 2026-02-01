"""
Agent prompt templates for payment operations reasoning.
Structured for optional LLM use; rule-based agent uses same output schema.
"""
AGENT_SYSTEM = """You are a senior payment operations manager working 24/7.
Your goals: maximize successful payments, minimize customer friction, avoid risky/irreversible changes, escalate when confidence is low.

You receive aggregated payment data from the last 60 seconds and optional historical incident outcomes.
Classify the issue, cite evidence, propose ONE safe action, assess risk, and output a confidence score (0.0–1.0).
If confidence is below 0.8, recommend human approval instead of acting autonomously."""

DIAGNOSIS_OPTIONS = [
    "User-related",
    "Bank/issuer degradation",
    "Network or system failure",
    "Retry or routing misconfiguration",
]

ACTION_OPTIONS = [
    "Reroute traffic",
    "Adjust retry policy",
    "Suppress failing path",
    "Alert human operators",
    "Take no action",
]

OUTPUT_FORMAT = """
Output (strict):
- Diagnosis:
- Evidence:
- Proposed Action:
- Risk Assessment:
- Confidence Score:
"""

def build_agent_prompt(aggregated: dict, historical: list) -> str:
    """Build the reasoning prompt from current aggregated data and past outcomes."""
    parts = [
        "## Current aggregated payment data (last 60s)",
        f"- Success count: {aggregated.get('success_count', 0)}",
        f"- Failure count: {aggregated.get('failure_count', 0)}",
        f"- Success rate: {aggregated.get('success_rate', 0):.2%}",
        f"- Error code distribution: {aggregated.get('error_code_distribution', {})}",
        f"- Failures by bank: {aggregated.get('failures_by_bank', {})}",
        f"- Failures by issuer: {aggregated.get('failures_by_issuer', {})}",
        f"- Failures by method: {aggregated.get('failures_by_method', {})}",
        f"- Affected banks: {aggregated.get('affected_banks', [])}",
        f"- Affected issuers: {aggregated.get('affected_issuers', [])}",
        f"- Average latency (ms): {aggregated.get('average_latency_ms', 0)}",
        "",
        "## Diagnosis options: " + ", ".join(DIAGNOSIS_OPTIONS),
        "## Allowed actions: " + ", ".join(ACTION_OPTIONS),
    ]
    if historical:
        parts.extend([
            "",
            "## Recent historical incident outcomes",
            str(historical[-5:]),
        ])
    parts.append(OUTPUT_FORMAT)
    return "\n".join(parts)
