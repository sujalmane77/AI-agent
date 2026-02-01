# What the Code Does — Payment Operations Agent

This project is an **AI payment operations agent** that behaves like a 24/7 senior ops manager: it watches payment traffic, spots problems (e.g. bank or issuer issues), decides what to do (reroute, retry, alert), and only acts when it’s safe (confidence ≥ 0.8). Below is what each part does.

---

## 1. High-level flow

- **Data** comes from a **simulated** payment stream (banks, success/failure, latency).
- Events are **aggregated** over the last 60 seconds (totals, success rate, failures by bank/issuer/method, errors, latency).
- The **agent** gets this aggregate (and optional past incident outcomes), **diagnoses** the issue, **proposes one action**, and assigns a **confidence** score.
- **Guardrails** decide: if confidence &lt; 0.8 or volume too high → **escalate** (alert humans); otherwise the system can **execute** the action (reroute, retry, suppress, etc.).
- **Memory**: each cycle is stored short-term; outcomes are stored long-term so future cycles can “learn” from past incidents.

You can run this either as a **CLI loop** (`main.py`) or as a **Streamlit dashboard** (`app.py`).

---

## 2. Data stream (`data_stream/simulator.py`)

**Purpose:** Simulate live payment transactions and turn them into 60-second summaries for the agent.

- **`generate_transaction()`**  
  Creates one fake transaction: random **bank** (HDFC, ICICI, SBI, AXIS, KOTAK), **issuer** (VISA, MASTERCARD, RUPAY), **method** (CARD, UPI, NETBANKING), **status** (SUCCESS, BANK_TIMEOUT, ISSUER_DOWN, USER_DECLINED, NETWORK_ERROR), **latency_ms**, and **timestamp**.  
  SBI is biased to fail more often (ISSUER_DOWN) to simulate bank-level degradation.

- **`aggregate_last_60_seconds(events)`**  
  Takes a list of events and keeps only those in the last 60 seconds (by timestamp). It then computes:
  - **total_count**, **success_count**, **failure_count**, **success_rate**
  - **error_code_distribution** (count per status)
  - **failures_by_bank**, **failures_by_issuer**, **failures_by_method**
  - **affected_banks**, **affected_issuers**, **affected_methods**
  - **average_latency_ms**

  The agent only sees this **aggregated** snapshot, not raw events.

- **`stream_aggregated()`**  
  Optional generator: keeps appending new transactions, trims to last 60s, and yields an aggregate every `tick_sec` seconds (for demos).

---

## 3. Brain — agent logic (`brain/agent.py`, `brain/prompts.py`)

**Purpose:** Decide *what’s wrong* and *what to do*, with evidence and confidence.

- **`diagnose_and_decide(aggregated, historical)`**  
  Rule-based “reasoning” (no LLM required):
  1. If too few transactions (&lt; 10) → “Insufficient sample”, confidence 0.4, **no action**.
  2. If most failures are **USER_DECLINED** → **User-related**; **no action** (automation won’t help).
  3. If failures are **concentrated on one bank** or **ISSUER_DOWN** is high → **Bank/issuer degradation**; propose **Suppress failing path** or **Reroute traffic** (confidence ~0.75–0.82).
  4. If **BANK_TIMEOUT** is high → **Bank/issuer degradation**; propose **Adjust retry policy**.
  5. If **NETWORK_ERROR** is high or **latency + failure rate** are high → **Network or system failure**; propose **Alert human operators**.
  6. If **failure rate** is high and **latency** is high but not clearly user/issuer → **Retry or routing misconfiguration**; propose **Alert human operators**.
  7. Otherwise → **Normal variance** or **unclear**; either no action or alert.

  It returns a dict: **diagnosis**, **evidence**, **proposed_action**, **risk_assessment**, **confidence_score**, and **recommend_human_approval** (True when confidence &lt; 0.8).

- **`get_action_key(proposed_action)`**  
  Maps the text proposal to a tool key: `reroute`, `retry`, `suppress`, `alert`, or `no_action`.

- **`format_agent_output(result)`**  
  Turns that dict into the strict text format (Diagnosis, Evidence, Proposed Action, Risk Assessment, Confidence Score, and “Human approval required” when applicable).

- **`brain/prompts.py`**  
  Holds prompt templates and the list of diagnosis/action options, for future use with an LLM; the current agent is rule-based.

---

## 4. Tools (`tools/routing.py`, `tools/retry.py`, `tools/notify.py`)

**Purpose:** The actual “actions” the agent can take (in production these would call real APIs).

- **`reroute_traffic(percent, reason)`** — Reroute a share of traffic to backup PSP; prints the decision (simulated).
- **`suppress_failing_path(bank_or_issuer, reason)`** — Stop sending traffic to a failing bank/path; prints the decision (simulated).
- **`adjust_retry_policy(max_retries, backoff_seconds, reason)`** — Change retry/backoff; prints the decision (simulated).
- **`alert_ops(message, severity)`** — Notify human operators; prints the alert (simulated).

So: **reroute**, **suppress**, **retry**, and **alert** are the interventions; “no action” means none of these are called.

---

## 5. Guardrails (`guardrails/safety.py`)

**Purpose:** Decide whether the agent is *allowed* to act automatically or must escalate.

- **`is_safe(confidence, volume)`**  
  Returns False if **confidence** &lt; `CONFIDENCE_THRESHOLD` (0.8) or **volume** &gt; `MAX_AUTONOMOUS_VOLUME` (5000). Only when True should the system execute reroute/retry/suppress.

- **`should_escalate(agent_result)`**  
  Returns True if the agent says “recommend human approval” or confidence &lt; 0.8. When True, the flow should **alert ops** and **not** run the proposed action autonomously.

So: **low confidence or high volume → escalate; only high confidence and low volume → act.**

---

## 6. Memory (`memory/short_term.py`, `memory/long_term.py`)

**Purpose:** Remember recent cycles and past outcomes so the agent can “learn” over time.

- **Short-term**  
  - **`remember(incident)`** — Appends one incident (aggregate + diagnosis + action + confidence) to a fixed-size buffer (last 200).
  - **`get_recent(n)`** — Returns the last n incidents. Used for recent context (e.g. “what just happened”).

- **Long-term**  
  - **`store_lesson(diagnosis, action, outcome, metadata)`** — Saves one “lesson” to disk (`memory/lessons.json`): what was diagnosed, what action was taken (or “ALERT_ONLY”, “MONITORED”), and the outcome (e.g. “ESCALATED”, “EXECUTED”).
  - **`get_historical_outcomes(n)`** — Returns the last n lessons. Passed into **`diagnose_and_decide(aggregated, historical)`** so the agent can use past outcomes (e.g. “last time we rerouted for SBI it worked”).

---

## 7. Main loop — CLI (`main.py`)

**Purpose:** Run the agent continuously in the terminal (no UI).

1. **Every 5 seconds** (configurable):
   - **Simulate** 8 new transactions and add them to a global event buffer.
   - **Trim** the buffer to the last 60 seconds.
   - **Aggregate** → get the 60s summary.
   - **Load** last 5 historical outcomes from long-term memory.
   - **Run** `diagnose_and_decide(aggregated, historical)` → get diagnosis, evidence, proposed action, confidence.
   - **Print** the strict output (Diagnosis, Evidence, Proposed Action, Risk Assessment, Confidence Score).
   - **Remember** this cycle in short-term memory.
   - **Guardrail:**
     - If **should_escalate(result)** → **alert_ops**, **store_lesson(..., ESCALATED)**.
     - Else if proposed action is not “no_action” and **is_safe(confidence, volume)** → **run_action(...)** (reroute / retry / suppress / alert), **store_lesson(..., EXECUTED)**.
     - Else if proposed action is not “no_action” → alert, **store_lesson(..., SKIPPED_SAFETY)**.
     - Else → **store_lesson(..., MONITORED)** (no action).
2. **Sleep** until the next tick.

So: **observe (aggregate) → reason (diagnose_and_decide) → decide (action key) → guardrail (escalate or run_action) → remember (short + long term).**

---

## 8. Streamlit dashboard (`app.py`)

**Purpose:** Same agent logic, but with a **web UI** for operations monitoring (not a chatbot).

- **Session state** holds: `events` (list of transactions), `agent_result` (last diagnosis/evidence/action/confidence), `action_taken` (“escalated”, “reroute”, or “no_action”).
- **Sidebar:** Buttons “Simulate 25 transactions” and “Simulate 50 transactions” call **`simulate_traffic(n)`**, which appends n new transactions and trims to the last 60 seconds.
- **Observe:** **`get_aggregated()`** runs **`aggregate_last_60_seconds(events)`** on the current buffer.
- **Display:**
  - **Total transactions**, **Success rate**, **Failures** (three metrics).
  - **Bank-wise failure counts** (bar chart; HDFC, ICICI, SBI emphasized).
- **Agent loop:** Button “Run agent cycle”:
  - Loads **historical outcomes** (last 5).
  - Runs **`diagnose_and_decide(aggregated, historical)`**.
  - Applies **guardrails**: if **should_escalate** → set action to “escalated”, **alert_ops**, **store_lesson(ESCALATED)**; else if **reroute** and **is_safe** → **reroute_traffic**, **store_lesson(EXECUTED)**; else if not “no_action” → escalate and **store_lesson(SKIPPED_SAFETY)**; else **store_lesson(MONITORED)**.
- **Agent reasoning** section shows: **Diagnosis**, **Evidence**, **Confidence score**, **Proposed action**, **Risk assessment**, and whether the system **took action** (reroute), **escalated**, or did **no action**.

So the dashboard **reuses** the same data stream, brain, guardrails, and memory; it only adds the Streamlit UI and button-driven simulation.

---

## 9. Config (`config.py`)

- **WINDOW_SIZE** — Legacy/short-term buffer size.
- **FAILURE_THRESHOLD** — Legacy threshold for “too many failures”.
- **CONFIDENCE_THRESHOLD** (0.8) — Below this → escalate, don’t act.
- **MAX_AUTONOMOUS_VOLUME** (5000) — Above this → don’t act autonomously.
- **AGGREGATION_WINDOW_SEC** (60) — How many seconds of events go into each aggregate.

---

## 10. Summary table

| Component        | Role |
|-----------------|------|
| **data_stream/simulator** | Generate fake transactions; aggregate last 60s into counts, rates, failures by bank/issuer/method, latency. |
| **brain/agent**  | Diagnose (user vs bank/issuer vs network vs retry/routing), propose one action, set confidence; recommend human approval if &lt; 0.8. |
| **tools/**       | Execute (simulated) reroute, suppress, retry policy, alert. |
| **guardrails**   | Block autonomous action when confidence &lt; 0.8 or volume &gt; limit; force escalation. |
| **memory**       | Short-term: recent incidents; long-term: lessons (diagnosis, action, outcome) for future reasoning. |
| **main.py**      | CLI: loop every 5s → simulate, aggregate, diagnose, guardrail, act or escalate, remember. |
| **app.py**       | Streamlit: simulate on button, show metrics + bank failures, run agent on button, show reasoning and action/escalation. |

Overall: the code **simulates** payment traffic, **aggregates** it over 60 seconds, **diagnoses** failure patterns (with rules and optional history), **proposes** one safe action, **enforces** guardrails so it only acts when confidence ≥ 0.8 and volume is safe, and **remembers** outcomes so the system can improve on similar incidents later.
