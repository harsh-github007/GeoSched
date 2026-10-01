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
  $('sites').innerHTML = rows.map((r, i) => `
    <div class="site${i === 0 ? ' best' : ''}">
      <div class="site-top"><span class="dot" style="background:${COLOR[r.dc]}"></span><b>${r.dc}</b>${i === 0 ? '<span class="tag">GeoSched sends it here</span>' : ''}</div>
      <div class="site-cost">${money(r.cost)}</div>
      <div class="bar"><i style="width:${(100 * r.cost / worst).toFixed(1)}%;background:${COLOR[r.dc]}"></i></div>
      <div class="site-meta"><span>${r.temp.toFixed(0)}°F · ${r.mode}</span><span>$${r.price.toFixed(0)}/MWh + ${(100 * r.overhead).toFixed(0)}% cooling</span></div>
    </div>`).join('');
  const best = rows[0], local = rows.find(r => r.dc === 'Singapore');
  $('siteNote').innerHTML = `In the week from ${weekLabel(w)}, the job costs <b>${money(best.cost)}</b> in ${best.dc} and <b>${money(local.cost)}</b> in Singapore, ${(local.cost / best.cost).toFixed(1)}× as much. `
    + `If it is a batch job (classes 0–1), GeoSched runs it in ${best.dc}. If it is latency-sensitive (classes 2–3), it stays where it arrived.`;
}
['w', 'c', 'u', 'h'].forEach(id => $(id).addEventListener('input', drawSites));
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
