"""Analisi dei titoli con FinBERT (modello gratuito addestrato su testi finanziari). Facoltativo: se le librerie o il modello
non sono disponibili, Armor continua con il vocabolario finanziario e lo dichiara nel report."""
_pipe = None
_failed = False


def available() -> bool:
    global _pipe, _failed
    if _pipe is not None:
        return True
    if _failed:
        return False
    try:
        from transformers import pipeline
        _pipe = pipeline("text-classification", model="ProsusAI/finbert", top_k=None, truncation=True, max_length=128)
        return True
    except Exception as e:  # noqa: BLE001
        print("[finbert] non disponibile:", type(e).__name__, str(e)[:80])
        _failed = True
        return False


def score(texts: list[str]) -> list[float] | None:
    """Punteggio da -1 a +1 per ogni testo (probabilità positiva meno negativa), o None se il modello manca."""
    if not texts or not available():
        return None
    out = []
    for i in range(0, len(texts), 32):
        for res in _pipe(texts[i:i + 32]):
            d = {r["label"].lower(): r["score"] for r in res}
            out.append(round(d.get("positive", 0.0) - d.get("negative", 0.0), 2))
    return out
