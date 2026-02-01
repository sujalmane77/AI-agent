from config import CONFIDENCE_THRESHOLD, MAX_AUTONOMOUS_VOLUME

def is_safe(confidence: float, volume: float = 0) -> bool:
    """
    If confidence is below threshold, require human approval.
    If volume is above max autonomous limit, do not act autonomously.
    """
    if confidence < CONFIDENCE_THRESHOLD:
        return False
    if volume > MAX_AUTONOMOUS_VOLUME:
        return False
    return True


def should_escalate(agent_result: dict) -> bool:
    """True if agent recommends human approval or confidence < threshold."""
    return agent_result.get("recommend_human_approval", True) or (
        agent_result.get("confidence_score", 0) < CONFIDENCE_THRESHOLD
    )
