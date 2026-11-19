// Servizio gratuito Cloudflare per Armor: legge i prezzi e li passa alla pagina con il permesso (CORS) di leggerli dal browser.
// VWCE: sede scelta (?sede=LS Exchange), poi le altre sedi tedesche; futures S&P 500, cambio euro/dollaro e paura (VIX) da Yahoo.
// Nessun dato personale, nessuna chiave. La risposta resta in cache 5 secondi: la pagina può chiedere ogni 15 secondi senza problemi.
const ISIN = 'IE00BK5BQT80';
const UA = { 'User-Agent': 'Mozilla/5.0 (Armor personal dashboard)', 'Accept': 'application/json' };
const CORS = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, OPTIONS', 'Access-Control-Allow-Headers': '*' };
const yh = (s, i, r) => `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(s)}?interval=${i}&range=${r}`;

async function J(u) {
  const r = await fetch(u, { headers: UA, cf: { cacheTtl: 5, cacheEverything: true } });
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}
function serie(js) {
  const r = js.chart.result[0], ts = r.timestamp || [], c = r.indicators.quote[0].close || [], pts = [];
  for (let i = 0; i < ts.length; i++) if (c[i] != null) pts.push([ts[i], c[i]]);
  let now = pts.length ? pts[pts.length - 1] : null;
  const m = r.meta || {};
  if (m.regularMarketPrice && (!now || m.regularMarketTime >= now[0])) now = [m.regularMarketTime, m.regularMarketPrice];
  return { pts, now };
}
const before = (pts, t) => { let v = null; for (const [a, b] of pts) { if (a <= t) v = b; else break; } return v; };
function num(x) {
  if (typeof x === 'number') return x;
  if (x == null) return null;
  const s = String(x);
  const v = s.includes(',') ? parseFloat(s.replace(/\./g, '').replace(',', '.')) : parseFloat(s);
  return isNaN(v) ? null : v;
}
function berlinToUtc(s) {   // «2026-11-18T16:40:00» senza fuso = ora di Berlino
  const naive = Date.parse(s + 'Z');
  const f = new Intl.DateTimeFormat('en-US', { timeZone: 'Europe/Berlin', hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const p = Object.fromEntries(f.formatToParts(new Date(naive)).map(x => [x.type, x.value]));
  const asBerlin = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second);
  return naive - (asBerlin - naive);
}
function toSec(t) {
  const s = String(t);
  if (/^\d{10,13}$/.test(s)) return s.length === 13 ? Math.round(+s / 1000) : +s;
  return Math.round((/(Z|[+-]\d\d:?\d\d)$/.test(s) ? Date.parse(s) : berlinToUtc(s)) / 1000);
}
function venuesOnvista(js) {   // cerca ovunque le quotazioni in euro con prezzo, ora e sede
  const out = [];
  (function walk(o) {
    if (Array.isArray(o)) return o.forEach(walk);
    if (o && typeof o === 'object') {
      const price = num(o.last), t = o.datetimeLast || o.datetime || o.lastTradeTime, cur = o.isoCurrency || o.currency, mk = o.market;
      const venue = (mk && typeof mk === 'object' ? mk.name : null) || o.marketName || (typeof mk === 'string' ? mk : null);
      if (price && t && (cur == null || cur === 'EUR')) { try { out.push({ price, time: toSec(t), venue: String(venue || 'onvista') }); } catch (e) {} }
      Object.values(o).forEach(walk);
    }
  })(js);
  return out;
}
async function sedi() {
  const trovate = [], errori = [];
  const prove = [
    ['onvista', async () => venuesOnvista(await J(`https://api.onvista.de/api/v1/instruments/FUND/ISIN:${ISIN}/snapshot`))],
    ['onvista', async () => venuesOnvista(await J(`https://api.onvista.de/api/v1/etfs/ISIN:${ISIN}/snapshot`))],
    ['tradegate', async () => {
      const js = await J(`https://www.tradegate.de/refresh.php?isin=${ISIN}`), last = num(js.last);
      if (!last || !num(js.executions || 0)) return [];
      return [{ price: last, time: Math.round(Date.now() / 1000), venue: 'Tradegate' }];
    }],
    ['xetra', async () => { const s = serie(await J(yh('VWCE.DE', '1m', '1d'))); return s.now ? [{ price: s.now[1], time: s.now[0], venue: 'Xetra' }] : []; }],
  ];
  const visti = new Set();
  await Promise.all(prove.map(async ([n, f]) => { try { const v = await f(); if (v.length) { if (!visti.has(n)) { trovate.push(...v); if (n !== 'xetra') visti.add(n); } } } catch (e) { errori.push(n + ': ' + e.message); } }));
  return { trovate, errori };
}
function scegli(trovate, sede) {
  if (!trovate.length) return null;
  const xe = trovate.find(v => v.venue === 'Xetra') || trovate[0];
  const ok = trovate.filter(v => Math.abs(v.price / xe.price - 1) < 0.03);   // scarta prezzi anomali
  const tmax = Math.max(...ok.map(v => v.time));
  const pref = (sede || '').toLowerCase();
  const alias = pref === 'francoforte' ? 'frankfurt' : pref;
  const cand = pref ? ok.filter(v => v.venue.toLowerCase().includes(alias) && tmax - v.time <= 1200) : [];
  const best = cand.length ? cand.sort((a, b) => b.time - a.time)[0] : ok.filter(v => tmax - v.time <= 300)[0];
  return { ...best, alts: Object.fromEntries(ok.map(v => [v.venue, [Math.round(v.price * 100) / 100, v.time]])), scelta_preferita: cand.length > 0 };
}

// ---------- Sentinella (PROTOCOLLO_FRAGILITA.md): controlla ogni minuto e manda un avviso con ntfy ----------
const REGOLE = { calo15: -0.008, vixSalto15: 0.10, vixMin: 20, vixAlto: 22, vixSalto5g: 0.10, bandaMedia: 3 };
const dopo = (pts, t) => { let v = null; for (const [a, b] of pts) { if (a <= t) v = b; else break; } return v; };
// Vendite in corso: futures giù di almeno 0,8% in 15 minuti, oppure paura su di almeno 10% in 15 minuti (con paura già da 20 in su).
function rilevaRapido(es, vix) {
  const out = [];
  if (es.length) {
    const [t, p] = es[es.length - 1], p0 = dopo(es, t - 900);
    if (p0 && p / p0 - 1 <= REGOLE.calo15) out.push({ tipo: 'calo', valore: p / p0 - 1, t });
  }
  if (vix.length) {
    const [t, p] = vix[vix.length - 1], p0 = dopo(vix, t - 900);
    if (p0 && p >= REGOLE.vixMin && p / p0 - 1 >= REGOLE.vixSalto15) out.push({ tipo: 'paura', valore: p / p0 - 1, vix: p, t });
  }
  return out;
}
// Terreno fragile: (A) indice appena sceso sotto la media dei 200 giorni (ultime 3 sedute) oppure (B) paura >= 22 e salita >= 10% in 5 sedute.
function rilevaFragile(chiusure, prezzoOra, vixChiusure, vixOra) {
  const c = chiusure.concat([prezzoOra]);
  if (c.length < 205) return null;
  const sotto = [];
  for (let k = c.length - 4; k < c.length; k++) { const m = c.slice(k - 199, k + 1).reduce((x, y) => x + y, 0) / 200; sotto.push(c[k] < m); }
  const A = sotto.slice(1).some((v, i) => v && !sotto[i]);
  const v5 = vixChiusure.length >= 5 ? vixChiusure[vixChiusure.length - 5] : null;
  const B = vixOra >= REGOLE.vixAlto && v5 && vixOra / v5 - 1 >= REGOLE.vixSalto5g;
  return A || B ? { A, B, vix: vixOra, salita5g: v5 ? vixOra / v5 - 1 : null } : null;
}
const pc = (x, d = 1, sg = true) => ((sg && x >= 0 ? '+' : '') + (x * 100).toFixed(d)).replace('.', ',') + '%';
async function giaInviato(chiave, secondi) {
  const cache = caches.default, req = new Request('https://armor.local/' + chiave);
  if (await cache.match(req)) return true;
  await cache.put(req, new Response('1', { headers: { 'Cache-Control': 'max-age=' + secondi } }));
  return false;
}
async function ntfy(topic, titolo, testo, priorita) {
  await fetch('https://ntfy.sh/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ topic, title: titolo, message: testo, priority: priorita, tags: ['chart_with_downwards_trend'] }) });
}
async function controlla(env, prova = false) {
  if (!prova && !env.NTFY_TOPIC) return { errore: 'manca NTFY_TOPIC' };
  const [es, vx, gd, vd] = await Promise.all([J(yh('ES=F', '5m', '1d')).then(serie), J(yh('^VIX', '5m', '1d')).then(serie), J(yh('^GSPC', '1d', '1y')).then(serie), J(yh('^VIX', '1d', '1mo')).then(serie)]);
  const res = { rapido: rilevaRapido(es.pts, vx.pts), fragile: null, inviati: [] };
  const chiusure = gd.pts.map(x => x[1]).slice(0, -1), vixCh = vd.pts.map(x => x[1]).slice(0, -1);
  if (gd.now && vx.now) res.fragile = rilevaFragile(chiusure, gd.now[1], vixCh, vx.now[1]);
  if (prova) return res;   // /sentinella: solo lettura, non manda nulla
  for (const r of res.rapido) {
    if (await giaInviato('rapido-' + r.tipo, 3600)) continue;
    const t = r.tipo === 'calo'
      ? `Futures S&P 500 ${pc(r.valore, 2)} in 15 minuti. Dopo giornate con cali oltre l'1,2%, dal 1990 la mediana a 20 sedute è stata +2% (64% positive): vendere nel panico spesso blocca la perdita. Decidi con calma.`
      : `Paura (VIX) salita a ${r.vix.toFixed(1).replace('.', ',')} (${pc(r.valore, 0)} in 15 minuti): il mercato si sta spaventando.`;
    await ntfy(env.NTFY_TOPIC, r.tipo === 'calo' ? 'Armor: vendite forti in corso' : 'Armor: paura in forte salita', t + ' I prezzi gratuiti hanno 9-15 minuti di ritardo.', 5);
    res.inviati.push(r.tipo);
  }
  if (res.fragile && !(await giaInviato('fragile', 43200))) {
    const f = res.fragile, why = [f.B ? `paura a ${f.vix.toFixed(1).replace('.', ',')} e salita del ${(f.salita5g * 100).toFixed(0)}% in 5 giorni` : null, f.A ? "l'indice è appena sceso sotto la media dei 200 giorni" : null].filter(Boolean).join('; ');
    await ntfy(env.NTFY_TOPIC, 'Armor: terreno fragile', `Oggi: ${why}. Dal 1990, in giorni così il mercato ha perso oltre l'1,2% il giorno dopo 1 volta su 5 circa (di norma 1 su 11). Non è una previsione: è un invito a non aggiungere capitale in fretta.`, 4);
    res.inviati.push('fragile');
  }
  return res;
}

export default {
  async scheduled(event, env, ctx) { ctx.waitUntil(controlla(env).catch(() => {})); },
  async fetch(req) {
    if (req.method === 'OPTIONS') return new Response(null, { headers: CORS });
    if (new URL(req.url).pathname === '/sentinella') return new Response(JSON.stringify(await controlla({}, true).catch(e => ({ errore: String(e) }))), { headers: { ...CORS, 'Content-Type': 'application/json' } });
    const sede = new URL(req.url).searchParams.get('sede') || 'LS Exchange';
    try {
      const [es, fx, vx, sd] = await Promise.all([
        J(yh('ES=F', '5m', '2d')).then(serie), J(yh('EURUSD=X', '5m', '1d')).then(serie), J(yh('^VIX', '5m', '1d')).then(serie), sedi()]);
      const vw = scegli(sd.trovate, sede);
      if (!vw || !es.now || !fx.now) throw new Error('dati non disponibili ' + sd.errori.join('; '));
      const tn = es.now[0];
      const out = {
        ok: true, t: Math.round(Date.now() / 1000), sede_richiesta: sede, errori: sd.errori,
        vwce: vw,
        es: { p: es.now[1], time: es.now[0], h1: before(es.pts, tn - 3600), h24: before(es.pts, tn - 86400), serie: es.pts.filter(p => p[0] >= tn - 21600) },
        fx: { p: fx.now[1], time: fx.now[0], serie: fx.pts.filter(p => p[0] >= fx.now[0] - 21600) },
        vix: vx.now ? { p: vx.now[1], time: vx.now[0], h1: before(vx.pts, vx.now[0] - 3600) } : null,
      };
      return new Response(JSON.stringify(out), { headers: { ...CORS, 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'public, max-age=5' } });
    } catch (e) {
      return new Response(JSON.stringify({ ok: false, errore: String(e.message || e) }), { status: 502, headers: { ...CORS, 'Content-Type': 'application/json' } });
    }
  },
};
