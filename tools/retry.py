"""
Retry policy adjustments for payment operations.
"""
def adjust_retry_policy(
    max_retries: int = None,
    backoff_seconds: float = None,
    reason: str = "",
):
    """
    Adjust retry policy (e.g. reduce retries or increase backoff) to avoid retry storms.
    Reversible via config.
    """
    parts = ["Adjusting retry policy"]
    if max_retries is not None:
        parts.append(f"max_retries={max_retries}")
    if backoff_seconds is not None:
        parts.append(f"backoff={backoff_seconds}s")
    msg = " — ".join(parts)
    if reason:
        msg += f" — {reason}"
    print(f"[ACTION] {msg}")
