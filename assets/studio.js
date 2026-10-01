(() => {
  const source = document.getElementById('sites');
  const target = document.getElementById('heroSites');
  function sync() {
    target.replaceChildren(...[...source.querySelectorAll('.site')].map((site, index) => {
      const row = document.createElement('div'); row.className = 'route-row';
      const name = document.createElement('span'); name.textContent = site.querySelector('.site-top b').textContent;
      const detail = document.createElement('small'); detail.textContent = index === 0 ? 'Lowest modeled cost · batch job destination' : site.querySelector('.site-meta span').textContent;
      name.append(detail); const cost = document.createElement('b'); cost.textContent = site.querySelector('.site-cost').textContent;
      row.append(name, cost); return row;
    }));
    document.querySelector('.routing-title>span:last-child').textContent = 'Week ' + document.querySelector('#wVal').textContent;
    document.querySelector('.job-ticket').replaceChildren(...['cVal','uVal','hVal'].map(id => { const item=document.createElement('span'); item.textContent=document.getElementById(id).textContent;return item; }));
  }
  new MutationObserver(sync).observe(source, {childList:true});
  if(source.children.length) sync();
})();
