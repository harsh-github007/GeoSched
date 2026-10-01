import { DCS, parseCSV, week, jobCost } from './geo.js';

const $ = id => document.getElementById(id);
const CORES = [8, 16, 32, 64, 128, 256, 512, 1024];
const COLOR = { Iowa: '#ff5c5c', Oregon: '#5878a0', Singapore: '#b17a28', Chile: '#39826f', Finland: '#3c7e95' };
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const weekLabel = w => { const d = new Date(Date.UTC(2013, 0, 1 + 7 * w)); return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`; };
const money = v => v >= 100 ? `$${v.toFixed(0)}` : v >= 1 ? `$${v.toFixed(2)}` : `${(v * 100).toFixed(1)}¢`;

Chart.defaults.color = '#626d70';
Chart.defaults.borderColor = '#dce1df';
Chart.defaults.font.family = 'Inter, system-ui, sans-serif';

const [temp, price] = await Promise.all(['data/weekly_temp_f.csv', 'data/weekly_price_usd_mwh.csv']
  .map(p => fetch(p).then(r => r.text()).then(parseCSV)));

// ---------- 1. Playground ----------
function drawSites() {
  const w = +$('w').value, cores = CORES[+$('c').value], util = +$('u').value / 100, hours = +$('h').value;
  $('wVal').textContent = `from ${weekLabel(w)}`; $('cVal').textContent = `${cores} cores`; $('uVal').textContent = `${Math.round(util * 100)}%`;
  $('hVal').textContent = `${hours} h`;
  const rows = jobCost(week(temp, price, w), cores, util, hours).sort((a, b) => a.cost - b.cost);
  const worst = rows[rows.length - 1].cost;
  const available = new Set([...document.querySelectorAll('.siteAvailable:checked')].map(x => x.value));
  const klass = +$('jobClass').value, origin = $('origin').value;
  const eligible = rows.filter(r => available.has(r.dc));
  const destination = klass >= 2 ? (available.has(origin) ? origin : null) : eligible[0]?.dc;
  $('sites').innerHTML = rows.map(r => `
    <div class="site${r.dc === destination ? ' best' : ''}${available.has(r.dc) ? '' : ' unavailable'}">
      <div class="site-top"><span class="dot" style="background:${COLOR[r.dc]}"></span><b>${r.dc}</b>${r.dc === destination ? '<span class="tag">'+(klass >= 2 ? 'Stays at arrival site' : 'Selected destination')+'</span>' : !available.has(r.dc) ? '<span class="tag">No shared capacity</span>' : ''}</div>
      <div class="site-cost">${money(r.cost)}</div>
      <div class="bar"><i style="width:${(100 * r.cost / worst).toFixed(1)}%;background:${COLOR[r.dc]}"></i></div>
      <div class="site-meta"><span>${r.temp.toFixed(0)}°F · ${r.mode}</span><span>$${r.price.toFixed(0)}/MWh + ${(100 * r.overhead).toFixed(0)}% cooling</span></div>
    </div>`).join('');
  const chosen = rows.find(r => r.dc === destination);
  $('siteNote').textContent = destination
    ? `${klass >= 2 ? 'Latency-sensitive work stays in' : 'This batch job selects'} ${destination}. Its modeled incremental cost is ${money(chosen.cost)}. ${klass >= 2 ? 'The cheapest remote site does not override the class policy.' : 'Unavailable sites are excluded, even if their price is lower.'} This illustration excludes site-wide idle energy and task fragmentation; the Python engine includes both.`
    : `${klass >= 2 ? origin + ' has no shared capacity; latency-sensitive work queues locally.' : 'No site has shared capacity; the new simulator falls back to the local queue.'} A lower price does not justify sending a job to a site that cannot host it.`;
}
['w', 'c', 'u', 'h','jobClass','origin'].forEach(id => $(id).addEventListener('input', drawSites));
document.querySelectorAll('.siteAvailable').forEach(x => x.addEventListener('change',drawSites));
drawSites();

// ---------- 2. The year ----------
const weeks = [...Array(53).keys()];
const yearRows = weeks.map(w => week(temp, price, w));
let yearChart;
function drawYear(m) {
  const data = DCS.map(dc => ({
    label: dc, data: yearRows.map(rs => rs.find(r => r.dc === dc)[m]), borderColor: COLOR[dc], backgroundColor: COLOR[dc],
    pointRadius: 0, borderWidth: 2, tension: 0.25,
  }));
  const unit = m === 'temp' ? '°F' : '$/MWh';
  if (yearChart) yearChart.destroy();
  yearChart = new Chart($('yearChart'), {
    type: 'line', data: { labels: weeks.map(weekLabel), datasets: data },
    options: {
      maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      scales: { x: { ticks: { maxTicksLimit: 12 }, grid: { display: false } }, y: { title: { display: true, text: unit } } },
      plugins: { legend: { labels: { boxWidth: 12, boxHeight: 2 } }, tooltip: { callbacks: { label: c => `${c.dataset.label}: ${c.parsed.y.toFixed(1)} ${unit}` } } },
    },
  });
  const cheapest = yearRows.map(rs => rs.reduce((a, b) => (b.effective < a.effective ? b : a)).dc);
  const count = DCS.map(dc => [dc, cheapest.filter(c => c === dc).length]).filter(([, n]) => n).sort((a, b) => b[1] - a[1]);
  $('yearNote').innerHTML = {
    effective: `Cheapest site, week by week: ${count.map(([dc, n]) => `<b>${dc}</b> ${n} weeks`).join(', ')}. Singapore is the most expensive every week: the highest prices, and too hot for outside air all year.`,
    price: 'Singapore pays the most for power all year. Chile\'s line is flat because only monthly prices were available. Iowa uses the 2013 average price of MISO\'s West region (see the repository README).',
    temp: 'Below 65°F a site can cool with outside air. Singapore never gets there; Iowa and Oregon lose it in high summer.',
  }[m];
}
document.querySelectorAll('#yearChips .chip').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('#yearChips .chip').forEach(x => x.setAttribute('aria-pressed', x === b));
  drawYear(b.dataset.m);
}));
drawYear('effective');

// ---------- Saved independent simulator demonstration ----------
try {
 const response=await fetch('results/demo.json');
 if(!response.ok) throw new Error('Experiment data unavailable');
 const demo=await response.json();
 const controls=$('demoMonths');
 const render=(index)=>{
  const exp=demo.experiments[index];
  controls.querySelectorAll('button').forEach((b,i)=>b.setAttribute('aria-pressed',String(i===index)));
  $('demoStatus').textContent=`${exp.start.slice(0,10)} · ${demo.source} · ${demo.capacity}`;
  const local=exp.runs.local.sites, geo=exp.runs.geosched.sites;
  $('demoRows').innerHTML=DCS.map(n=>`<tr><th>${n}</th><td>$${local[n].cost_usd.toFixed(3)}</td><td>$${geo[n].cost_usd.toFixed(3)}</td><td>${(local[n].energy_j/1e6).toFixed(2)} MJ</td><td>${(geo[n].energy_j/1e6).toFixed(2)} MJ</td><td>${geo[n].completed}</td></tr>`).join('');
  const status=(run)=>{
   const sites=Object.values(run.sites);
   return ['completed','queued','running','rejected'].map(k=>`${sites.reduce((a,s)=>a+s[k],0)} ${k}`).join(' · ');
  };
  $('demoAccounting').textContent=`Local: ${status(exp.runs.local)}. GeoSched: ${status(exp.runs.geosched)}. Both received ${exp.runs.local.arrived_jobs} jobs in the same ${exp.runs.local.horizon_s}-second window. All site energy includes idle power.`;
 };
 demo.experiments.forEach((exp,i)=>{const button=document.createElement('button');button.className='chip';button.textContent=new Date(exp.start).toLocaleString('en-US',{month:'short',timeZone:'UTC'});button.addEventListener('click',()=>render(i));controls.append(button);});
 render(0);
} catch(error) { $('demoStatus').textContent='The saved demonstration could not load. Run python3 -m simulator.run --all-months to generate it.'; }
