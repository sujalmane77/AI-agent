from collections import Counter
from config import FAILURE_THRESHOLD

def summarize(window):
    failures = [e for e in window if e["status"] == "FAILED"]
    by_bank = Counter(e["bank"] for e in failures)
    by_error = Counter(e["error_code"] for e in failures)

    return {
        "total_events": len(window),
        "failure_count": len(failures),
        "failures_by_bank": dict(by_bank),
        "errors": dict(by_error)
    }

def reason(summary):
    if summary["failure_count"] < FAILURE_THRESHOLD:
        return {
            "hypothesis": "Normal variance",
            "confidence": 0.3
        }

    dominant_bank = max(summary["failures_by_bank"], key=summary["failures_by_bank"].get)
    dominant_error = max(summary["errors"], key=summary["errors"].get)

    if dominant_error == "ISSUER_TIMEOUT":
        return {
            "hypothesis": f"Issuer degradation at {dominant_bank}",
            "confidence": 0.82
        }

    return {
        "hypothesis": "Network instability",
        "confidence": 0.65
    }
