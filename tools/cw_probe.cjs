// Probe only: Chemist Warehouse catalogue data (nexuspublications)
const H = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36', 'Referer': 'https://app.nexuspublications.com.au/', 'Origin': 'https://app.nexuspublications.com.au' };
async function j(u) { const r = await fetch(u, { headers: H }); const t = await r.text(); console.log('\n=====', r.status, u, 'len', t.length); return t; }
(async () => {
  const cats = await j('https://node.nexuspublications.com.au/client/3476/catalogues/json?_format=json');
  console.log(cats.slice(0, 6000));
  console.log((await j('https://node.nexuspublications.com.au/clientdomain/3476/catalogues/json?_format=json')).slice(0, 3000));
  let ids = [...new Set([...cats.matchAll(/"(?:catalogue_id|id|nid)"\s*:\s*"?(\d{6,})/g)].map(m => m[1]))];
  console.log('IDS', ids);
  for (const id of ids.slice(0, 6)) {
    const t = await j(`https://node.nexuspublications.com.au/get-catalogue-advance_search/${id}/json`);
    console.log(t.slice(0, 15000));
  }
  const d = await j('https://node.nexuspublications.com.au/view/catalogue/details/name/the-house-of-wellness-november-2026/json?_format=json');
  console.log(d.slice(0, 4000));
  console.log((await j('https://node.nexuspublications.com.au/client/3476/category/data')).slice(0, 3000));
})();
