// Replay del 20 novembre: a che ora sarebbero scattate le regole (prezzi con 9 minuti di ritardo)? node scratch/sentinella_gradini_prova.mjs /tmp/wt/w3.mjs
const m = await import(process.argv[2]);
const get = async (s) => { const j = (await (await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(s)}?interval=5m&range=5d`, { headers: { 'User-Agent': 'Mozilla/5.0' } })).json()).chart.result[0]; const c = j.indicators.quote[0].close; return j.timestamp.map((t, k) => [t, c[k]]).filter(x => x[1] != null); };
const es = await get('ES=F'), vx = await get('^VIX'); const hh = t => new Date(t * 1000).toISOString().slice(11, 16);
const day = Date.parse('2026-11-20T00:00:00Z') / 1000, RIT = 9 * 60, visti = {};
for (let t = day; t <= day + 86400; t += 60) {
  const e = es.filter(x => x[0] <= t - RIT), v = vx.filter(x => x[0] <= t - RIT);
  for (const r of [...m.rilevaRapido(e, v), ...m.rilevaGradini(e, v)]) if (!visti[r.tipo]) { visti[r.tipo] = 1; console.log('20 nov', r.tipo, 'avviso alle', hh(t), 'UTC =', hh(t + 3600), 'ora italiana, valore', r.valore.toFixed(4)); }
}
