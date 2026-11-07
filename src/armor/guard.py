"""Limite di tempo per le operazioni di rete: se una fonte si blocca, si salta e si continua."""
import threading
import time


def with_timeout(fn, seconds: int, label: str = ""):
    box: dict = {}

    def target():
        try:
            box["v"] = fn()
        except BaseException as e:  # noqa: BLE001
            box["e"] = e

    t0 = time.time()
    th = threading.Thread(target=target, daemon=True)
    th.start()
    th.join(seconds)
    if th.is_alive():
        raise TimeoutError(f"{label or 'operazione'} bloccata oltre {seconds} secondi: saltata")
    if "e" in box:
        raise box["e"]
    print(f"   [{label}] fatto in {time.time() - t0:.0f}s", flush=True)
    return box.get("v")
