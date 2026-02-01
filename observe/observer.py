from collections import deque
from config import WINDOW_SIZE

WINDOW = deque(maxlen=WINDOW_SIZE)

def observe(event):
    WINDOW.append(event)
    return list(WINDOW)
