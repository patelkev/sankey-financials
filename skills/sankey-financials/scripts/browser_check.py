#!/usr/bin/env python3
"""Load a built widget in headless Chrome: measure real label overlaps in every view,
click every control, hover every node, and save one screenshot per view.
Usage: python3 browser_check.py widget.html out_prefix   (exit 1 on any problem)"""
import asyncio, sys, os, json, re, subprocess, tempfile
from playwright.async_api import async_playwright
CHROME = os.environ.get('CHROME')
w = open(sys.argv[1]).read(); out = sys.argv[2]
html = ("<html><head><style>:root{--surface-1:#fcfcfb;--surface-2:#fff;--text-primary:#0b0b0b;--text-secondary:#52514e;"
        "--text-muted:#898781;--text-success:#0c7a0c;--text-danger:#c53030;--text-accent:#2a78d6;--bg-neutral:#f0efec;"
        "--border-strong:#ccc;--border-stronger:#999;--radius:8px}body{margin:0;background:#fcfcfb;"
        "font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;width:760px}</style></head><body>"
        "<script>window.prompts=[];window.sendPrompt=t=>prompts.push(t)</script>" + w + "</body></html>")
MEASURE = """()=>{const sk=document.getElementById('sk');const vb=sk.viewBox.baseVal;
 const B=[...sk.querySelectorAll('g.lb')].map(g=>{const b=g.getBBox();return{id:g.dataset.n,x0:b.x,x1:b.x+b.width,y0:b.y,y1:b.y+b.height}});
 const R=[...sk.querySelectorAll('rect.nd')].map(r=>({id:r.dataset.n,x0:+r.getAttribute('x'),x1:+r.getAttribute('x')+10,y0:+r.getAttribute('y'),y1:+r.getAttribute('y')+ +r.getAttribute('height')}));
 const ov=(a,b)=>a.x0<b.x1-1&&b.x0<a.x1-1&&a.y0<b.y1-1&&b.y0<a.y1-1;const bad=[];
 B.forEach((a,i)=>{if(a.x0<0||a.x1>vb.width||a.y1>vb.height)bad.push('off-canvas '+a.id);
   B.slice(i+1).forEach(b=>{if(ov(a,b))bad.push('labels '+a.id+'/'+b.id)});
   R.forEach(r=>{if(r.id!==a.id&&ov(a,r))bad.push('label '+a.id+' covers '+r.id)})});
 return {bad,nodes:R.map(r=>r.id),h:vb.height}}"""
def data_checks(widget):
    """Run test.js on the CFG embedded in the page, so a chart with broken numbers can't pass here."""
    m = re.search(r'const CFG=(.*?);\n', widget)
    if not m: return ['no chart data (const CFG=...) found in the page']
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        f.write(m.group(1)); tmp = f.name
    r = subprocess.run(['node', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test.js'), tmp, '-q'],
                       capture_output=True, text=True)
    os.unlink(tmp)
    return [] if r.returncode == 0 else ['data/layout checks failed: ' + '; '.join(
        l for l in (r.stdout + r.stderr).splitlines() if l.startswith('ERROR') or 'Error' in l)[:600]]
async def main():
    probs = data_checks(w)
    async with async_playwright() as p:
        b = await (p.chromium.launch(executable_path=CHROME) if CHROME else p.chromium.launch())
        pg = await b.new_page(viewport={'width': 760, 'height': 1000}, device_scale_factor=2)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('dialog', lambda d: (errs.append('page opened a dialog: ' + d.message), asyncio.ensure_future(d.dismiss())))
        await pg.set_content(html)
        tabs = await pg.locator('#views button').all()
        visible_tabs = await pg.locator('#views').is_visible()
        sw = await pg.locator('#yoy').is_visible()
        for ti in range(max(1, len(tabs) if visible_tabs else 1)):
            if visible_tabs and tabs: await tabs[ti].click()
            name = (await tabs[ti].inner_text()) if visible_tabs and tabs else 'main'
            for state in ([True, False] if sw else [None]):
                if sw:
                    cur = await pg.get_attribute('#yoy', 'aria-checked') == 'true'
                    if cur != state: await pg.click('#yoy')
                m = await pg.evaluate(MEASURE)
                if m['bad']: probs.append(f"{name}/{'cmp' if state else 'no-cmp'}: " + '; '.join(sorted(set(m['bad']))))
                if state is not False:
                    await pg.locator('#sk').screenshot(path=f"{out}_{name.lower().replace(' ','_')}.png")
                    for nid in m['nodes']:
                        await pg.locator(f'rect.nd[data-n="{nid}"]').hover(force=True)
                        t = await pg.locator('#tip').inner_text()
                        if not t.strip(): probs.append(f'{name}: empty tooltip on {nid}')
            if sw and await pg.get_attribute('#yoy', 'aria-checked') != 'true': await pg.click('#yoy')
        nodes = (await pg.evaluate(MEASURE))['nodes']
        if not nodes: probs.append('no nodes rendered')
        else: await pg.locator(f'rect.nd[data-n="{nodes[0]}"]').click(force=True)
        pr = await pg.evaluate('prompts')
        if nodes and not pr: probs.append('click-to-ask sent nothing')
        if any(x in pr[0] for x in ('undefined', 'NaN')) if pr else False: probs.append('bad prompt: ' + pr[0])
        if errs: probs.append('page errors: ' + '; '.join(errs))
        await b.close()
    name = os.path.basename(sys.argv[1])
    print(f"{name}: browser {'OK' if not probs else 'PROBLEMS'}" + ('' if not probs else '\n  ' + '\n  '.join(probs)))
    sys.exit(1 if probs else 0)
asyncio.run(main())
