"""Marchio Armor (Patch 52): A in cerchio con freccia di crescita e scritta ARMOR con la gamba della R che diventa una freccia. SVG incorporati, nessun font da caricare."""

LOGO = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><linearGradient id="a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1e293b"/><stop offset="1" stop-color="#020617"/></linearGradient><linearGradient id="b" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#22d3ee"/><stop offset="1" stop-color="#34d399"/></linearGradient></defs><circle cx="256" cy="256" r="206" fill="url(#a)" stroke="url(#b)" stroke-width="12"/><path d="M150 384 L256 124 L362 384" fill="none" stroke="#f8fafc" stroke-width="46" stroke-linecap="round" stroke-linejoin="round"/><polyline points="188.0,296.0 226.0,362.0 324.2,262.4" fill="none" stroke="url(#b)" stroke-width="38" stroke-linecap="round" stroke-linejoin="round"/><polygon points="372.0,214.0 354.2,294.7 291.5,232.9" fill="url(#b)" stroke="url(#b)" stroke-width="10" stroke-linejoin="round"/></svg>'
WORDMARK = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-8 -14 454 130" class="wm" fill="none" stroke="currentColor" stroke-width="15" stroke-linejoin="round" stroke-linecap="round"><g transform="skewX(0) translate(0 0)"><g transform="translate(0 0)"><path d="M4 100 L30 6 L56 100"/></g><g transform="translate(72 0)"><path d="M6 100 V6 H34 Q58 6 58 32 Q58 58 34 58 H6 M30 58 L58 100"/></g><g transform="translate(148 0)"><path d="M6 100 V6 L36 62 L66 6 V100"/></g><g transform="translate(232 0)"><path d="M32 6 A30 47 0 1 0 32.01 6 Z"/></g><g transform="translate(308 0)"><path d="M6 100 V6 H34 Q58 6 58 32 Q58 58 34 58 H6"/><g><polyline points="30.0,58.0 48.0,94.0 85.9,49.4" fill="none" stroke="currentColor" stroke-width="15" stroke-linecap="round" stroke-linejoin="round"/><polygon points="104.0,28.0 99.1,63.2 70.1,38.6" fill="currentColor" stroke="currentColor" stroke-width="10" stroke-linejoin="round"/></g></g></g></svg>'

CSS = """
.brand{display:flex;align-items:center;gap:10px;margin:0}.brand .lg{width:44px;height:44px;flex:none;filter:drop-shadow(0 4px 10px rgba(37,99,235,.35))}.brand .lg svg{width:100%;height:100%}
.brand .wm{height:30px;width:auto;color:var(--tx)}
"""


def html() -> str:
    return f"<h1 class='brand' aria-label='Armor'><span class='lg'>{LOGO}</span>{WORDMARK}</h1>"
