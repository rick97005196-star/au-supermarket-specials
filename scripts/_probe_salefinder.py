import json, re, requests, time
from bs4 import BeautifulSoup
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
a=json.load(open('static/data/specials.json'))
sf=[i for i in a if 'salefinder' in i['product_url']]
big=sorted(sf,key=lambda i:-i['price'])[:6]+[i for i in sf if i['price']<10][:3]
for i in big:
    r=requests.get(i['product_url'],headers=H,timeout=20); time.sleep(3)
    soup=BeautifulSoup(r.text,'html.parser')
    main=soup.select_one('#sf-content, .sf-item-detail, main') or soup
    t=re.sub(r'\s+',' ',main.get_text(' '))
    print('=====',r.status_code,i['store'],i['title'][:50],i['price'])
    for kw in ['nline','Market','store','available','Available','Page']:
        for m in re.finditer(kw,t):
            print('   ',kw,':',t[max(0,m.start()-120):m.start()+120]); break
    # catalogue page number
    print('   links:',[x.get('href') for x in soup.select('a[href*="catalogue2"]')][:3])
