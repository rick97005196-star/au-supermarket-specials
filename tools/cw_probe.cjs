// Probe only: what does the Chemist Warehouse catalogue viewer load?
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36' });
  fs.mkdirSync('probe', { recursive: true });
  let n = 0;
  p.on('response', async r => {
    const u = r.url(); const ct = r.headers()['content-type'] || '';
    console.log(r.status(), ct.split(';')[0], u.slice(0, 300));
    if (/json|text\/plain|xml/.test(ct) && !/google|facebook|doubleclick/.test(u)) {
      try { const t = await r.text(); fs.writeFileSync(`probe/r${++n}.txt`, u + '\n' + t.slice(0, 400000)); } catch (e) {}
    }
  });
  await p.goto('https://nexuspublications.com.au/a10/publications/home/3476?toolbar=no&portrait=false', { waitUntil: 'networkidle', timeout: 90000 }).catch(e => console.log('goto', e.message));
  await p.waitForTimeout(8000);
  fs.writeFileSync('probe/page.html', await p.content());
  // click into first publication if listing
  const links = await p.$$eval('a', as => as.map(a => a.href)).catch(() => []);
  console.log('LINKS', JSON.stringify(links.slice(0, 50)));
  await p.mouse.click(400, 300).catch(() => {});
  await p.waitForTimeout(8000);
  console.log('URL', p.url());
  fs.writeFileSync('probe/page2.html', await p.content());
  await p.goto('https://www.chemistwarehouse.com.au/catalogue', { waitUntil: 'networkidle', timeout: 90000 }).catch(e => console.log('goto2', e.message));
  await p.waitForTimeout(5000);
  await b.close();
})();
