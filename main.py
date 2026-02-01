"""
Payment operations agent runtime.
Continuously observes 60s aggregated payment signals, reasons about root cause,
decides one safe action, and learns from outcomes. Escalates when confidence < 0.8.
"""
import time
from data_stream.simulator import generate_transaction, aggregate_last_60_seconds
from brain.agent import diagnose_and_decide, format_agent_output, get_action_key
from memory.long_term import get_historical_outcomes, store_lesson
from memory.short_term import remember
from guardrails.safety import is_safe, should_escalate
from tools.routing import reroute_traffic, suppress_failing_path
from tools.retry import adjust_retry_policy
from tools.notify import alert_ops
from config import MAX_AUTONOMOUS_VOLUME

# Event buffer for last 60 seconds
_event_buffer = []
AGGREGATION_WINDOW_SEC = 60
TICK_SEC = 5   # for demo: run agent every 5s; use 60 in production


def collect_and_aggregate():
    """Gather events for the window and return aggregated snapshot."""
    global _event_buffer
    now = time.time()
    cutoff = now - AGGREGATION_WINDOW_SEC
    _event_buffer = [e for e in _event_buffer if e.get("ts", 0) >= cutoff]
    return aggregate_last_60_seconds(_event_buffer)


def run_action(action_key: str, result: dict):
    """Execute the chosen tool based on proposed action."""
    if action_key == "reroute":
        reroute_traffic(percent=30, reason=result.get("diagnosis", "")[:50])
    elif action_key == "suppress":
        suppress_failing_path(reason=result.get("diagnosis", "")[:50])
    elif action_key == "retry":
        adjust_retry_policy(backoff_seconds=2.0, reason=result.get("diagnosis", "")[:50])
    elif action_key == "alert":
        alert_ops(result.get("evidence", "Escalation: low confidence or policy."), severity="warning")
    # no_action: do nothing


def main():
    print("\n[Payment operations agent started - 24/7 senior ops manager mode]\n")
    cycle = 0
    total_volume = 0

    while True:
        cycle += 1
        # Simulate incoming events (in production, these come from live stream)
        for _ in range(8):
            evt = generate_transaction()
            _event_buffer.append(evt)
            total_volume += 1

        aggregated = collect_and_aggregate()
        historical = get_historical_outcomes(5)

        result = diagnose_and_decide(aggregated, historical)
        action_key = get_action_key(result["proposed_action"])

        # Strict output format
        print("\n--- AGENT CYCLE", cycle, "---")
        print(format_agent_output(result))
        print()

        incident = {
            "aggregated": aggregated,
            "diagnosis": result["diagnosis"],
            "evidence": result["evidence"],
            "proposed_action": result["proposed_action"],
            "confidence_score": result["confidence_score"],
            "action_key": action_key,
        }
        remember(incident)

        if should_escalate(result):
            alert_ops(
                f"Confidence {result['confidence_score']} < 0.8 — human approval required. "
                f"Proposed: {result['proposed_action']}"
            )
            store_lesson(
                result["diagnosis"],
                "ALERT_ONLY",
                "ESCALATED",
                metadata={"proposed_action": result["proposed_action"], "confidence": result["confidence_score"]},
            )
        elif action_key != "no_action" and is_safe(result["confidence_score"], total_volume):
            run_action(action_key, result)
            store_lesson(
                result["diagnosis"],
                result["proposed_action"],
                "EXECUTED",
                metadata={"action_key": action_key},
            )
        elif action_key != "no_action":
            alert_ops("Action skipped: volume or safety limit exceeded.")
            store_lesson(result["diagnosis"], result["proposed_action"], "SKIPPED_SAFETY", {})
        else:
            store_lesson(result["diagnosis"], "Take no action", "MONITORED", {})

        time.sleep(TICK_SEC)


if __name__ == "__main__":
    main()
