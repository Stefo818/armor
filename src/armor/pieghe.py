# -*- coding: utf-8 -*-
"""Sezioni a tendina: ogni macro-argomento di una pagina si apre e si chiude con una freccetta, chiuso all'apertura.
`fold()` crea una tendina; `compatta()` raggruppa da sola il contenuto di una pagina: ogni titolo di secondo livello (h2) diventa la tendina che contiene ciò che lo segue."""
import html as _h
import re
from html.parser import HTMLParser

CSS = """<style>
details.fold{margin:10px 0;border:1px solid var(--bd);border-radius:14px;background:var(--card);overflow:hidden}
details.fold>summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:10px;padding:13px 16px;font-weight:700;font-size:15px;line-height:1.3;-webkit-tap-highlight-color:transparent}
details.fold>summary::-webkit-details-marker{display:none}
details.fold>summary .fh{flex:1;min-width:0}
details.fold>summary .fs{display:block;font-weight:400;font-size:12.5px;color:var(--mu);margin-top:2px}
details.fold>summary::after{content:"";width:9px;height:9px;border-right:2px solid var(--mu);border-bottom:2px solid var(--mu);transform:rotate(45deg);transition:transform .18s;margin:-4px 4px 0 0;flex:none}
details.fold[open]>summary::after{transform:rotate(225deg);margin-top:4px}
details.fold>summary:hover{background:rgba(127,127,127,.07)}
details.fold>summary:focus-visible{outline:2px solid var(--ac);outline-offset:-2px}
details.fold>.fb{padding:2px 14px 14px;border-top:1px solid var(--bd)}
details.fold>.fb>:first-child{margin-top:12px}
details.fold>.fb>.card,details.fold>.fb>.b5{border:0;box-shadow:none;background:transparent;padding:0;margin-top:12px}
.fold-bar{display:flex;gap:8px;justify-content:flex-end;margin:6px 0 -2px}
.fold-bar button{font:inherit;font-size:12.5px;padding:5px 11px;border-radius:999px;border:1px solid var(--bd);background:var(--card);color:var(--mu);cursor:pointer}
</style>"""

JS = """<script>(function(){if(window.__pieghe)return;window.__pieghe=1;
document.addEventListener('toggle',function(e){var d=e.target;if(d&&d.classList&&d.classList.contains('fold')&&d.open){setTimeout(function(){try{window.dispatchEvent(new Event('resize'))}catch(x){}},60)}},true);
document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('[data-foldall]');if(!b)return;var pg=b.closest('.pg');if(!pg)return;var open=b.getAttribute('data-foldall')==='1';pg.querySelectorAll('details.fold').forEach(function(d){d.open=open})});
document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('[data-go],a[href^="#"]');if(!a)return;setTimeout(function(){var h=(a.getAttribute('data-go')||'');if(!h)return;var t=document.getElementById(h);if(t){var d=t.closest&&t.closest('details.fold');if(d)d.open=true}},0)});
})();</script>"""

_VOID = {"br", "hr", "img", "input", "meta", "link", "source", "col", "wbr", "area", "base", "embed", "param", "track"}


def fold(titolo: str, corpo: str, sub: str = "", aperto: bool = False, extra_cls: str = "") -> str:
    """Una tendina con titolo (e riga di anteprima opzionale). Corpo vuoto → niente."""
    if not corpo or not corpo.strip():
        return ""
    s = f"<span class='fs'>{_h.escape(sub)}</span>" if sub else ""
    return (f"<details class='fold {extra_cls}'{' open' if aperto else ''}><summary><span class='fh'>{_h.escape(titolo)}{s}</span></summary>"
            f"<div class='fb'>{corpo}</div></details>")


class _Top(HTMLParser):
    """Trova gli elementi di primo livello (inizio, fine, nome) di un frammento."""

    def __init__(self, src: str):
        super().__init__(convert_charrefs=False)
        self.src = src
        self.lines = [0]
        for m in re.finditer("\n", src):
            self.lines.append(m.end())
        self.depth = 0
        self.top: list[list] = []   # [start, end, tag, classi]
        self._open: list[tuple[str, int]] = []

    def _pos(self) -> int:
        l, c = self.getpos()
        return self.lines[l - 1] + c

    def handle_starttag(self, tag, attrs):
        if tag in _VOID:
            if self.depth == 0:
                p = self._pos()
                self.top.append([p, p + len(self.get_starttag_text()), tag, ""])
            return
        if self.depth == 0:
            self.top.append([self._pos(), None, tag, dict(attrs).get("class", "") or ""])
        self.depth += 1

    def handle_startendtag(self, tag, attrs):
        if self.depth == 0:
            p = self._pos()
            self.top.append([p, p + len(self.get_starttag_text()), tag, ""])

    def handle_endtag(self, tag):
        if tag in _VOID or self.depth == 0:
            return
        self.depth -= 1
        if self.depth == 0 and self.top and self.top[-1][1] is None:
            self.top[-1][1] = self._pos() + len(f"</{tag}>")


def _segmenti(src: str):
    p = _Top(src)
    try:
        p.feed(src)
        p.close()
    except Exception:  # noqa: BLE001
        return None
    if p.depth != 0 or any(t[1] is None for t in p.top):
        return None
    return p.top


def _titolo(txt: str) -> str:
    return re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", "", txt))).strip()


_HEAD = re.compile(r"<(h[2-4])\b[^>]*>(.*?)</\1>", re.S)
_CARD = re.compile(r"class=['\"][^'\"]*\b(card|b5)\b")


def _carta_con_titolo(src: str, t) -> tuple[str, str] | None:
    """Se l'elemento è una scheda che inizia con un titolo (h2-h4), restituisce (titolo, scheda senza quel titolo)."""
    if t[2] not in ("div", "section"):
        return None
    el = src[t[0]:t[1]]
    m0 = re.match(r"<[^>]+>", el)
    if not m0 or not _CARD.search(m0.group(0)):
        return None
    resto = el[len(m0.group(0)):]
    m = _HEAD.match(resto.lstrip())
    if not m:
        return None
    pos = resto.index(m.group(0))
    return _titolo(m.group(2)), m0.group(0) + resto[:pos] + resto[pos + len(m.group(0)):]


def _raggruppa(src: str, seg: list, starters: list[int], primo_aperto: bool = False) -> str:
    out = [src[:seg[starters[0]][0]]]
    for n, i in enumerate(starters):
        ultimo = n + 1 == len(starters)
        if not ultimo:
            fine = seg[starters[n + 1]][0]
        else:
            k = len(seg)
            while k - 1 > i and seg[k - 1][2] in ("script", "style"):
                k -= 1
            fine = seg[k - 1][1]
        if primo_aperto and n == 0 and i == 0:   # il primo titolo della pagina con la sua introduzione resta visibile
            out.append(src[seg[i][0]:fine])
            if ultimo:
                out.append(src[fine:])
            continue
        carta = _carta_con_titolo(src, seg[i])
        if carta:
            titolo, testa = carta
            corpo = testa + src[seg[i][1]:fine]
        else:
            titolo = _titolo(src[seg[i][0]:seg[i][1]])
            corpo = src[seg[i][1]:fine]
        out.append(fold(titolo, corpo) if corpo.strip() else src[seg[i][0]:seg[i][1]])
        if ultimo:
            out.append(src[fine:])
    return "".join(out)


def compatta(src: str, minimo: int = 2, profondita: int = 3, titolo_aperto: bool = True) -> str:
    """Ogni titolo di sezione di primo livello apre una tendina con ciò che lo segue. Prima si usano gli h2; se non bastano, gli h3 e le schede che iniziano con un titolo.
    L'introduzione prima del primo titolo resta visibile. Se i titoli stanno dentro un contenitore (per esempio <div class='mn'>), si scende dentro."""
    if not src or not re.search(r"<h[23]", src):
        return src
    seg = _segmenti(src)
    if not seg:
        return src
    h2 = [i for i, t in enumerate(seg) if t[2] == "h2"]
    if len(h2) >= minimo:
        return _raggruppa(src, seg, h2, titolo_aperto)
    st = [i for i, t in enumerate(seg) if t[2] == "h3" or (_carta_con_titolo(src, t) is not None and t[2] != "h2")]
    if len(st) >= minimo:
        return _raggruppa(src, seg, st)
    if profondita > 0:
        for t in seg:
            if t[2] in ("div", "section") and len(re.findall(r"<h[23]\b", src[t[0]:t[1]])) >= minimo and "fold" not in t[3]:
                m = re.match(r"<[^>]+>", src[t[0]:t[1]])
                inner = src[t[0] + len(m.group(0)):t[1] - len(f"</{t[2]}>")]
                nuovo = compatta(inner, minimo, profondita - 1, titolo_aperto)
                if nuovo != inner:
                    return src[:t[0]] + m.group(0) + nuovo + f"</{t[2]}>" + src[t[1]:]
    return src
