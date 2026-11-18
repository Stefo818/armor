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

export default {
  async fetch(req) {
    if (req.method === 'OPTIONS') return new Response(null, { headers: CORS });
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
