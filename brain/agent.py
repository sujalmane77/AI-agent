"""
Payment operations agent: diagnosis, evidence, proposed action, risk, confidence.
Produces strict output format; uses rule-based logic (optionally pluggable LLM later).
"""
from brain.prompts import (
    DIAGNOSIS_OPTIONS,
    ACTION_OPTIONS,
    build_agent_prompt,
)


# Thresholds (can move to config)
FAILURE_SPIKE_THRESHOLD = 0.15   # failure rate above this = anomaly
LATENCY_HIGH_MS = 1800
BANK_CONCENTRATION_THRESHOLD = 0.6  # one bank > 60% of failures
ISSUER_CONCENTRATION_THRESHOLD = 0.5
CONFIDENCE_AUTONOMOUS = 0.8


def diagnose_and_decide(aggregated: dict, historical: list) -> dict:
    """
    Run diagnosis and produce one decision in the strict output format.
    Returns dict with: diagnosis, evidence, proposed_action, risk_assessment, confidence_score.
    """
    total = aggregated.get("total_count") or 0
    success = aggregated.get("success_count", 0)
    failure = aggregated.get("failure_count", 0)
    success_rate = aggregated.get("success_rate", 0)
    error_dist = aggregated.get("error_code_distribution", {})
    failures_by_bank = aggregated.get("failures_by_bank", {})
    failures_by_issuer = aggregated.get("failures_by_issuer", {})
    failures_by_method = aggregated.get("failures_by_method", {})
    avg_latency = aggregated.get("average_latency_ms", 0)

    # Default: no anomaly
    diagnosis = "Normal variance (no significant anomaly)"
    evidence = f"Success rate {success_rate:.1%}, {failure} failures in {total} txns; within normal range."
    proposed_action = "Take no action"
    risk_assessment = "No change; no risk."
    confidence_score = 0.85

    if total < 10:
        return _format_output(
            diagnosis,
            "Insufficient sample size; no reliable diagnosis.",
            "Take no action",
            "Low risk; no intervention.",
            0.4,
        )

    failure_rate = failure / total if total else 0
    user_declined = error_dist.get("USER_DECLINED", 0)
    bank_timeout = error_dist.get("BANK_TIMEOUT", 0)
    issuer_down = error_dist.get("ISSUER_DOWN", 0)
    network_error = error_dist.get("NETWORK_ERROR", 0)

    # User-related: high USER_DECLINED share
    if failure > 0 and user_declined / failure >= 0.5:
        diagnosis = "User-related"
        evidence = f"USER_DECLINED accounts for {user_declined}/{failure} failures; pattern suggests user/card issues rather than infra."
        proposed_action = "Take no action"
        risk_assessment = "Automated intervention unlikely to help; could increase friction."
        confidence_score = 0.82
        return _format_output(diagnosis, evidence, proposed_action, risk_assessment, confidence_score)

    # Bank/issuer degradation: concentrated failures on one bank or issuer
    if failure >= 3:
        by_bank = failures_by_bank
        by_issuer = failures_by_issuer
        top_bank = max(by_bank, key=by_bank.get) if by_bank else None
        top_issuer = max(by_issuer, key=by_issuer.get) if by_issuer else None
        pct_bank = by_bank.get(top_bank, 0) / failure if top_bank else 0
        pct_issuer = by_issuer.get(top_issuer, 0) / failure if top_issuer else 0

        if pct_bank >= BANK_CONCENTRATION_THRESHOLD or issuer_down >= failure * 0.4:
            diagnosis = "Bank/issuer degradation"
            evidence = f"Failures concentrated: bank {top_bank} ({pct_bank:.0%} of failures), ISSUER_DOWN={issuer_down}. Suggests issuer or bank-side degradation."
            proposed_action = "Suppress failing path"
            risk_assessment = "Suppressing one path reduces exposure; low–medium risk if rollback is available."
            confidence_score = 0.78
            if pct_bank >= 0.7 and issuer_down >= 2:
                confidence_score = 0.82
                proposed_action = "Reroute traffic"
            return _format_output(diagnosis, evidence, proposed_action, risk_assessment, confidence_score)

        if bank_timeout >= max(2, failure * 0.4):
            diagnosis = "Bank/issuer degradation"
            evidence = f"BANK_TIMEOUT={bank_timeout} of {failure} failures; indicates bank connectivity or timeout issues."
            proposed_action = "Adjust retry policy"
            risk_assessment = "Retry policy change is reversible; medium risk if backoff is not too aggressive."
            confidence_score = 0.75
            return _format_output(diagnosis, evidence, proposed_action, risk_assessment, confidence_score)

    # Network or system failure
    if network_error >= max(2, failure * 0.35) or (avg_latency >= LATENCY_HIGH_MS and failure_rate >= FAILURE_SPIKE_THRESHOLD):
        diagnosis = "Network or system failure"
        evidence = f"NETWORK_ERROR={network_error}, avg latency={avg_latency}ms, failure rate={failure_rate:.1%}."
        proposed_action = "Alert human operators"
        risk_assessment = "Network/system issues need investigation; autonomous rerouting could mask root cause."
        confidence_score = 0.72
        return _format_output(diagnosis, evidence, proposed_action, risk_assessment, confidence_score)

    # Retry or routing misconfiguration
    if failure_rate >= FAILURE_SPIKE_THRESHOLD and avg_latency > 1500 and not (user_declined / max(failure, 1) >= 0.5):
        diagnosis = "Retry or routing misconfiguration"
        evidence = f"Elevated failure rate ({failure_rate:.1%}) with high latency ({avg_latency}ms); may indicate bad routing or retry storms."
        proposed_action = "Alert human operators"
        risk_assessment = "Misconfiguration changes are sensitive; recommend human review before changing retry or routing."
        confidence_score = 0.68
        return _format_output(diagnosis, evidence, proposed_action, risk_assessment, confidence_score)

    # Anomaly but unclear
    if failure_rate >= FAILURE_SPIKE_THRESHOLD:
        diagnosis = "Possible bank/issuer or network issue; unclear from data"
        evidence = f"Failure rate {failure_rate:.1%} above threshold; error mix: {error_dist}."
        proposed_action = "Alert human operators"
        risk_assessment = "Uncertain root cause; escalating to avoid wrong intervention."
        confidence_score = 0.65
        return _format_output(diagnosis, evidence, proposed_action, risk_assessment, confidence_score)

    return _format_output(diagnosis, evidence, proposed_action, risk_assessment, confidence_score)


def _format_output(diagnosis, evidence, proposed_action, risk_assessment, confidence_score):
    return {
        "diagnosis": diagnosis,
        "evidence": evidence,
        "proposed_action": proposed_action,
        "risk_assessment": risk_assessment,
        "confidence_score": round(confidence_score, 2),
        "recommend_human_approval": confidence_score < CONFIDENCE_AUTONOMOUS,
    }


def format_agent_output(result: dict) -> str:
    """Produce the strict text output for logs/UI."""
    lines = [
        "- Diagnosis: " + result["diagnosis"],
        "- Evidence: " + result["evidence"],
        "- Proposed Action: " + result["proposed_action"],
        "- Risk Assessment: " + result["risk_assessment"],
        "- Confidence Score: " + str(result["confidence_score"]),
    ]
    if result.get("recommend_human_approval"):
        lines.append("- Recommendation: Human approval required before acting (confidence < 0.8).")
    return "\n".join(lines)


def get_action_key(proposed_action: str) -> str:
    """Map proposed_action text to tool key: reroute, retry, suppress, alert, no_action."""
    a = (proposed_action or "").strip().lower()
    if "reroute" in a or "traffic" in a:
        return "reroute"
    if "retry" in a:
        return "retry"
    if "suppress" in a or "failing path" in a:
        return "suppress"
    if "alert" in a or "human" in a or "operators" in a:
        return "alert"
    return "no_action"
