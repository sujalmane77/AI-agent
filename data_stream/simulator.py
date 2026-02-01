"""
Simulated payment event stream. Aggregates transactions over a 60-second window
and exposes success/failure counts, error distributions, banks/issuers/methods, latency.
"""
import random
import time
from collections import defaultdict

BANKS = ["HDFC", "ICICI", "SBI", "AXIS", "KOTAK"]
ISSUERS = ["VISA", "MASTERCARD", "RUPAY"]
METHODS = ["CARD", "UPI", "NETBANKING"]
ERROR_CODES = ["SUCCESS", "BANK_TIMEOUT", "ISSUER_DOWN", "USER_DECLINED", "NETWORK_ERROR"]


def generate_transaction():
    """Single transaction event."""
    bank = random.choice(BANKS)
    issuer = random.choice(ISSUERS)
    method = random.choice(METHODS)
    # Simulate SBI/issuer degradation occasionally
    if bank == "SBI" and random.random() < 0.35:
        status = "ISSUER_DOWN"
    elif random.random() < 0.08:
        status = "BANK_TIMEOUT"
    elif random.random() < 0.05:
        status = "NETWORK_ERROR"
    elif random.random() < 0.04:
        status = "USER_DECLINED"
    else:
        status = "SUCCESS"

    return {
        "bank": bank,
        "issuer": issuer,
        "method": method,
        "status": status,
        "latency_ms": random.randint(80, 2500),
        "ts": time.time(),
    }


def aggregate_last_60_seconds(events):
    """
    Aggregate events from the last 60 seconds into the format expected by the agent:
    - success_count, failure_count
    - error_code_distribution
    - affected banks, issuers, payment methods
    - average latency
    """
    now = time.time()
    window = [e for e in events if (now - e.get("ts", 0)) <= 60]
    if not window:
        return _empty_aggregate()

    success = [e for e in window if e["status"] == "SUCCESS"]
    failures = [e for e in window if e["status"] != "SUCCESS"]

    error_dist = defaultdict(int)
    for e in window:
        error_dist[e["status"]] += 1

    banks = list({e["bank"] for e in window})
    issuers = list({e["issuer"] for e in window})
    methods = list({e["method"] for e in window})

    failures_by_bank = defaultdict(int)
    failures_by_issuer = defaultdict(int)
    failures_by_method = defaultdict(int)
    for e in failures:
        failures_by_bank[e["bank"]] += 1
        failures_by_issuer[e["issuer"]] += 1
        failures_by_method[e["method"]] += 1

    latencies = [e["latency_ms"] for e in window]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    return {
        "window_seconds": 60,
        "total_count": len(window),
        "success_count": len(success),
        "failure_count": len(failures),
        "success_rate": len(success) / len(window) if window else 0,
        "error_code_distribution": dict(error_dist),
        "affected_banks": banks,
        "affected_issuers": issuers,
        "affected_methods": methods,
        "failures_by_bank": dict(failures_by_bank),
        "failures_by_issuer": dict(failures_by_issuer),
        "failures_by_method": dict(failures_by_method),
        "average_latency_ms": round(avg_latency, 2),
        "sample_size": len(window),
    }


def _empty_aggregate():
    return {
        "window_seconds": 60,
        "total_count": 0,
        "success_count": 0,
        "failure_count": 0,
        "success_rate": 0,
        "error_code_distribution": {},
        "affected_banks": [],
        "affected_issuers": [],
        "affected_methods": [],
        "failures_by_bank": {},
        "failures_by_issuer": {},
        "failures_by_method": {},
        "average_latency_ms": 0,
        "sample_size": 0,
    }


def stream_aggregated(window_sec=60, tick_sec=5):
    """
    Simulate continuous stream: collect events for window_sec, then yield
    one aggregated snapshot every tick_sec. For demo, tick_sec can be 2–5.
    """
    buffer = []
    last_emit = time.time()
    while True:
        buffer.append(generate_transaction())
        # Keep only last 60s
        cutoff = time.time() - window_sec
        buffer = [e for e in buffer if e.get("ts", 0) >= cutoff]
        if time.time() - last_emit >= tick_sec:
            yield aggregate_last_60_seconds(buffer)
            last_emit = time.time()
        time.sleep(0.15)
