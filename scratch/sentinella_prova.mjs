// Prova della sentinella sui dati reali di oggi: a che ora sarebbe partito l'avviso? Uso: node scratch/sentinella_prova.mjs /tmp/wt/w.mjs
const m = await import(process.argv[2]);
const yh = (s, i, r) => `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(s)}?interval=${i}&range=${r}`;
const get = async (s, i, r) => { const j = (await (await fetch(yh(s, i, r), { headers: { 'User-Agent': 'Mozilla/5.0' } })).json()).chart.result[0]; const c = j.indicators.quote[0].close; return j.timestamp.map((t, k) => [t, c[k]]).filter(x => x[1] != null); };
const es = await get('ES=F', '5m', '1d'), vx = await get('^VIX', '5m', '1d'), gd = await get('^GSPC', '1d', '1y'), vd = await get('^VIX', '1d', '1mo');
const RITARDO = 9 * 60;   // i prezzi gratuiti arrivano con circa 9 minuti di ritardo
const hh = t => new Date(t * 1000).toISOString().slice(11, 16);
let visti = {};
for (let t = es[0][0] + 3600; t <= es[es.length - 1][0] + RITARDO; t += 60) {
  const e = es.filter(x => x[0] <= t - RITARDO), v = vx.filter(x => x[0] <= t - RITARDO);
  for (const r of m.rilevaRapido(e, v)) if (!visti[r.tipo]) { visti[r.tipo] = t; console.log('avviso', r.tipo, 'alle', hh(t), 'UTC (', hh(t + 3600), 'ora italiana) valore', r.valore.toFixed(4)); }
}
const ch = gd.map(x => x[1]);
for (const [nome, cut] of [['oggi', 1], ['ieri', 2], ['2 giorni fa', 3]]) {
  const f = m.rilevaFragile(ch.slice(0, ch.length - cut), ch[ch.length - cut], vd.map(x => x[1]).slice(0, vd.length - cut), vd[vd.length - cut][1]);
  console.log('terreno fragile', nome, f ? JSON.stringify(f) : 'no');
}
console.log('ES di oggi: ultimo', hh(es[es.length - 1][0]), 'UTC');
