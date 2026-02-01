"""
Payment operations monitoring dashboard.
Simulates payment traffic, runs the agent loop (observe → reason → decide → guardrail),
and displays metrics and agent reasoning. Not a chatbot — operations monitoring only.
"""
import time
import streamlit as st

from data_stream.simulator import generate_transaction, aggregate_last_60_seconds
from brain.agent import diagnose_and_decide, get_action_key
from memory.long_term import get_historical_outcomes, store_lesson
from guardrails.safety import should_escalate, is_safe
from tools.routing import reroute_traffic
from tools.notify import alert_ops

# Banks we care about for the dashboard (simulator includes HDFC, ICICI, SBI + others)
BANKS_DISPLAY = ["HDFC", "ICICI", "SBI"]

CONFIDENCE_THRESHOLD = 0.8


def init_session_state():
    if "events" not in st.session_state:
        st.session_state.events = []
    if "agent_result" not in st.session_state:
        st.session_state.agent_result = None
    if "action_taken" not in st.session_state:
        st.session_state.action_taken = None


def simulate_traffic(n: int = 25):
    """Add n simulated transactions to the buffer (recent window used for aggregation)."""
    for _ in range(n):
        st.session_state.events.append(generate_transaction())
    # Keep only last 60 seconds by timestamp
    now = time.time()
    st.session_state.events = [e for e in st.session_state.events if (now - e.get("ts", 0)) <= 60]


def get_aggregated():
    """Observe: aggregate failures and metrics from recent events."""
    return aggregate_last_60_seconds(st.session_state.events)


def run_agent_cycle(aggregated: dict):
    """Reason + Decide: run agent; Guardrail: only act if confidence >= 0.8."""
    historical = get_historical_outcomes(5)
    result = diagnose_and_decide(aggregated, historical)
    st.session_state.agent_result = result

    action_key = get_action_key(result["proposed_action"])
    confidence = result["confidence_score"]

    if should_escalate(result):
        st.session_state.action_taken = "escalated"
        alert_ops(
            f"Confidence {confidence} < {CONFIDENCE_THRESHOLD} — human approval required. "
            f"Proposed: {result['proposed_action']}"
        )
        store_lesson(
            result["diagnosis"],
            "ALERT_ONLY",
            "ESCALATED",
            metadata={"proposed_action": result["proposed_action"], "confidence": confidence},
        )
        return
    if action_key == "reroute" and is_safe(confidence, len(st.session_state.events)):
        st.session_state.action_taken = "reroute"
        reroute_traffic(percent=30, reason=result.get("diagnosis", "")[:50])
        store_lesson(result["diagnosis"], result["proposed_action"], "EXECUTED", metadata={"action_key": action_key})
        return
    if action_key != "no_action":
        st.session_state.action_taken = "escalated"
        alert_ops(result.get("evidence", "Low confidence or safety limit."))
        store_lesson(result["diagnosis"], result["proposed_action"], "SKIPPED_SAFETY", {})
        return
    st.session_state.action_taken = "no_action"
    store_lesson(result["diagnosis"], "Take no action", "MONITORED", {})


def render_metrics(aggregated: dict):
    """Display total transactions, success rate, bank-wise failure counts."""
    total = aggregated.get("total_count", 0)
    success = aggregated.get("success_count", 0)
    failure = aggregated.get("failure_count", 0)
    rate = aggregated.get("success_rate", 0)
    by_bank = aggregated.get("failures_by_bank", {})

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total transactions", total)
    with col2:
        st.metric("Success rate", f"{rate:.1%}")
    with col3:
        st.metric("Failures", failure)

    st.subheader("Bank-wise failure counts")
    # Show HDFC, ICICI, SBI first; then any others
    banks_ordered = [b for b in BANKS_DISPLAY if b in by_bank] + [b for b in sorted(by_bank) if b not in BANKS_DISPLAY]
    if not banks_ordered:
        banks_ordered = list(by_bank.keys())
    if by_bank:
        import pandas as pd
        df = pd.DataFrame({"Bank": banks_ordered, "Failures": [by_bank.get(b, 0) for b in banks_ordered]})
        st.bar_chart(df, x="Bank", y="Failures")
    else:
        st.caption("No failures by bank in current window.")


def render_agent_reasoning(result: dict, action_taken: str):
    """Display agent reasoning: diagnosis, evidence, confidence, action or escalation."""
    st.subheader("Agent reasoning")
    st.markdown(f"**Diagnosis:** {result['diagnosis']}")
    st.markdown(f"**Evidence:** {result['evidence']}")
    st.markdown(f"**Confidence score:** {result['confidence_score']}")
    st.markdown(f"**Proposed action:** {result['proposed_action']}")
    st.markdown(f"**Risk assessment:** {result['risk_assessment']}")

    if action_taken == "escalated":
        st.warning("Action: Escalated to human operators (confidence below threshold or safety limit).")
    elif action_taken == "reroute":
        st.success("Action taken: Traffic rerouted (confidence >= 0.8, guardrail passed).")
    elif action_taken == "no_action":
        st.info("Action: No action (monitoring only).")

    # Explainable AI: why this decision
    with st.expander("Explainability — why this decision?"):
        st.caption("The agent uses rule-based logic (no black-box model). You can trace every decision to specific data and a clear rule.")
        st.markdown("**Data that drove this decision:**")
        st.markdown(f"- Evidence cited: *{result['evidence']}*")
        st.markdown(f"- Confidence **{result['confidence_score']}** → "
                    + ("**below 0.8** → human approval required (escalated)." if result["confidence_score"] < 0.8 else "**≥ 0.8** → autonomous action allowed if guardrail passed."))
        st.markdown("**Outcome:** " + (
            "Proposed action was **not** executed automatically; operators were alerted."
            if action_taken == "escalated" else
            "Proposed action was **executed** (reroute)." if action_taken == "reroute" else
            "No intervention; monitoring only."
        ))


def main():
    st.set_page_config(page_title="Payment operations", page_icon="📊", layout="wide")
    st.title("Payment operations monitoring")
    st.caption("Agentic AI operations dashboard — not a chatbot. Simulate traffic, run agent, view reasoning.")

    init_session_state()

    # Sidebar: simulation controls
    with st.sidebar:
        st.header("Simulation")
        if st.button("Simulate 25 transactions"):
            simulate_traffic(25)
            st.rerun()
        if st.button("Simulate 50 transactions"):
            simulate_traffic(50)
            st.rerun()
        st.caption(f"Events in buffer: {len(st.session_state.events)}")

    aggregated = get_aggregated()

    # Metrics
    render_metrics(aggregated)

    st.divider()

    # Agent loop
    st.subheader("Agent loop")
    st.caption("Observe (aggregate) → Reason (detect bank-level degradation) → Decide (propose rerouting) → Guardrail (act only if confidence ≥ 0.8)")

    if st.button("Run agent cycle"):
        if aggregated.get("total_count", 0) < 5:
            st.info("Add more transactions (e.g. Simulate 25) then run the agent.")
        else:
            run_agent_cycle(aggregated)
            st.rerun()

    if st.session_state.agent_result is not None:
        render_agent_reasoning(
            st.session_state.agent_result,
            st.session_state.action_taken or "no_action",
        )


if __name__ == "__main__":
    main()
