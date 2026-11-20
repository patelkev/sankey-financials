#!/usr/bin/env python3
"""Assemble the chart from a CFG.

  python3 build.py cfg.json out.html               -> widget fragment (inline widget fragment for chat UIs such as claude.ai)
  python3 build.py cfg.json out.html --standalone  -> full web page to open in a browser (CLI or any browser)
"""
import html, json, os, sys
D = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(sys.argv[1]))
summary = html.escape(f"Interactive Sankey diagram: {cfg['title']}, {cfg['sub']}.")
head = open(os.path.join(D, 'shell_head.html')).read().replace('SUMMARY', summary)
# '</' inside a JSON string would close the <script> tag early; '<\/' is the same string in JS.
data = json.dumps(cfg, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')
frag = (head + 'const CFG=' + data + ';\n'
        + open(os.path.join(D, 'engine.js')).read() + open(os.path.join(D, 'interact.js')).read() + '</script>')
if '--standalone' in sys.argv:
    page = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>%s</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--surface-1:#fcfcfb;--surface-2:#fff;--text-primary:#0b0b0b;--text-secondary:#52514e;--text-muted:#898781;
--text-success:#0c7a0c;--text-danger:#c53030;--text-accent:#2a78d6;--bg-neutral:#f0efec;--border-strong:rgba(11,11,11,.18);
--border-stronger:rgba(11,11,11,.4);--radius:8px}
@media (prefers-color-scheme:dark){:root{--surface-1:#151515;--surface-2:#202020;--text-primary:#f0efec;--text-secondary:#c3c2b7;
--text-muted:#898781;--text-success:#3fb950;--text-danger:#f47067;--text-accent:#3987e5;--bg-neutral:#262624;
--border-strong:rgba(255,255,255,.18);--border-stronger:rgba(255,255,255,.4)}}
body{margin:0;background:var(--surface-1);color:var(--text-primary);font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue',Arial,sans-serif}
main{max-width:900px;margin:24px auto;padding:0 16px}
button{font:inherit;cursor:pointer}
#copied{position:fixed;bottom:16px;left:50%%;transform:translateX(-50%%);background:var(--surface-2);border:1px solid var(--border-strong);
border-radius:8px;padding:8px 14px;font-size:13px;opacity:0;transition:opacity .2s}
</style></head><body><main>
<script>window.sendPrompt=t=>{const c=document.getElementById('copied'),show=m=>{c.textContent=m;c.style.opacity=1;setTimeout(()=>c.style.opacity=0,3500)};
const fail=()=>show('Could not copy automatically. Your question: '+t);
navigator.clipboard?navigator.clipboard.writeText(t).then(()=>show('Question copied. Paste it into your AI assistant to ask about this line.'),fail):fail()}</script>
%s
<p style="font-size:12px;color:var(--text-muted)">Source: %s</p></main>
<div id="copied" role="status" aria-live="polite"></div></body></html>""" % (
        html.escape(cfg['title']), frag, html.escape(cfg.get('source', 'company filings')))
    open(sys.argv[2], 'w').write(page)
else:
    open(sys.argv[2], 'w').write(frag)
print(f'{sys.argv[2]}: {os.path.getsize(sys.argv[2]):,} bytes')
