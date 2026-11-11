"""Guida breve «Cosa sono questi due numeri?» (Patch 81): per chi arriva per la prima volta e non sa cosa rappresentano Indice Armor e Super Armor Index.
Pesi e famiglie sono letti dal codice, così la guida non diventa vecchia quando cambiano."""
import html as _h

from . import armor_index
from .super_armor import NOMI, PESI


def html() -> str:
    try:
        from . import titan_schede
        g = titan_schede.guida_html()
        if g:
            return g
    except Exception:  # noqa: BLE001
        pass
    E = _h.escape
    fam = "".join(f"<li>{E(n)} <small>{w}%</small></li>" for n, (w, _it) in armor_index.GROUPS.items())
    pil = "".join(f"<li>{E(NOMI[k])} <small>{PESI[k]:.0f}%</small></li>" for k in ("previsione", "armor", "economia", "vix") if PESI.get(k))
    fondi = "<li>Grandi fondi <small>0% · in prova</small></li>" if not PESI.get("fondi") else f"<li>Grandi fondi <small>{PESI['fondi']:.0f}%</small></li>"
    return (CSS + "<details class='gi'><summary><i>?</i><span><b>Nuovo qui? Cosa sono questi due numeri</b><small>Indice Armor e Super Armor Index in 30 secondi</small></span></summary>"
            "<div class='gi-b'>"
            "<p class='gi-lead'>Sono due <b>termometri del rischio</b> dell'S&amp;P 500 (le 500 maggiori aziende americane, il mercato che guida le Borse del mondo, VWCE compreso). "
            "Vanno da <b>1 (mercato sano)</b> a <b>100 (mercato pericoloso e instabile)</b>. Dicono <b>quanto, oggi, i segnali sono preoccupanti</b>, non quando scenderà la Borsa e non cosa comprare o vendere.</p>"
            "<div class='gi-cols'>"
            "<div class='gi-c' style='border-top:4px solid hsl(265,75%,68%)'><h4>Indice Armor</h4><p><b>Misura il rischio di cali e di forte nervosità</b> guardando 8 famiglie di indicatori, ognuna con un peso fisso:</p>"
            f"<ul>{fam}</ul>"
            "<p>Ogni indicatore passa da verde a rosso quando supera soglie storiche; le famiglie si sommano nel numero finale. <b>Come si legge:</b> il testo sotto il numero dice, in passato, con un valore simile, quante volte è arrivato un calo importante rispetto al normale. "
            "È un punteggio di <b>rischio storico</b>, non una previsione di data.</p></div>"
            "<div class='gi-c' style='border-top:4px solid hsl(35,90%,55%)'><h4>Super Armor Index</h4><p><b>È il riassunto di tutto in un solo numero:</b> la media di cinque «pilastri», con pesi fissi scritti prima di guardare i risultati:</p>"
            f"<ul>{pil}{fondi}</ul>"
            "<p>Dentro c'è anche l'Indice Armor (che quindi è uno dei pilastri). <b>Come si legge:</b> cinque fasce, da «Mercato sano» a «Mercato pericoloso e instabile». "
            "Le cinque rotelle sotto mostrano <b>quale pilastro sta spingendo il numero</b>; toccale per il dettaglio. Se i pilastri sono in disaccordo, il numero unico lo segnala.</p></div></div>"
            "<div class='gi-diff'><b>La differenza in una riga:</b> l'Indice Armor è uno dei <b>singoli strumenti</b>; il Super Armor Index li mette <b>tutti insieme</b>, compresa l'economia reale, la paura delle opzioni e la previsione dei modelli.</div>"
            "<p class='gi-lim'><b>Cosa non sono:</b> non sono consigli di investimento e non prevedono il futuro. Hanno una capacità di distinguere i giorni a rischio buona ma imperfetta (circa 70 su 100, dove 50 è tirare a sorte): servono a <b>non farsi sorprendere</b>, non a indovinare.</p>"
            "</div></details>")


CSS = """<style>
.gi{background:var(--card);border:1px solid var(--bd);border-radius:14px;margin:0 0 12px;padding:2px 14px}.gi summary{display:flex;align-items:center;gap:10px;cursor:pointer;padding:9px 0;list-style:none}.gi summary::-webkit-details-marker{display:none}
.gi summary i{flex:none;width:26px;height:26px;border-radius:50%;background:linear-gradient(135deg,var(--ac),#6366f1);color:#fff;font-style:normal;font-weight:800;text-align:center;line-height:26px}
.gi summary span{display:flex;flex-direction:column;font-size:14px}.gi summary small{color:var(--mu);font-size:12px;font-weight:400}.gi[open] summary{border-bottom:1px solid var(--bd)}
.gi-b{padding:8px 0 10px;font-size:13px;line-height:1.5}.gi-lead{margin:4px 0 10px}.gi-cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px}.gi-c{border:1px solid var(--bd);border-radius:12px;padding:8px 12px;background:var(--bg)}
.gi-c h4{margin:0 0 4px;font-size:15px}.gi-c p{margin:4px 0}.gi-c ul{margin:4px 0;padding-left:0;list-style:none;display:flex;flex-wrap:wrap;gap:4px}.gi-c li{border:1px solid var(--bd);border-radius:99px;padding:1px 9px;font-size:12px;background:var(--card)}.gi-c li small{color:var(--mu)}
.gi-diff{margin:10px 0 4px;padding:8px 12px;border-left:5px solid #6366f1;background:var(--bg);border-radius:8px}.gi-lim{margin:6px 0 0;color:var(--mu);font-size:12px}
</style>"""
