import random
import time

BANKS = ["HDFC", "ICICI", "SBI"]
METHODS = ["CARD", "UPI", "NETBANKING"]
ERRORS = ["SUCCESS", "BANK_TIMEOUT", "ISSUER_DOWN", "USER_DECLINED"]

def generate_transaction():
    bank = random.choice(BANKS)
    method = random.choice(METHODS)

    if bank == "SBI" and random.random() < 0.4:
        error = "ISSUER_DOWN"
    else:
        error = random.choices(ERRORS, weights=[70, 10, 10, 10])[0]

    return {
        "bank": bank,
        "method": method,
        "status": error,
        "latency": random.randint(100, 2000)
    }

def stream_transactions():
    while True:
        yield generate_transaction()
        time.sleep(0.2)
