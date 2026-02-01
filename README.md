# Payment Operations Agent (Fintech Agent)

An AI payment operations agent that runs like a **senior payment operations manager 24/7**. It observes live payment signals (transaction success/failures, latency, banks, payment methods), detects abnormal behavior, reasons about root cause, and decides whether to intervene—rerouting traffic, adjusting retry policy, suppressing failing paths, or alerting human operators—while respecting safety guardrails and learning from outcomes.

## Goals

- **Maximize successful payments**
- **Minimize customer friction**
- **Avoid risky or irreversible changes**
- **Escalate to humans when confidence is low** (e.g. &lt; 0.8)

## How it works

1. **Observe**  
   Receives aggregated payment data from the last **60 seconds**: success/failure counts, error code distributions, affected banks/issuers/methods, average latency.

2. **Reason**  
   Classifies the issue as:
   - User-related  
   - Bank/issuer degradation  
   - Network or system failure  
   - Retry or routing misconfiguration  

   Uses concrete evidence from the data and (optionally) historical incident outcomes.

3. **Decide**  
   Proposes **one** safe action:
   - Reroute traffic  
   - Adjust retry policy  
   - Suppress failing path  
   - Alert human operators  
   - Take no action  

4. **Risk & confidence**  
   Assigns a confidence score (0.0–1.0). If confidence is below **0.8**, the agent recommends human approval instead of acting autonomously.

5. **Act & learn**  
   Executes the chosen tool only when safe; otherwise alerts ops. Outcomes are stored so the system can improve on similar incidents.

## Output format (strict)

Each cycle prints:

- **Diagnosis:**  
- **Evidence:**  
- **Proposed Action:**  
- **Risk Assessment:**  
- **Confidence Score:**  
- *(If confidence &lt; 0.8)* Recommendation: Human approval required before acting.

## Project structure

```
├── main.py                 # Agent runtime loop
├── config.py               # Thresholds and config
├── data_stream/
│   └── simulator.py        # Simulated 60s aggregated payment events
├── brain/
│   ├── agent.py            # Diagnosis + decisions (rule-based; LLM-pluggable)
│   └── prompts.py          # Agent prompt templates
├── tools/
│   ├── routing.py          # Reroute traffic, suppress failing path
│   ├── retry.py            # Retry policy changes
│   └── notify.py           # Ops alerts
├── memory/
│   ├── short_term.py       # Incident buffer
│   └── long_term.py        # Historical outcomes (lessons)
├── guardrails/
│   └── safety.py           # Confidence + volume checks; escalation
├── requirements.txt
└── README.md
```

## Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   source .venv/bin/activate # macOS/Linux
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the agent:

   ```bash
   python main.py
   ```

The agent runs in a loop: every 5 seconds (configurable) it aggregates the last 60 seconds of simulated payment events, diagnoses, outputs the strict format above, and either executes an action (if safe and confidence ≥ 0.8) or escalates to human operators.

## Configuration

- `config.py`: `CONFIDENCE_THRESHOLD` (0.8), `MAX_AUTONOMOUS_VOLUME`, `AGGREGATION_WINDOW_SEC`, etc.
- In `main.py`: `TICK_SEC` controls how often the agent cycle runs (e.g. 5 for demo, 60 for production-style).

## Safety

- Autonomous actions are only taken when **confidence ≥ 0.8** and volume is within limits.
- Otherwise the agent **alerts human operators** and records the incident for learning.
