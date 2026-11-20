#!/usr/bin/env python3
"""Run make -> test -> build --standalone -> browser_check for each spec; print one line each.
Usage: run.py SKILLDIR OUTDIR spec.json...  (set NOBROWSER=1 to skip browser)"""
import subprocess, sys, os, re
skill, out, specs = sys.argv[1], sys.argv[2], sys.argv[3:]
os.makedirs(out, exist_ok=True)
S = os.path.join(skill, 'scripts')
def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()
for s in specs:
    n = os.path.basename(s)[:-5]; cfg = f'{out}/{n}.cfg.json'; html = f'{out}/{n}.html'
    rc, o = run(['python3', f'{S}/make.py', s, cfg])
    if rc:
        last = o.splitlines()[-1] if o else ''
        kind = 'REFUSED' if 'SPEC ERROR' in o else 'CRASH'
        print(f'{n:34} make:{kind}: {last[:160]}'); continue
    rc, o = run(['node', f'{S}/test.js', cfg, '-q'])
    errs = [l for l in o.splitlines() if l.startswith('ERROR')]
    warns = [l for l in o.splitlines() if l.startswith('WARN')]
    tstat = 'ok' if rc == 0 else f'FAIL({len(errs)})'
    if rc and not errs: tstat = 'CRASH:' + o.splitlines()[-1][:100] if o else 'CRASH'
    run(['python3', f'{S}/build.py', cfg, html, '--standalone'])
    run(['python3', f'{S}/build.py', cfg, f'{out}/{n}.widget.html'])
    b = '-'
    if not os.environ.get('NOBROWSER'):
        rc2, o2 = run(['python3', f'{S}/browser_check.py', f'{out}/{n}.widget.html', f'{out}/{n}'])
        b = 'ok' if rc2 == 0 else 'PROB:' + ' | '.join(o2.splitlines()[1:3])[:140]
    detail = (errs[:2] + warns[:1])
    print(f'{n:34} make:ok test:{tstat} browser:{b}  ' + ' || '.join(x[:110] for x in detail))
