"""
Alerts and notifications to human operators.
"""
def alert_ops(message: str, severity: str = "warning"):
    """
    Send alert to human operators. Use when confidence is low or escalation is required.
    """
    prefix = "ALERT OPS"
    if severity == "critical":
        prefix = "CRITICAL"
    elif severity == "info":
        prefix = "OPS"
    print(f"[{prefix}]: {message}")
