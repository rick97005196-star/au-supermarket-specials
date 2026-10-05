# Cute "sticker" category icons: soft pastel tile, dark-brown outline, dot eyes + blush.
import json, os
O = '#3d2b2b'          # outline / eyes
SW = 2.2
def face(cx, cy, gap=6, smile=True, blush=True, s=1.0):
    e = f'<circle cx="{cx-gap/2}" cy="{cy}" r="{1.5*s}" fill="{O}"/><circle cx="{cx+gap/2}" cy="{cy}" r="{1.5*s}" fill="{O}"/>'
    if smile:
        e += f'<path d="M{cx-1.6*s} {cy+2.3*s} q{1.6*s} {1.6*s} {3.2*s} 0" fill="none" stroke="{O}" stroke-width="{1.4*s}" stroke-linecap="round"/>'
    if blush:
        e += f'<ellipse cx="{cx-gap/2-2.6*s}" cy="{cy+2.6*s}" rx="{1.8*s}" ry="{1.1*s}" fill="#ff8fa3" opacity=".75"/><ellipse cx="{cx+gap/2+2.6*s}" cy="{cy+2.6*s}" rx="{1.8*s}" ry="{1.1*s}" fill="#ff8fa3" opacity=".75"/>'
    return e
def st(fill):   # filled shape with outline
    return f'fill="{fill}" stroke="{O}" stroke-width="{SW}" stroke-linejoin="round" stroke-linecap="round"'
def line(w=SW):
    return f'fill="none" stroke="{O}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"'

I = {}
# tile colours (pastel) are applied by CSS via a per-icon variable; here only the drawing
I['all'] = ('#fff1c9', f'''<path d="M13 19h22l-2 19a3 3 0 0 1-3 2.6H18a3 3 0 0 1-3-2.6z" {st('#ffb547')}/>
<path d="M19 19v-3a5 5 0 0 1 10 0v3" {line()}/>{face(24,28)}
<path d="M37 8l1.2 2.6 2.8.4-2 2 .5 2.8-2.5-1.3-2.5 1.3.5-2.8-2-2 2.8-.4z" fill="#ff6b8a" stroke="{O}" stroke-width="1.4" stroke-linejoin="round"/>''')
I['meat'] = ('#ffe1e1', f'''<path d="M30 30l7 7" stroke="{O}" stroke-width="7.5" stroke-linecap="round"/><path d="M30 30l7 7" stroke="#fff6e8" stroke-width="3.6" stroke-linecap="round"/>
<circle cx="38.5" cy="35" r="3" {st('#fff6e8')}/><circle cx="35" cy="38.5" r="3" {st('#fff6e8')}/>
<path d="M10 21c0-7 6-12 13-12 9 0 15 7 14 14-1 6-5 9-10 9-3 0-4 1-6 2-6 2-11-5-11-13z" {st('#ff8a65')}/>
<path d="M15 16q3-3 7-3" fill="none" stroke="#ffd0bf" stroke-width="2.4" stroke-linecap="round"/>{face(22,22)}''')
I['produce'] = ('#ddf5dc', f'''<path d="M21 28h6l1 12h-8z" {st('#9fd67a')}/>
<path d="M13 26a6 6 0 0 1 2-11 7 7 0 0 1 13-3 6 6 0 0 1 7 9 5 5 0 0 1-3 9H16a5 5 0 0 1-3-4z" {st('#5cbf63')}/>{face(24,20,5.5)}''')
I['sub_icecream'] = ('#ffe4f0', f'''<path d="M16 24h16l-8 18z" {st('#f5b86a')}/><path d="M19 28l9 6M21 34l5-3" {line(1.4)}/>
<path d="M14 24a10 10 0 0 1 20 0z" {st('#ff9ec4')}/><circle cx="24" cy="10.5" r="2.6" {st('#ff5a6e')}/>{face(24,19,5.5)}''')
I['sub_chocolate'] = ('#f3e3d6', f'''<path d="M13 11h18l4 4v22H13z" {st('#8a5a3c')}/><path d="M13 23h22M24 11v26M13 30h22" fill="none" stroke="#5c3a26" stroke-width="1.6"/>
<path d="M31 11l4 4h-4z" {st('#f2d3b8')}/>{face(18.5,17,4.5,smile=True,blush=True,s=.85)}''')
I['sub_chips'] = ('#fff2c2', f'''<path d="M14 9h20l-2 5 3 22-3 4H16l-3-4 3-22z" {st('#ffd23f')}/><path d="M16 14h16M16 36h16" {line(1.6)}/>
{face(24,24)}<path d="M33 10l4-3M35 13l4 0" {line(1.6)}/>''')
I['sub_coffee'] = ('#efe2d6', f'''<path d="M12 20h20v11a8 8 0 0 1-8 8h-4a8 8 0 0 1-8-8z" {st('#ffffff')}/>
<path d="M32 23h2a4 4 0 0 1 0 8h-2" {line()}/><path d="M12 20h20v3H12z" fill="#a0673f" stroke="{O}" stroke-width="{SW}" stroke-linejoin="round"/>
<path d="M18 15c-2-2 2-3 0-6M24 15c-2-2 2-3 0-6" {line(1.6)}/>{face(22,29)}''')
I['dairy_eggs'] = ('#e3f0ff', f'''<path d="M16 16l4-6h8l4 6v24H16z" {st('#ffffff')}/><path d="M16 16h16" {line()}/>
<path d="M16 22h16v9H16z" fill="#7fb6ff" stroke="{O}" stroke-width="1.6"/><path d="M20 10h8" {line()}/>{face(24,34,5,s=.85)}''')
I['bakery'] = ('#fdebd3', f'''<path d="M11 21a7 7 0 0 1 7-9h12a7 7 0 0 1 7 9v17H11z" {st('#e9a55b')}/>
<path d="M15 22a3 3 0 0 1 3-4h12a3 3 0 0 1 3 4v13H15z" fill="#ffe9c4" stroke="none"/>{face(24,27)}''')
I['frozen'] = ('#dff3ff', f'''<rect x="11" y="13" width="26" height="24" rx="6" {st('#bfe6ff')}/><path d="M15 17l5 0" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/>
{face(24,26)}<path d="M38 8v6M35 11h6M36 9l4 4M40 9l-4 4" {line(1.3)}/>''')
I['seafood'] = ('#dcf2f7', f'''<path d="M9 24c5-8 15-10 23-3l7-6v18l-7-6c-8 7-18 5-23-3z" {st('#5fb8d6')}/>
<circle cx="17" cy="22" r="1.6" fill="{O}"/><path d="M17 27q2 1.5 4 0" {line(1.4)}/><ellipse cx="14" cy="26" rx="1.7" ry="1" fill="#ff8fa3" opacity=".75"/><path d="M26 18q3 6 0 12" {line(1.4)}/>''')
I['snacks'] = ('#f6e6d4', f'''<circle cx="24" cy="25" r="14" {st('#e2a55f')}/>
<circle cx="17" cy="18" r="1.8" fill="#6b3f22"/><circle cx="32" cy="20" r="1.8" fill="#6b3f22"/><circle cx="31" cy="32" r="1.8" fill="#6b3f22"/><circle cx="16" cy="31" r="1.6" fill="#6b3f22"/>{face(24,25)}''')
I['drinks'] = ('#e4f7ef', f'''<path d="M15 15h18v25H15z" {st('#7fd8b0')}/><path d="M15 21h18" {line(1.6)}/><path d="M28 15l3-7h4" {line()}/>
{face(24,30)}''')
I['sub_noodles'] = ('#fff0d9', f'''<path d="M9 24h30a15 13 0 0 1-30 0z" {st('#ff8a5c')}/><path d="M14 24c2-6 4-6 6 0s4 6 6 0 4-6 6 0" fill="none" stroke="#ffe08a" stroke-width="2.4" stroke-linecap="round"/>
<path d="M30 6l-6 16M36 8l-8 15" {line(1.8)}/>{face(24,31)}''')
I['sub_quickmeals'] = ('#ffecd2', f'''<rect x="6" y="13" width="36" height="24" rx="5" {st('#ffffff')}/><rect x="10" y="17" width="21" height="16" rx="3" fill="#ffd28a" stroke="{O}" stroke-width="1.8"/>
<circle cx="36" cy="20" r="2.4" {st('#ff8a65')}/><path d="M34 27h4M34 31h4" {line(1.8)}/><path d="M17 11c-1.5-2 1.5-3 0-5M23 11c-1.5-2 1.5-3 0-5" {line(1.5)}/>{face(20.5,24,5,s=.85)}''')
I['sub_soda'] = ('#e0f0ff', f'''<path d="M16 12h16l1 4v20l-1 4H16l-1-4V16z" {st('#ff5d5d')}/><path d="M16 12h16M15 16h18M15 36h18" {line(1.6)}/>
<path d="M18 21h12v9H18z" fill="#fff" stroke="none"/>{face(24,25,5,s=.85)}<circle cx="37" cy="10" r="2" {line(1.3)}/><circle cx="40" cy="16" r="1.3" {line(1.2)}/>''')
I['pantry'] = ('#fdf3d9', f'''<path d="M9 24h30a15 13 0 0 1-30 0z" {st('#ffffff')}/>
<path d="M11 24c0-6 6-10 13-10s13 4 13 10z" fill="#fffaf0" stroke="{O}" stroke-width="{SW}" stroke-linejoin="round"/>
<path d="M17 19h1M22 17h1M27 18h1M31 21h1M20 21h1" {line(1.6)}/><path d="M9 24h30" {line()}/>{face(24,31)}''')
I['sub_laundry'] = ('#e7e9ff', f'''<path d="M15 16h18v20a4 4 0 0 1-4 4H19a4 4 0 0 1-4-4z" {st('#8f9bff')}/><path d="M20 10h8v6h-8z" {st('#ffd166')}/>
<path d="M19 22h10v8H19z" fill="#fff" stroke="none"/>{face(24,26,4.6,s=.8)}<circle cx="37" cy="12" r="3" {st('#ffffff')}/><circle cx="40" cy="20" r="2" {st('#ffffff')}/>''')
I['sub_vitamins'] = ('#ffe9e3', f'''<g transform="rotate(-35 24 24)"><rect x="10" y="17" width="28" height="14" rx="7" {st('#ffffff')}/>
<path d="M24 17h7a7 7 0 0 1 0 14h-7z" fill="#ff7b6b" stroke="{O}" stroke-width="{SW}" stroke-linejoin="round"/></g>{face(19,26,5,s=.85)}''')
I['health_vitamins'] = ('#fde6f5', f'''<path d="M15 19h18v18a4 4 0 0 1-4 4H19a4 4 0 0 1-4-4z" {st('#f6a6d6')}/><path d="M20 14h8v5h-8z" {st('#ffffff')}/>
<path d="M24 14V9h7" {line()}/>{face(24,29)}''')
I['household'] = ('#eef0f4', f'''<rect x="11" y="13" width="20" height="26" rx="4" {st('#ffffff')}/><ellipse cx="31" cy="26" rx="6" ry="13" {st('#ffffff')}/>
<ellipse cx="31" cy="26" rx="2.4" ry="5" fill="#d9dde6" stroke="{O}" stroke-width="1.6"/>{face(20,25,5,s=.9)}''')
I['liquor'] = ('#fff3cf', f'''<path d="M13 17h18v19a4 4 0 0 1-4 4h-10a4 4 0 0 1-4-4z" {st('#ffc23d')}/><path d="M31 21h3a4 4 0 0 1 4 4v3a4 4 0 0 1-4 4h-3" {line()}/>
<path d="M12 17a4 4 0 0 1 4-6 5 5 0 0 1 8-1 5 5 0 0 1 8 2 4 4 0 0 1 0 6z" {st('#ffffff')}/>{face(22,28)}''')
I['pet'] = ('#f1e8dd', f'''<path d="M11 18l3-9 7 6h6l7-6 3 9c2 4 2 9-1 13-3 5-8 7-13 7s-10-2-13-7c-3-4-3-9 1-13z" {st('#ffb36b')}/>
<path d="M15 12l1 5M33 12l-1 5" {line(1.4)}/>{face(24,26,8)}<path d="M8 27h5M8 31h5M35 27h5M35 31h5" {line(1.2)}/>''')

out = {}
for k, (bg, body) in I.items():
    out[k] = f'<svg viewBox="0 0 48 48" aria-hidden="true"><rect x="1" y="1" width="46" height="46" rx="15" fill="{bg}"/>{body}</svg>'.replace('\n','')
js = "// Hand-drawn category icons (cute sticker style). Generated: one SVG per category.\nconst CATEGORY_ICONS = " + json.dumps(out, ensure_ascii=False, indent=0) + ";\n"
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'category-icons.js'),'w').write(js)
labels = {'all':'全部特價','meat':'肉品','produce':'蔬果','sub_icecream':'冰淇淋','sub_chocolate':'巧克力','sub_chips':'洋芋片','sub_coffee':'咖啡','dairy_eggs':'乳品蛋類','bakery':'麵包甜點','frozen':'冷凍食品','seafood':'海鮮','snacks':'零食餅乾','drinks':'飲料沖泡','sub_noodles':'泡麵','sub_quickmeals':'微波即食','sub_soda':'汽水','pantry':'米油調味','sub_laundry':'洗衣精','sub_vitamins':'維他命','health_vitamins':'個人清潔保養','household':'居家日用','liquor':'酒類','pet':'寵物用品'}
html = '<html><body style="font-family:sans-serif;background:#f5f5f7;padding:20px"><div style="display:grid;grid-template-columns:repeat(6,120px);gap:16px">' + ''.join(f'<div style="text-align:center"><div style="width:96px;height:96px;margin:auto">{out[k]}</div><div style="display:flex;align-items:center;gap:6px;justify-content:center;margin-top:8px;background:#fff;border-radius:99px;padding:4px 10px 4px 4px;font-size:13px"><span style="width:26px;height:26px;display:inline-block">{out[k]}</span>{labels[k]}</div></div>' for k in out) + '</div></body></html>'
open(os.devnull,'w').write(html)
print(len(out))
