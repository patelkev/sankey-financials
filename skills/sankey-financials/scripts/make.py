#!/usr/bin/env python3
"""Turn a sankey-financials spec (line items as reported) into a chart CFG.

Usage: python3 make.py spec.json out_cfg.json
Exits 1 with a plain message if the figures don't reconcile.

All money in $ millions. Signs follow the filing: income/inflows positive,
expenses/outflows positive where the spec says "cost" lists, see each flow.
"""
import datetime, json, re, sys

TOL = 1.0  # $M rounding tolerance for reported-total checks; make() shrinks it for small companies


class SpecError(Exception):
    pass


def slug(s, used):
    b = re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')[:18] or 'n'
    k, i = b, 2
    while k in used:
        k, i = f'{b}{i}', i + 1
    used.add(k)
    return k


def pair(x):
    """[cur, prior] or number -> (cur, prior|None)."""
    if isinstance(x, (list, tuple)):
        return float(x[0]), (None if len(x) < 2 or x[1] is None else float(x[1]))
    return float(x), None


def item(d):
    return d['l'], float(d['v']), (None if d.get('p') is None else float(d['p']))


SYMBOLS = {'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'CNY': 'CN¥', 'INR': '₹', 'KRW': '₩', 'CAD': 'C$',
           'AUD': 'A$', 'HKD': 'HK$', 'TWD': 'NT$', 'BRL': 'R$', 'MXN': 'MX$', 'CHF': 'CHF ', 'SEK': 'SEK ',
           'DKK': 'DKK ', 'NOK': 'NOK '}
CUR = '$'  # set by make() from spec['currency']


def money(v):
    a, c = abs(v), CUR
    s = (f'{c}{a/1e6:.2f}T' if a >= 1e6 else f'{c}{a/1000:.2f}B' if a >= 1000 else f'{c}{a:.1f}M' if a >= 1
         else f'{c}{a*1000:.0f}K' if a > 0 else f'{c}0')
    return ('-' if v < 0 else '') + s


def num(x):
    return f'{x:,.3f}' if TOL < 1 else f'{x:,.1f}'


def check(name, got, want):
    if want is None or got is None:
        return
    if abs(got - want) > TOL:
        raise SpecError(f'{name}: computed {num(got)} but the filing says {num(want)} '
                        f'(off by {num(got-want)}). Fix the line items before drawing.')


def check_prior(name, got, want):
    """Same check for the comparison column, so every Y/Y figure rests on reconciled numbers."""
    if want is None or got is None:
        return
    if abs(got - want) > TOL:
        raise SpecError(f'{name}, prior period: the prior figures add to {num(got)} but the reported prior total is '
                        f'{num(want)} (off by {num(got-want)}). Fix the prior figures (or set unknown ones to null).')


def psum(items, key='p'):
    """Sum of prior values, or None if any is missing."""
    vals = [d.get(key) for d in items]
    return None if any(x is None for x in vals) else sum(float(x) for x in vals)


def need(spec, *keys):
    for k in keys:
        if spec.get(k) is None:
            raise SpecError(f'"{k}" is required: it is the reported total the chart is checked against. '
                            'Copy it from the filing.')


def grouped(items):
    """Merge items sharing a 'group' key; drop zeros."""
    out, idx = [], {}
    for d in items:
        g = d.get('group')
        if g:
            if g not in idx:
                idx[g] = len(out)
                out.append({'l': g, 'v': 0.0, 'p': 0.0, 'parts': [], 'note': d.get('group_note')})
            o = out[idx[g]]
            o['v'] += float(d['v'])
            o['p'] = None if (o['p'] is None or d.get('p') is None) else o['p'] + float(d['p'])
            o['parts'].append(d['l'])
        else:
            out.append(dict(d))
    for o in out:
        if o.get('parts') and not o.get('note'):
            o['note'] = 'Combines ' + ', '.join(o['parts']) + '.'
        o.pop('parts', None)
    return [o for o in out if abs(float(o['v'])) > 1e-9]


class G:
    """Graph builder: nodes in column order, links, ids."""

    def __init__(self):
        self.nodes, self.links, self.used = [], [], set()
        self.shift = 0  # 1 drops column 2 (income statement without cost of revenue)

    def node(self, c, t, l, v, p=None, full=None, note=None, key=None):
        c = c - self.shift if c >= 2 else c
        nid = slug(key or l, self.used)
        n = {'id': nid, 'c': c, 't': t, 'l': l, 'v': round(v, 4), 'p': None if p is None else round(p, 4)}
        if full: n['full'] = full
        if note: n['note'] = note
        self.nodes.append(n)
        return nid

    def link(self, a, b, v):
        if v > 1e-9 and a != b:
            self.links.append([a, b, round(v, 4)])


def flip(v, p, kind):
    """Magnitude of a signed item, prior kept only if it had the same sign."""
    note = None
    if p is not None and (p > 0) != (v > 0) and p != 0:
        note = f'A year ago this line was {money(abs(p))} of {kind[1] if p > 0 else kind[0]}.'
        p = None
    return abs(v), (abs(p) if p is not None else None), note


def views_out(spec, used):
    out = {}
    for label, v in spec.get('views', {}).items():
        key = {'Product': 'prod', 'Business': 'biz', 'Geography': 'geo'}.get(label) or slug(label, set())
        if 'same' in v:
            if v['same'] not in spec['views'] or 'same' in spec['views'][v['same']]:
                raise SpecError(f'View {label} says "same":"{v["same"]}", but there is no view with items called that.')
            same = {'Product': 'prod', 'Business': 'biz', 'Geography': 'geo'}.get(v['same'], v['same'])
            out[key] = {'label': label, 'same': same}
        else:
            nodes = []
            for d in grouped(v['items']):
                n = {'id': slug(d['l'], used), 'l': d['l'], 'v': float(d['v'])}
                n['p'] = None if d.get('p') is None else float(d['p'])
                for f in ('full', 'note'):
                    if d.get(f): n[f] = d[f]
                nodes.append(n)
            out[key] = {'label': label, 'nodes': nodes}
        if v.get('note'): out[key]['note'] = v['note']
    # same-as views reuse ids of their source, fine.
    return out


# ---------------------------------------------------------------- income
def income(spec):
    g = G()
    rev, rev_p = pair(spec['revenue'])
    cogs, cogs_p = pair(spec.get('cogs', [0, 0]))
    # Banks, insurers and many service firms report no cost of revenue: skip the gross-profit step.
    nocogs = cogs == 0 and not cogs_p
    if nocogs: g.shift = 1
    opex = grouped(spec.get('opex', []))
    nonop = grouped(spec.get('nonop', []))
    tax, tax_p = pair(spec.get('tax', [0, 0]))
    sub = lambda a, b: None if a is None or b is None else a - b

    for label, v in spec.get('views', {}).items():
        if 'items' in v:
            check(f'{label} items vs revenue', sum(float(d['v']) for d in v['items']), rev)
            check_prior(f'{label} items vs revenue', psum(v['items']), rev_p)

    gp, gp_p = rev - cogs, sub(rev_p, cogs_p)
    if rev <= 0:
        raise SpecError(f'Revenue is {money(rev)}. The income chart starts from revenue, so it needs revenue above zero '
                        '(a pre-revenue company is better described in text, or shown as a cash flow).')
    if gp <= 0:
        raise SpecError('Gross loss (cost of revenue above revenue) is not supported yet.')
    ox = sum(float(d['v']) for d in opex)
    # priors come from the raw lines: grouped() drops lines that are zero now but were not a year ago
    ox_p = psum(spec['opex']) if opex else None
    oi, oi_p = gp - ox, sub(gp_p, ox_p)
    need(spec, 'operating_income', 'net_income')
    check('Operating income', oi, pair(spec['operating_income'])[0])
    check_prior('Operating income', oi_p, pair(spec['operating_income'])[1])

    R = g.node(1, 'rev', spec.get('revenue_label', 'Revenue'), rev, rev_p, key='rev')
    GP = R if nocogs else g.node(2, 'profit', 'Gross profit', gp, gp_p, key='gp')
    pos_ox = [d for d in opex if float(d['v']) > 0]
    gains_ox = [d for d in opex if float(d['v']) < 0]
    pos_sum = sum(float(d['v']) for d in pos_ox)

    if oi < 0:  # ---- operating loss: chain stops at opex
        loss = -oi
        lp = -oi_p if oi_p is not None and oi_p < 0 else None
        ni, ni_p = pair(spec['net_income']) if 'net_income' in spec else (None, None)
        nonop_sum = sum(float(d['v']) for d in nonop)
        check('Net income', oi + nonop_sum - tax, ni)
        nps = psum(spec.get('nonop', []))
        check_prior('Net income', None if oi_p is None or nps is None or tax_p is None else oi_p + nps - tax_p, ni_p)
        note = f'Spending exceeded gross profit by {money(loss)}.'
        if ni is not None:
            note += f' After other items and tax, the net loss was {money(-ni)}' + (f' ({money(-ni_p)} a year ago).' if ni_p is not None else '.')
        OL = g.node(2, 'loss', 'Operating loss', loss, lp, note=note, key='oploss')
        C = g.node(2, 'cost', 'Cost of revenue', cogs, cogs_p, key='cogs')
        OX = g.node(3, 'cost', 'Operating expenses', ox, ox_p, key='opex')
        g.link(R, GP, gp); g.link(R, C, cogs); g.link(GP, OX, gp); g.link(OL, OX, loss)
        if gains_ox:
            raise SpecError('Operating gains inside a loss-making quarter: group them into an opex line instead.')
        for d in pos_ox:
            l, v, p = item(d)
            g.link(OX, g.node(4, 'cost', l, v, p, d.get('full'), d.get('note')), v)
        return g, {'subtitle_extra': f'Net loss {money(-ni)}' if ni is not None else 'Operating loss'}

    C = g.node(2, 'cost', 'Cost of revenue', cogs, cogs_p, key='cogs')
    OI = g.node(3, 'profit', 'Operating income', oi, oi_p, key='oi')
    nonop_inc = [d for d in nonop if float(d['v']) > 0]
    nonop_exp = [d for d in nonop if float(d['v']) < 0]
    inc_ids = []
    for d in nonop_inc:
        l, v, p = item(d)
        v, p, note = flip(v, p, ('expense', 'income'))
        inc_ids.append((g.node(3, 'profit', l, v, p, d.get('full'), d.get('note') or note), v))
    OX = g.node(3, 'cost', 'Operating expenses', ox, ox_p, key='opex')
    gain_ids = []
    for d in gains_ox:
        l, v, p = item(d)
        v, p, note = flip(v, p, ('gain', 'charge'))
        gain_ids.append((g.node(3, 'profit', l, v, p, d.get('full'), d.get('note') or note), v))
    g.link(R, GP, gp); g.link(R, C, cogs); g.link(GP, OI, oi); g.link(GP, OX, ox)

    nonop_sum = sum(float(d['v']) for d in nonop)
    nonop_sum_p = psum(spec.get('nonop', []))
    pti = oi + nonop_sum
    pti_p = None if oi_p is None or nonop_sum_p is None else oi_p + nonop_sum_p
    if pti <= 0:
        raise SpecError('Pretax loss despite an operating profit is not supported yet.')
    PTI = g.node(4, 'profit', 'Pretax income', pti, pti_p, key='pti')
    g.link(OI, PTI, oi - sum(abs(float(d['v'])) for d in nonop_exp))
    for nid, v in inc_ids:
        g.link(nid, PTI, v)
    if len(nonop_exp) == 1:
        d = nonop_exp[0]; l, v, p = item(d); v, p, note = flip(v, p, ('expense', 'income'))
        g.link(OI, g.node(4, 'cost', l, v, p, d.get('full'), d.get('note') or note), v)
    elif nonop_exp:
        tot = sum(-float(d['v']) for d in nonop_exp)
        tp = None if any(d.get('p') is None or float(d['p']) >= 0 for d in nonop_exp) else sum(-float(d['p']) for d in nonop_exp)
        AG = g.node(4, 'cost', 'Interest and other', tot, tp if tp and tp > 0 else None, key='io')
        g.link(OI, AG, tot)
        later = []
        for d in nonop_exp:
            l, v, p = item(d); v, p, note = flip(v, p, ('expense', 'income'))
            later.append((AG, l, v, p, d.get('full'), d.get('note') or note))

    ni = pti - tax
    ni_p = None if pti_p is None or tax_p is None else pti_p - tax_p
    check('Net income', ni, pair(spec['net_income'])[0])
    check_prior('Net income', ni_p, pair(spec['net_income'])[1])
    if tax >= 0:
        NI = g.node(5, 'profit', 'Net income', ni, ni_p, note=spec.get('notes', {}).get('net_income'), key='ni')
        g.link(PTI, NI, pti - tax)
        if tax > 0:
            tp = tax_p if tax_p is not None and tax_p > 0 else None
            g.link(PTI, g.node(5, 'cost', 'Income tax', tax, tp, key='tax',
                               note=None if tp is not None or tax_p is None else f'A year ago tax was a {money(-tax_p)} benefit.'), tax)
    else:
        TB = g.node(4, 'profit', 'Tax benefit', -tax, -tax_p if tax_p is not None and tax_p < 0 else None, key='taxb')
        NI = g.node(5, 'profit', 'Net income', ni, ni_p, note=spec.get('notes', {}).get('net_income'), key='ni')
        g.link(PTI, NI, pti); g.link(TB, NI, -tax)
    if len(nonop_exp) > 1:
        for AG, l, v, p, full, note in later:
            g.link(AG, g.node(5, 'cost', l, v, p, full, note), v)
    if gain_ids:
        AGO = g.node(4, 'cost', 'Gross operating expenses', pos_sum, None, key='gox',
                     note='Operating expenses before the gains shown entering this box.')
        g.link(OX, AGO, ox)
        for nid, v in gain_ids:
            g.link(nid, AGO, v)
        src = AGO
    else:
        src = OX
    for d in pos_ox:
        l, v, p = item(d)
        g.link(src, g.node(5, 'cost', l, v, p, d.get('full'), d.get('note')), v)
    return g, {}


# ---------------------------------------------------------------- cash flow
def cashflow(spec):
    g = G()
    ops = grouped(spec['operating'])
    cfo, cfo_p = pair(spec['cfo'])
    check('Operating items vs cash from operations', sum(float(d['v']) for d in ops), cfo)
    check_prior('Operating items vs cash from operations', psum(spec['operating']), cfo_p)
    if cfo <= 0:
        raise SpecError('Negative operating cash flow is not supported yet.')
    capex, capex_p = pair(spec['capex'])
    if capex < 0 or (capex_p or 0) < 0:
        raise SpecError(f'capex is {money(capex)}. Enter capital expenditures as a positive number, although the '
                        'filing shows them in parentheses.')
    other = grouped(spec.get('other', []))
    chg, chg_p = pair(spec['change_in_cash'])
    check('Change in cash', cfo - capex + sum(float(d['v']) for d in other), chg)
    op = psum(spec.get('other', []))
    check_prior('Change in cash', None if None in (cfo_p, capex_p, op) else cfo_p - capex_p + op, chg_p)

    H = g.node(1, 'rev', 'Operating cash flow', cfo, cfo_p, key='cfo')
    fcf = cfo - capex
    fcf_p = None if cfo_p is None or capex_p is None else cfo_p - capex_p
    inflows = [d for d in other if float(d['v']) > 0]
    uses = [d for d in other if float(d['v']) < 0]
    pool_in = []
    if fcf > 0:
        F = g.node(2, 'profit', 'Free cash flow', fcf, fcf_p if fcf_p and fcf_p > 0 else None, key='fcf')
        g.link(H, F, fcf); pool_in.append((F, fcf))
    for d in inflows:
        l, v, p = item(d); v, p, note = flip(v, p, ('outflow', 'inflow'))
        pool_in.append((g.node(2, 'rev', l, v, p, d.get('full'), d.get('note') or note), v))
    if chg < 0:
        pool_in.append((g.node(2, 'loss', 'Drawn from cash', -chg, -chg_p if chg_p is not None and chg_p < 0 else None,
                               note='Spending beyond the cash generated, paid from the existing cash balance.', key='draw'), -chg))
    if fcf >= 0:
        CX = g.node(2, 'cost', 'Capital expenditures', capex, capex_p, key='capex')
        g.link(H, CX, capex)
    pool = sum(v for _, v in pool_in)
    if len(pool_in) == 1 and fcf > 0:
        P, uc = pool_in[0][0], 3
    else:
        P, uc = g.node(3, 'profit', 'Cash to deploy', pool, None, key='pool',
                       note='Free cash flow plus any other inflows, before buybacks, dividends and other uses.'), 4
        for nid, v in pool_in:
            g.link(nid, P, v)
    if fcf < 0:
        # Capex above operating cash flow: draw the full capex figure (so its value and Y/Y are the
        # real ones), funded by all of operating cash flow plus the shortfall from the pool.
        CX = g.node(uc, 'cost', 'Capital expenditures', capex, capex_p, key='capex',
                    note=f'Paid with all {money(cfo)} of operating cash flow plus {money(-fcf)} from the other sources '
                         f'on the left: free cash flow was {money(fcf)}.')
        g.link(H, CX, cfo); g.link(P, CX, -fcf)
    for d in uses:
        l, v, p = item(d); v, p, note = flip(v, p, ('outflow', 'inflow'))
        g.link(P, g.node(uc, 'cost', l, v, p, d.get('full'), d.get('note') or note), v)
    if chg > 0:
        g.link(P, g.node(uc, 'profit', 'Added to cash', chg, chg_p if chg_p and chg_p > 0 else None, key='addcash'), chg)
    return g, {'hub': 'cfo', 'subtitle_extra': f'Free cash flow {money(fcf)}' if fcf < 0 else None}


# ---------------------------------------------------------------- balance sheet
def net_into_largest(items, kind):
    """Net negative lines (treasury stock, AOCI, accumulated depreciation) against the positive lines,
    largest first. When the negatives outweigh the largest line they spill into the next one, and lines
    netted down to zero are dropped, so no box goes negative (Boeing's treasury stock is larger than
    any single positive equity line)."""
    pos = sorted([dict(d) for d in items if float(d['v']) > 0], key=lambda d: -float(d['v']))
    neg = [d for d in items if float(d['v']) < 0]
    if not (neg and pos):
        return pos

    def spill(vals, owed):
        out, touched = list(vals), []
        for i, v in enumerate(out):
            if owed <= 1e-9: break
            take = min(v, owed); out[i] -= take; owed -= take; touched.append(i)
        return out, touched, owed

    cur, touched, left = spill([float(d['v']) for d in pos], -sum(float(d['v']) for d in neg))
    if left > 1e-9:  # negatives outweigh every positive line: the group total is negative
        return pos
    pri = [d.get('p') for d in pos]
    negp = [d.get('p') for d in neg]
    prior_ok = None not in pri and None not in negp
    if prior_ok:
        pcur, ptouched, pleft = spill([float(x) for x in pri], -sum(float(x) for x in negp))
        prior_ok = ptouched == touched and pleft <= 1e-9
    what = ', '.join(f"{d['l']} ({money(float(d['v']))})" for d in neg)
    if len(touched) == 1:
        d = pos[touched[0]]
        d['v'] = cur[touched[0]]
        d['p'] = pcur[touched[0]] if prior_ok else None
        d['l'] += ' (net)'
        d['note'] = ((d.get('note') or '') + f' Shown net of {what}.').strip()
        return pos
    # The negatives outweigh the largest line: merge the lines they absorb into one box, so no single
    # line is shown with a misleading net figure.
    tl = [pos[i] for i in touched]
    pv = [d.get('p') for d in tl] + negp
    merged = {'l': ' and '.join(d['l'] for d in tl) + ' (net)', 'v': sum(cur[i] for i in touched),
              'p': None if None in pv else sum(float(x) for x in pv),
              'note': 'Combines ' + ', '.join(f"{d['l']} ({money(float(d['v']))})" for d in tl) + f', net of {what}.'}
    return [merged] + [d for i, d in enumerate(pos) if i not in touched]


def balance(spec):
    g = G()
    assets = grouped(spec['assets'])
    liabs = grouped(spec['liabilities'])
    eq_items = grouped(spec['equity'])
    ta = sum(float(d['v']) for d in assets)
    tl = sum(float(d['v']) for d in liabs)
    te = sum(float(d['v']) for d in eq_items)
    ta_p = psum(spec['assets'])
    tl_p = psum(spec['liabilities'])
    te_p = psum(spec['equity'])
    need(spec, 'total_assets')
    check('Total assets', ta, pair(spec['total_assets'])[0])
    check('Assets = liabilities + equity', ta, tl + te)
    check_prior('Total assets', ta_p, pair(spec['total_assets'])[1])
    check_prior('Liabilities + equity vs total assets', None if tl_p is None or te_p is None else tl_p + te_p, ta_p)
    assets = net_into_largest(assets, 'asset')
    if te < 0:
        A = [(g.node(0, 'rev', *item(d)[0:3], d.get('full'), d.get('note')), float(d['v'])) for d in assets]
        D = g.node(0, 'loss', "Shareholders' deficit", -te, -te_p if te_p is not None and te_p < 0 else None, key='deficit',
                   note='Liabilities exceed assets by this amount, usually from buybacks and dividends above cumulative earnings.')
        Hn = g.node(1, 'cost', 'Total liabilities', tl, tl_p, key='tl')
        for nid, v in A: g.link(nid, Hn, v)
        g.link(D, Hn, -te)
        for d in net_into_largest(liabs, 'liability'):
            l, v, p = item(d); g.link(Hn, g.node(2, 'cost', l, v, p, d.get('full'), d.get('note')), v)
        return g, {'hub': 'tl', 'views': False}
    A = [(g.node(0, 'rev', *item(d)[0:3], d.get('full'), d.get('note')), float(d['v'])) for d in assets]
    Hn = g.node(1, 'rev', 'Total assets', ta, ta_p, key='ta')
    for nid, v in A: g.link(nid, Hn, v)
    E = g.node(2, 'profit', "Shareholders' equity", te, te_p, key='te')
    L = g.node(2, 'cost', 'Total liabilities', tl, tl_p, key='tl')
    g.link(Hn, E, te); g.link(Hn, L, tl)
    for d in net_into_largest(eq_items, 'equity'):
        l, v, p = item(d); g.link(E, g.node(3, 'profit', l, v, p, d.get('full'), d.get('note')), v)
    for d in net_into_largest(liabs, 'liability'):
        l, v, p = item(d); g.link(L, g.node(3, 'cost', l, v, p, d.get('full'), d.get('note')), v)
    return g, {'hub': 'ta', 'views': False}


# ---------------------------------------------------------------- fund holdings
def holdings(spec):
    g = G()
    minw = float(spec.get('min_weight', 2.0))
    sectors = spec['sectors']
    tot = sum(float(s['v']) for s in sectors)
    if abs(tot - 100) > 1.5:
        raise SpecError(f'Sector weights sum to {tot:.2f}%, expected about 100%.')
    merged = {}
    for h in spec['holdings']:
        k = (h['l'], h['sector'])
        merged[k] = merged.get(k, 0) + float(h['v'])
    names = {s['l'] for s in sectors}
    for (l, s) in merged:
        if s not in names:
            raise SpecError(f'Holding {l} maps to unknown sector "{s}".')
    Hn = g.node(0, 'rev', spec['fund'], tot, None, key='fund',
                note=f"{spec.get('count', '?')} holdings" + (f", {money(spec['aum'])} in assets" if spec.get('aum') else '') + '.')
    later = []
    for s in sorted(sectors, key=lambda s: -float(s['v'])):
        sv = float(s['v'])
        named = sorted([(l, w) for (l, sec), w in merged.items() if sec == s['l'] and w >= minw], key=lambda x: -x[1])
        shown = sum(w for _, w in named)
        if shown > sv + 0.15:
            raise SpecError(f'Holdings mapped to {s["l"]} total {shown:.2f}% but the sector is {sv:.2f}%; check the mapping.')
        S = g.node(1, 'profit' if named else 'other', s['l'], sv, None, key='sec_' + s['l'])
        g.link(Hn, S, sv)
        later.append((S, named, max(sv - shown, 0.0), s['l']))
    for S, named, rest, sl in later:
        if not named: continue
        for l, w in named:
            g.link(S, g.node(2, 'rev', l, w, None), w)
        if rest > 0.01:
            g.link(S, g.node(2, 'other', f'Other {sl.lower()}', rest, None,
                             note=f'Holdings under {minw:g}% each.'), rest)
    return g, {'hub': 'fund', 'views': False}


# ---------------------------------------------------------------- segments
def segments(spec):
    g = G()
    segs = spec['segments']
    extra_rev = grouped(spec.get('other_revenue', []))
    corp = grouped(spec.get('corporate', []))
    for d in extra_rev:
        if float(d['v']) < 0:
            raise SpecError(f'Negative other revenue "{d["l"]}": put intersegment eliminations in "eliminations" '
                            'and other negative items in "corporate".')
    tot_rev = sum(pair(s['revenue'])[0] for s in segs) + sum(float(d['v']) for d in extra_rev)
    need(spec, 'revenue', 'operating_income')
    # Intersegment eliminations reduce reported revenue but not operating income (their profit effect is
    # reported in a corporate/eliminations line). Segment boxes stay gross, as the filing shows them.
    elim = spec.get('eliminations', [])
    if any(float(d['v']) > 0 for d in elim):
        raise SpecError('eliminations are reductions of revenue: enter them as negative numbers, as filed.')
    elim_v = sum(float(d['v']) for d in elim)
    check('Segment revenue vs total revenue', tot_rev + elim_v, pair(spec['revenue'])[0])
    srp = [pair(s['revenue'])[1] for s in segs]
    orp, elp = psum(spec.get('other_revenue', [])), psum(elim)
    check_prior('Segment revenue vs total revenue',
                None if None in srp or orp is None or elp is None else sum(srp) + orp + elp, pair(spec['revenue'])[1])
    oi = (sum(pair(s['operating_income'])[0] for s in segs) + sum(float(d['v']) for d in corp)
          + sum(float(d['v']) for d in extra_rev))
    oi_rep, oi_p = pair(spec['operating_income']) if 'operating_income' in spec else (None, None)
    check('Operating income', oi, oi_rep)
    sop = [pair(s['operating_income'])[1] for s in segs]
    check_prior('Operating income', None if None in sop or psum(spec.get('corporate', [])) is None or psum(spec.get('other_revenue', [])) is None
                else sum(sop) + psum(spec.get('corporate', [])) + psum(spec.get('other_revenue', [])), oi_p)
    if oi <= 0:
        raise SpecError('Total operating loss is not supported in the segment view yet.')
    rev_ids, er_ids = [], []
    for s in segs:
        r, rp = pair(s['revenue'])
        rev_ids.append(g.node(0, 'rev', s['l'], r, rp, key='r_' + s['l']))
    for d in extra_rev:
        l, v, p = item(d)
        er_ids.append((g.node(0, 'rev', l, v, p, d.get('full'), d.get('note')), v))
    pool_in, losses, costs = [], [], []
    for s, rid in zip(segs, rev_ids):
        r, rp = pair(s['revenue']); o, op = pair(s['operating_income'])
        if o > 0:
            P = g.node(1, 'profit', f"{s['l']} profit", o, op if op and op > 0 else None, key='p_' + s['l'])
            g.link(rid, P, o); pool_in.append((P, o))
            costs.append((rid, f"{s['l']} costs", r - o, None if rp is None or op is None else rp - op, None))
        else:
            costs.append((rid, f"{s['l']} costs", r, None,
                          f"Covered by its own revenue; the remaining {money(-o)} of spending is the loss on the right."))
            losses.append((f"{s['l']} loss", -o, -op if op is not None and op < 0 else None,
                           f"{s['l']} spent {money(r - o)} against {money(r)} of revenue."))
    cost_nodes = costs
    corp_cost = []
    for d in corp:
        l, v, p = item(d)
        if v > 0:
            pool_in.append((g.node(1, 'profit', l, v, p if p and p > 0 else None, d.get('full'), d.get('note')), v))
        else:
            corp_cost.append((l, -v, -p if p is not None and p < 0 else None, d.get('note')))
    for nid, v in er_ids:
        pool_in.append((nid, v))
    for rid, l, v, p, note in cost_nodes:
        g.link(rid, g.node(1, 'cost', l, v, p, note=note, key='c_' + l), v)
    pool = sum(v for _, v in pool_in)
    PL = g.node(2, 'profit', 'Segment profit pool', pool, None, key='pool',
                note='Profit from money-making segments plus any other revenue, before losses and corporate costs.')
    for nid, v in pool_in:
        g.link(nid, PL, v)
    g.link(PL, g.node(3, 'profit', 'Operating income', oi, oi_p, key='oi'), oi)
    for l, v, p, note in losses:
        g.link(PL, g.node(3, 'loss', l, v, p, note=note), v)
    for l, v, p, note in corp_cost:
        g.link(PL, g.node(3, 'cost', l, v, p, note=note), v)
    meta = {'hub': None, 'scale': {'v': tot_rev, 'l': 'Revenue' if not elim else 'Segment revenue'}, 'views': False}
    if elim:
        meta['subtitle_extra'] = f'Segments before {money(-elim_v)} of intersegment eliminations'
    return g, meta


FLOWS = {'income': income, 'cashflow': cashflow, 'balance': balance, 'holdings': holdings, 'segments': segments}
LEGENDS = {
    'income': [['Revenue', 'rev'], ['Expense', 'cost'], ['Profit', 'profit'], ['Loss', 'loss']],
    'cashflow': [['Sources', 'rev'], ['Uses', 'cost'], ['Kept or free', 'profit']],
    'balance': [['Assets', 'rev'], ['Liabilities', 'cost'], ['Equity', 'profit']],
    'holdings': [['Fund and holdings', 'rev'], ['Sectors', 'profit'], ['Other', 'other']],
    'segments': [['Revenue', 'rev'], ['Costs', 'cost'], ['Profit', 'profit'], ['Loss', 'loss']],
}
DEFAULT_TITLE = {'income': 'income statement', 'cashflow': 'cash flow', 'balance': 'balance sheet',
                 'holdings': 'holdings', 'segments': 'segment profit'}


def tolerance(spec):
    """$1M for normal filers (figures rounded to millions); smaller for companies reporting in
    thousands, where a flat $1M would let almost any mistake through."""
    big = 0.0
    def walk(x):
        nonlocal big
        if isinstance(x, bool): return
        if isinstance(x, (int, float)): big = max(big, abs(x))
        elif isinstance(x, list): [walk(y) for y in x]
        elif isinstance(x, dict): [walk(y) for k, y in x.items() if k not in ('count', 'min_weight')]
    walk({k: spec.get(k) for k in ('revenue', 'total_assets', 'cfo', 'segments')})
    return min(1.0, max(0.005, big * 0.005))


def compare_labels(spec, flow):
    """(cmp, prev_label) for the comparison switch. Explicit cmp/prev_label win; otherwise derived from
    the end dates of the two periods, so a balance sheet compared with Dec 31 can't be labelled Y/Y."""
    if spec.get('cmp'):
        return spec['cmp'], spec.get('prev_label')
    if spec.get('end') and spec.get('prior_end'):
        try:
            e, p = (datetime.date.fromisoformat(spec[k]) for k in ('end', 'prior_end'))
        except ValueError:
            raise SpecError('end and prior_end must be dates like 2026-09-30.')
        months = round((e - p).days / 30.44)
        if months == 12: return 'Y/Y', 'Year ago'
        if months == 3 and flow != 'balance': return 'Q/Q', 'Prior quarter'
        d = f'{p:%b} {p.day}, {p.year}'
        return f'vs {p:%b} {p.day}', d
    if flow == 'balance':
        raise SpecError('A balance sheet needs "end" and "prior_end" (e.g. "2026-09-30" and "2025-12-31"), or an '
                        'explicit "cmp"/"prev_label": 10-Qs usually compare with the last fiscal year end, not a year ago.')
    return None, spec.get('prev_label')


HINTS = {
    'ni': 'Net income is negative although pretax income is positive (tax above pretax income). That case is not supported yet.',
    'pti': 'Pretax income is not fully used by tax and net income; check tax and net_income.',
}


def finish(g, flow):
    """Drop zero-value boxes, then refuse any box the chart can't draw (negative or unbalanced)."""
    inn, out = {}, {}
    for a, b, v in g.links:
        out[a] = out.get(a, 0) + v; inn[b] = inn.get(b, 0) + v
    g.nodes = [n for n in g.nodes if abs(n['v']) > 1e-9 or n['id'] in inn or n['id'] in out]
    for n in g.nodes:
        if n['v'] <= 0:
            hint = HINTS.get(n['id']) or ('Negative lines were netted into this one and outweigh it; group them differently.'
                                          if '(net)' in n['l'] else 'This flow type cannot draw a negative box here.')
            raise SpecError(f'"{n["l"]}" works out to {money(n["v"])}. {hint}')
    for n in g.nodes:
        for side, tot in (('in', inn), ('out', out)):
            if n['id'] in tot and abs(tot[n['id']] - n['v']) > 0.51:
                raise SpecError(f'"{n["l"]}" is {money(n["v"])} but its {side}flows add to {money(tot[n["id"]])}. '
                                + HINTS.get(n['id'], 'The line items are inconsistent for this flow type.'))


def make(spec):
    flow = spec['flow']
    if flow not in FLOWS:
        raise SpecError(f'Unknown flow "{flow}". Use one of {", ".join(FLOWS)}.')
    global TOL, CUR
    TOL = tolerance(spec)
    code = str(spec.get('currency', 'USD')).upper()
    CUR = SYMBOLS.get(code, code + ' ')
    g, meta = FLOWS[flow](spec)
    finish(g, flow)
    used = {n['id'] for n in g.nodes}
    cfg = {
        'company': spec.get('company', spec.get('fund', '')),
        'ticker': spec['ticker'],
        'title': spec.get('title') or f"{spec['ticker']} {spec['period']} {DEFAULT_TITLE[flow]}",
        'sub': ' · '.join(x for x in [spec.get('dates'), code if flow != 'holdings' else 'Weight of fund',
                                      spec.get('basis'), meta.get('subtitle_extra')] if x),
        'flow': flow,
        'legend': [l for l in LEGENDS[flow] if any(n['t'] == l[1] for n in g.nodes) or l[1] == 'rev'],
        'base': g.nodes, 'links': g.links,
    }
    if flow == 'holdings':
        cfg['unit'] = 'pct'
    elif CUR != '$':
        cfg['cur'] = CUR
    hub = meta.get('hub', 'rev')
    if hub: cfg['hub'] = hub
    if meta.get('scale'): cfg['scale'] = meta['scale']
    if flow == 'income' and spec.get('views'):
        cfg['views'] = views_out(spec, used)
    elif flow == 'cashflow':
        ops = grouped(spec['operating'])
        cfg['views'] = {'ops': {'label': 'Operating', 'nodes': [
            dict({'id': slug(d['l'], used), 'l': d['l'], 'v': float(d['v']),
                  'p': None if d.get('p') is None else float(d['p'])}, **({'note': d['note']} if d.get('note') else {}))
            for d in ops]}}
        for n in cfg['views']['ops']['nodes']:
            if n['p'] is not None and (n['p'] > 0) != (n['v'] > 0):
                n['note'] = (n.get('note', '') + f" A year ago this was {money(n['p'])}.").strip()
                n['p'] = None if n['v'] > 0 else n['p']
    has_prior = any(n.get('p') is not None for n in g.nodes)
    cfg['yoy'] = bool(has_prior and spec.get('compare', True))
    if spec.get('source'): cfg['source'] = spec['source']
    cmp, prev = compare_labels(spec, flow)
    if cmp: cfg['cmp'] = cmp
    if prev: cfg['prevLabel'] = prev
    return cfg


if __name__ == '__main__':
    def no_nan(c):
        raise SpecError(f'The spec contains {c}; every number must be a real figure (use null for an unknown prior).')
    try:
        cfg = make(json.load(open(sys.argv[1]), parse_constant=no_nan))
    except SpecError as e:
        print(f'SPEC ERROR: {e}', file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f'SPEC ERROR: missing field {e}. See references/spec-format.md for the fields this flow needs.', file=sys.stderr)
        sys.exit(1)
    except (ValueError, TypeError) as e:
        print(f'SPEC ERROR: a value has the wrong type ({e}). Numbers must be plain JSON numbers in $ millions, '
              'no commas, currency signs or quotes.', file=sys.stderr)
        sys.exit(1)
    json.dump(cfg, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
    print(f'{sys.argv[2]}: {len(cfg["base"])} nodes, {len(cfg["links"])} links')
