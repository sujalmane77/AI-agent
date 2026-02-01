"""
Rerouting and path-suppression logic for payment traffic.
"""
from config import WINDOW_SIZE  # optional; use if needed


def reroute_traffic(percent: float = 30, reason: str = ""):
    """
    Reroute a percentage of traffic to backup PSP/acquirer.
    Reversible; low risk when percent is moderate.
    """
    msg = f"Rerouting {percent}% of traffic to backup PSP"
    if reason:
        msg += f" — {reason}"
    print(f"[ACTION] {msg}")


def suppress_failing_path(bank_or_issuer: str = None, reason: str = ""):
    """
    Suppress a failing bank/issuer path temporarily to stop sending traffic there.
    Should be reversible via config/feature flag.
    """
    target = bank_or_issuer or "affected path"
    msg = f"Suppressing failing path: {target}"
    if reason:
        msg += f" — {reason}"
    print(f"[ACTION] Suppress: {msg}")
