import json
import os
import time

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "lessons.json")
_store = None


def _get_store():
    global _store
    if _store is None:
        _store = LongTermMemory(path=_DEFAULT_PATH)
    return _store


class LongTermMemory:
    def __init__(self, path=None):
        self.path = path or _DEFAULT_PATH
        try:
            with open(self.path) as f:
                self.data = json.load(f)
        except Exception:
            self.data = []

    def save_lesson(self, lesson):
        self.data.append(lesson)
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def retrieve(self, n=5):
        return self.data[-n:]


def store_lesson(diagnosis: str, action: str, outcome: str, metadata: dict = None):
    """Record incident outcome for future learning."""
    lesson = {
        "diagnosis": diagnosis,
        "action": action,
        "outcome": outcome,
        "ts": time.time(),
    }
    if metadata:
        lesson["metadata"] = metadata
    _get_store().save_lesson(lesson)


def get_historical_outcomes(n=5):
    """Return recent incident outcomes for the agent."""
    return _get_store().retrieve(n)
