from collections import deque

_buffer = deque(maxlen=200)


def remember(incident: dict):
    """Append incident to short-term buffer (recent observations)."""
    _buffer.append(incident)


def get_recent(n=50):
    """Return last n incidents from short-term buffer."""
    return list(_buffer)[-n:]


class ShortTermMemory:
    def __init__(self, size=100):
        self.buffer = deque(maxlen=size)

    def add(self, txn):
        self.buffer.append(txn)

    def window(self):
        return list(self.buffer)
