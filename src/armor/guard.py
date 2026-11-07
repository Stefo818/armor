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


def run_parallel(jobs: dict, workers: int = 6, deadline: float = 240.0) -> dict:
    """Esegue funzioni in parallelo con thread 'daemon' (non bloccano la chiusura del programma).
    jobs = {chiave: funzione}. Restituisce {chiave: ("ok", valore) | ("err", messaggio)}.
    Quello che non finisce entro 'deadline' secondi viene segnato come errore e abbandonato."""
    import queue
    todo: queue.Queue = queue.Queue()
    for k, f in jobs.items():
        todo.put((k, f))
    res: dict = {}
    lock = threading.Lock()

    def worker():
        while True:
            try:
                k, f = todo.get_nowait()
            except queue.Empty:
                return
            try:
                v = ("ok", f())
            except BaseException as e:  # noqa: BLE001
                v = ("err", str(e) or type(e).__name__)
            with lock:
                res[k] = v

    ths = [threading.Thread(target=worker, daemon=True) for _ in range(max(1, min(workers, len(jobs))))]
    for t in ths:
        t.start()
    end = time.time() + deadline
    for t in ths:
        t.join(max(0.1, end - time.time()))
    with lock:
        out = dict(res)
    for k in jobs:
        out.setdefault(k, ("err", f"nessuna risposta entro {int(deadline)} secondi"))
    return out
