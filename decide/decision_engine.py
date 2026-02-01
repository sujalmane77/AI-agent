def decide(hypothesis, confidence):
    if confidence >= 0.8:
        return "REROUTE"
    if confidence >= 0.6:
        return "ALERT"
    return "MONITOR"
