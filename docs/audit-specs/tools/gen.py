#!/usr/bin/env python3
"""Generate the audit test matrix specs. Figures marked 'approx' are recalled public figures,
rounded; 'synthetic' are invented to hit an edge case."""
import json, os, sys, copy
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
def w(name, d):
    json.dump(d, open(f'{OUT}/{name}.json', 'w'), indent=1, allow_nan=True)
def base(flow, co, tk, per, dates, src='synthetic'):
    return {'flow': flow, 'company': co, 'ticker': tk, 'period': per, 'dates': dates, 'basis': 'GAAP', 'source': src}
def it(l, v, p=None, **k): d = {'l': l, 'v': v, 'p': p}; d.update(k); return d

# ---------------- income ----------------
inc = base('income', 'Testco', 'TST', 'Q2 2026', 'Apr 1 to Jun 30, 2026')
inc.update(revenue=[1000, 900], cogs=[400, 380], opex=[it('R&D', 200, 190), it('SG&A', 150, 140)],
           operating_income=[250, 190], nonop=[it('Interest income', 10, 8)], tax=[50, 40], net_income=[210, 158])
w('i01_baseline', inc)

# prior-period figures are never reconciled: operating_income prior says 190 but opex priors imply 290
d = copy.deepcopy(inc); d['opex'][0]['p'] = 90; w('i02_prior_mismatch_silent', d)
# view priors don't sum to revenue prior
d = copy.deepcopy(inc); d['views'] = {'Product': {'items': [it('A', 600, 100), it('B', 400, 100)]}}; w('i03_view_prior_mismatch', d)
# omit operating_income and net_income: nothing reconciles
d = copy.deepcopy(inc); del d['operating_income']; del d['net_income']; d['opex'][0]['v'] = 999; d['tax'] = [0, 0]
w('i04_no_totals_given', d)
# bank: no COGS (JPM-ish approx Q3 2025 managed: rev ~47.1B, provision ~3.4B, nonint exp ~24.3B, NI ~14.4B)
bank = base('income', 'JPMorgan Chase', 'JPM', 'Q3 2025', 'Jul 1 to Sep 30, 2025', 'approx, JPM Q3 2025 release')
bank.update(revenue=[46430, 42654], cogs=[0, 0], opex=[it('Provision for credit losses', 3403, 3111), it('Noninterest expense', 24250, 22565)],
            operating_income=[18777, 16978], nonop=[], tax=[4384, 4080], net_income=[14393, 12898])
w('i05_bank_cogs0', bank)
d = copy.deepcopy(bank); del d['cogs']; w('i06_bank_no_cogs_key', d)
# biotech, zero revenue
bio = base('income', 'Biotech Zero', 'BZRO', 'Q1 2026', 'Jan 1 to Mar 31, 2026')
bio.update(revenue=[0, 0], cogs=[0, 0], opex=[it('R&D', 120, 95), it('G&A', 30, 25)], operating_income=[-150, -120],
           nonop=[it('Interest income', 8, 9)], tax=[0, 0], net_income=[-142, -111])
w('i07_biotech_zero_rev', bio)
# biotech small collaboration revenue, no cogs
d = copy.deepcopy(bio); d['revenue'] = [5, 2]; d['operating_income'] = [-145, -118]; d['net_income'] = [-137, -109]; w('i08_biotech_tiny_rev_cogs0', d)
# negative revenue (reversal)
d = copy.deepcopy(inc); d['revenue'] = [-10, 900]; w('i09_negative_revenue', d)
# tax bigger than pretax -> net loss with operating profit (valuation allowance)
d = copy.deepcopy(inc); d['tax'] = [300, 40]; d['net_income'] = [-40, 158]; w('i10_tax_exceeds_pretax', d)
# pretax loss despite op profit (impairment in nonop) - profit-to-loss flip
d = copy.deepcopy(inc); d['nonop'] = [it('Impairment of investment', -400, 0)]; d['tax'] = [-20, 40]; d['net_income'] = [-130, 158]
w('i11_pretax_loss_flip', d)
# loss-to-profit flip
d = copy.deepcopy(inc); d['operating_income'] = [250, -60]; d['opex'][0]['p'] = 440; d['net_income'] = [210, -92]; d['tax'] = [50, 0]
d['opex'][1]['p'] = 140; d['nonop'][0]['p'] = 8; d['net_income'] = [210, -52]; w('i12_loss_to_profit', d)
# profit to operating loss
d = copy.deepcopy(inc); d['opex'][0]['v'] = 500; d['operating_income'] = [-50, 190]; d['tax'] = [-5, 40]; d['net_income'] = [-35, 158]
w('i13_profit_to_oploss', d)
# NCI: Walmart FY2025 approx (rev 680,985, cogs 511,753, opex 130,971 => OI 29,348 (reported 29,348)
wmt = base('income', 'Walmart', 'WMT', 'FY2025', 'Feb 1, 2024 to Jan 31, 2025', 'approx, WMT FY2025 10-K')
wmt.update(revenue=[680985, 648125], cogs=[511753, 490142], opex=[it('Operating, SG&A', 139884, 130971)],
           operating_income=[29348, 27012], nonop=[it('Interest, net', -2249, -2137), it('Other gains and losses', 1027, -3027)],
           tax=[6152, 5578], net_income=[21974, 16270])
w('i14_wmt_nci_consolidated', wmt)
# discontinued operations stuffed into nonop (silently labelled pretax)
d = copy.deepcopy(inc); d['nonop'].append(it('Income from discontinued ops, net of tax', 60, 0)); d['net_income'] = [270, 158]
w('i15_discontinued_in_nonop', d)
# non-USD IFRS filer (SAP-like, EUR m, approx FY2024): rev 34,176
sap = base('income', 'SAP', 'SAP', 'FY2024', 'Jan 1 to Dec 31, 2024', 'approx, SAP FY2024 IFRS, EUR')
sap['basis'] = 'IFRS'; sap['currency'] = 'EUR'
sap.update(revenue=[34176, 31207], cogs=[9887, 8937], opex=[it('R&D', 6513, 6324), it('S&M', 9671, 9050), it('G&A', 1626, 1499), it('Restructuring', 3144, 215)],
           operating_income=[3335, 5182], nonop=[it('Financial income, net', 250, 386)], tax=[2133, 1817], net_income=[1452, 3751])
w('i16_sap_eur_ifrs', sap)
# Toyota JPY (millions of yen) approx FY2025: revenue 48,036,704 -> trillions
ty = base('income', 'Toyota', 'TM', 'FY2025', 'Apr 1, 2024 to Mar 31, 2025', 'approx, Toyota 20-F, JPY')
ty['currency'] = 'JPY'
ty.update(revenue=[48036704, 45095325], cogs=[38578, 0], opex=[], operating_income=None)
ty['cogs'] = [39000000, 35000000]; ty['opex'] = [it('SG&A', 4241000, 4744000)]; del ty['operating_income']
ty['nonop'] = [it('Other income, net', 600000, 900000)]; ty['tax'] = [1400000, 1600000]
w('i17_toyota_jpy_huge', ty)
# tiny company in $ thousands -> money in fractions of $M ; and tolerance hides 0.9M errors
tiny = base('income', 'Microcap', 'MCRO', 'Q1 2026', 'Jan 1 to Mar 31, 2026')
tiny.update(revenue=[0.85, 0.62], cogs=[0.30, 0.25], opex=[it('SG&A', 0.40, 0.30)], operating_income=[0.15, 0.07], nonop=[], tax=[0, 0], net_income=[0.95, 0.07])
w('i18_tiny_thousands_tolerance', tiny)
# 30 opex lines
d = copy.deepcopy(inc); d['opex'] = [it(f'Expense line {i}', 10 + i % 3, 9) for i in range(30)]
tot = sum(x['v'] for x in d['opex']); d['operating_income'] = [600 - tot, None]; d['nonop'] = []; d['tax'] = [0, 0]; d['net_income'] = [600 - tot, None]
w('i19_many_opex', d)
# very long labels, unicode, emoji
d = copy.deepcopy(inc)
d['opex'] = [it('Research, development and engineering expenses including stock-based compensation and amortization', 200, 190),
             it('販売費及び一般管理費 (SG&A) 🚀', 150, 140)]
d['views'] = {'Product': {'items': [it('Ünïcødé Wídgets — Premium Edition™ for Enterprise and Government customers worldwide', 700, 600), it('🔥 Services', 300, 300)]}}
w('i20_long_unicode_labels', d)
# XSS
d = copy.deepcopy(inc)
d['ticker'] = 'X</title><script>alert(1)</script>'; d['company'] = 'Evil "Co" <b>'
d['source'] = '<img src=x onerror=alert(2)>'
d['opex'][0]['l'] = '</script><script>alert(3)</script>'; d['opex'][1]['note'] = '<img src=x onerror=alert(4)>'
d['dates'] = '<svg onload=alert(5)>'
w('i21_xss', d)
# malformed
d = copy.deepcopy(inc); d['opex'][0]['v'] = '1,200'; w('i22_string_number', d)
d = copy.deepcopy(inc); d['opex'][0]['p'] = float('nan'); w('i23_nan_prior', d)
d = copy.deepcopy(inc); d['opex'][0]['v'] = float('nan'); w('i24_nan_value', d)
d = copy.deepcopy(inc); del d['ticker']; w('i25_missing_ticker', d)
d = copy.deepcopy(inc); d['flow'] = 'Income'; w('i26_flow_case', d)
d = copy.deepcopy(inc); d['opex'].append(it('R&D', 0, 0)); d['opex'].append(it('SG&A', 0.0, 5)); w('i27_dup_and_zero_labels', d)
z = base('income', 'Zero', 'ZERO', 'Q1', 'x'); z.update(revenue=[0, 0], cogs=[0, 0], opex=[], nonop=[], tax=[0, 0]); w('i28_all_zero', z)
d = copy.deepcopy(inc); d['revenue'] = [1000]; d['cogs'] = 400; w('i29_scalar_and_short_pairs', d)
d = copy.deepcopy(inc); d['views'] = {'Product': {'items': [it('A', 600, 500), it('B', 400, 400)]}, 'Business': {'same': 'Segments'}}; w('i30_same_bad_ref', d)
d = copy.deepcopy(inc); d['views'] = {'Product': {'items': [it('A', 1000, 900)]}}; w('i31_single_item_view', d)
# gains in opex during operating loss -> refused
d = copy.deepcopy(inc); d['opex'] = [it('R&D', 700, 190), it('Gain on sale', -50, None)]; d['operating_income'] = [-50, None]; d['tax'] = [0, 0]; d['net_income'] = [-40, None]
w('i32_gain_in_oploss', d)
# quarter with only Q/Q comparison but default label says Y/Y
d = copy.deepcopy(inc); d['period'] = 'Q2 2026 vs Q1 2026'; w('i33_qoq_label_default', d)
# prior null everywhere (first quarter after IPO)
d = copy.deepcopy(inc)
for k in ('revenue', 'cogs', 'operating_income', 'tax', 'net_income'): d[k] = [d[k][0], None]
for x in d['opex'] + d['nonop']: x['p'] = None
w('i34_ipo_no_priors', d)
# 9M / restated priors fine; 53-week year label only
d = copy.deepcopy(inc); d['period'] = 'FY2026 (53 weeks)'; d['dates'] = '53 weeks to Feb 1, 2026 vs 52 weeks'; w('i35_53week', d)
# large SBC / equity-method income line in nonop
d = copy.deepcopy(inc); d['nonop'].append(it('Equity-method income (after tax)', 40, 30)); d['net_income'] = [250, 188]; w('i36_equity_method_after_tax', d)

# ---------------- cash flow ----------------
cf = base('cashflow', 'Cashco', 'CSH', 'FY2026', 'Jan 1 to Dec 31, 2026')
cf.update(operating=[it('Net income', 800, 700), it('D&A', 200, 180)], cfo=[1000, 880], capex=[300, 250],
          other=[it('Buybacks', -400, -300), it('Dividends', -100, -90)], change_in_cash=[200, 240])
w('c01_baseline', cf)
d = copy.deepcopy(cf); d['capex'] = [-300, -250]; w('c02_capex_signed_as_filed', d)
d = copy.deepcopy(cf); d['capex'] = [0, 0]; d['change_in_cash'] = [500, 490]; w('c03_capex_zero', d)
# negative FCF: capex prior vs capped node value
d = copy.deepcopy(cf); d['capex'] = [1500, 600]; d['other'] = [it('Debt issued', 800, 0)]; d['change_in_cash'] = [300, 280]; w('c04_negfcf_capex_yoy', d)
# Boeing 9M 2025 style: huge financing vs small cfo
d = copy.deepcopy(cf); d['operating'] = [it('Net loss', -1000, -9000), it('Working capital', 1300, 6000)]; d['cfo'] = [300, -3000]
d['capex'] = [200, 1500]; d['other'] = [it('Debt repaid', -5000, -100), it('Equity issued', 21000, 0), it('Debt issued', 2000, 10000), it('Investments', -9000, -1000)]
d['change_in_cash'] = [9100, 4400]; w('c05_huge_financing', d)
# CFO negative -> refused
d = copy.deepcopy(cf); d['operating'] = [it('Net loss', -500, 100)]; d['cfo'] = [-500, 100]; d['capex'] = [100, 100]; d['other'] = [it('Equity raised', 800, 0)]
d['change_in_cash'] = [200, 0]; w('c06_negative_cfo', d)
# fcf exactly zero, no other
d = copy.deepcopy(cf); d['capex'] = [1000, 880]; d['other'] = []; d['change_in_cash'] = [0, 0]; w('c07_fcf_zero', d)
# all eight sign combos of CFI/CFF beyond capex & chg sign
d = copy.deepcopy(cf); d['other'] = [it('Asset sale', 900, 0), it('Debt issued', 300, 0)]; d['change_in_cash'] = [1900, 0]; w('c08_inflows_only', d)
d = copy.deepcopy(cf); d['other'] = [it('Acquisition', -2000, 0)]; d['change_in_cash'] = [-1300, 0]; w('c09_drawdown', d)
d = copy.deepcopy(cf); d['capex'] = [1200, 0]; d['other'] = [it('Acquisition', -2000, 0)]; d['change_in_cash'] = [-2200, 0]; w('c10_negfcf_drawdown', d)
d = copy.deepcopy(cf); d['other'].append(it('FX effect', -3, 2)); d['change_in_cash'] = [197, 240]; w('c11_fx_tiny', d)
d = copy.deepcopy(cf); d['operating'] = [it('Net income', 800, 700), it('D&A', 200, 180), it('Deferred revenue', 600, 300), it('SBC', 300, 250), it('Working capital', -900, -550)]
w('c12_saas_deferred_sbc', d)
d = copy.deepcopy(cf); d['operating'][0]['v'] = -200; d['operating'][1]['v'] = 1200; w('c13_netloss_positive_cfo', d)

# ---------------- balance ----------------
bs = base('balance', 'Balco', 'BAL', 'Q3 2026', 'As of Sep 30, 2026')
bs.update(assets=[it('Cash', 100, 90), it('PP&E', 500, 480), it('Other', 400, 380)], total_assets=[1000, 950],
          liabilities=[it('Debt', 300, 300), it('Other liabilities', 200, 190)],
          equity=[it('APIC', 300, 290), it('Retained earnings', 250, 200), it('Treasury stock', -60, -40), it('AOCI', 10, 10)])
w('b01_baseline_default_label', bs)
# Boeing-like: treasury bigger than largest positive item
d = copy.deepcopy(bs); d['equity'] = [it('Common stock', 5, 5), it('APIC', 10000, 9000), it('Retained earnings', 46000, 47000),
     it('Treasury stock', -52000, -52000), it('AOCI', -3000, -3000), it('NCI', 100, 100)]
d['liabilities'] = [it('Debt', 900, 800), it('Other liabilities', -1, 0)]
d['assets'] = [it('Cash', 100, 100), it('Other', 1000, 1000)]; d['total_assets'] = [1100, 1100]
d['liabilities'] = [it('Debt', 0, 0)] + [it('Other liabilities', 1100 - 1105, 0)]
# simpler: make equity sum=1105 -> te positive; liabilities 1100-1105 negative => skip; rebuild clean:
d['equity'] = [it('APIC', 10000, 9000), it('Retained earnings', 46000, 47000), it('Treasury stock', -54000, -54000), it('AOCI', -1500, -1500)]
d['liabilities'] = [it('Debt', 600, 600)]; d['total_assets'] = [1100, 1100]
d['assets'] = [it('Cash', 100, 100), it('Other', 1000, 1000)]
w('b02_treasury_exceeds_largest', d)
# assets != L + E
d = copy.deepcopy(bs); d['liabilities'][0]['v'] = 310; w('b03_unbalanced', d)
# prior doesn't balance - silent?
d = copy.deepcopy(bs); d['liabilities'][0]['p'] = 999; w('b04_prior_unbalanced_silent', d)
# negative asset (accumulated depreciation as separate line)
d = copy.deepcopy(bs); d['assets'] = [it('Cash', 100, 90), it('Gross PP&E', 900, 850), it('Accumulated depreciation', -400, -370), it('Other', 400, 380)]
w('b05_negative_asset_line', d)
# dated comparison
d = copy.deepcopy(bs); d['cmp'] = 'vs Dec 31'; d['prev_label'] = 'Dec 31, 2025'; w('b06_manual_cmp', d)
# equity zero
d = copy.deepcopy(bs); d['equity'] = [it('APIC', 100, 100), it('Deficit', -100, -100)]; d['liabilities'] = [it('Debt', 800, 750), it('Other', 200, 200)]; w('b07_equity_zero', d)
# bank balance sheet (huge, trillions) JPM approx Q3 2025: assets 4.56T
d = copy.deepcopy(bs); d['company'] = 'JPMorgan Chase'; d['ticker'] = 'JPM'
d['assets'] = [it('Cash and deposits with banks', 450000, 400000), it('Securities', 1200000, 1000000), it('Loans, net', 1400000, 1300000), it('Trading assets', 1000000, 900000), it('Other', 510000, 500000)]
d['total_assets'] = [4560000, 4100000]
d['liabilities'] = [it('Deposits', 2550000, 2400000), it('Borrowings and other', 1650000, 1350000)]
d['equity'] = [it("Stockholders' equity", 360000, 350000)]
w('b08_bank_trillions', d)
# deficit: McDonald's-ish negative equity
d = copy.deepcopy(bs); d['equity'] = [it('APIC', 9000, 8900), it('Retained earnings', 67000, 64000), it('Treasury stock', -79000, -77000), it('AOCI', -2500, -2300)]
d['liabilities'] = [it('Debt', 3500, 3500), it('Other', 2000, 1850)]; w('b09_deficit_mcd', d)

# ---------------- holdings ----------------
hd = base('holdings', '', 'ONE', 'Nov 2026', 'As of Nov 18, 2026'); hd['fund'] = 'Single Stock ETF'
hd.update(count=1, sectors=[it('Technology', 100)], holdings=[{'l': 'Nvidia', 'v': 100, 'sector': 'Technology'}]); w('h01_one_holding', hd)
import random; random.seed(1)
secs = ['Technology', 'Health care', 'Financials', 'Industrials', 'Consumer', 'Energy', 'Utilities', 'Materials', 'Real estate', 'Communication', 'Staples']
ws = [random.random() ** 3 for _ in range(500)]; s = sum(ws); ws = [round(100 * x / s, 4) for x in ws]
hl = [{'l': f'Company {i}', 'v': ws[i], 'sector': secs[i % len(secs)]} for i in range(500)]
sv = {x: round(sum(h['v'] for h in hl if h['sector'] == x), 4) for x in secs}
d = copy.deepcopy(hd); d.update(fund='Broad 500 ETF', ticker='B500', count=500, min_weight=0.3, sectors=[it(k, v) for k, v in sv.items()], holdings=hl); w('h02_500_holdings_minw03', d)
d2 = copy.deepcopy(d); d2['min_weight'] = 0; w('h03_500_holdings_minw0', d2)
d = copy.deepcopy(hd); d.update(fund='Long/Short Fund', ticker='LSF', sectors=[it('Technology', 80), it('Cash', 25), it('Short positions', -5)],
     holdings=[{'l': 'Apple', 'v': 30, 'sector': 'Technology'}, {'l': 'Short SPY', 'v': -5, 'sector': 'Short positions'}]); w('h04_short_negative_weights', d)
d = copy.deepcopy(hd); d.update(fund='2x Leveraged', ticker='LEV', sectors=[it('Technology', 200), it('Cash', -100)],
     holdings=[{'l': 'Swap on NDX', 'v': 200, 'sector': 'Technology'}]); w('h05_leveraged_negative_cash', d)
d = copy.deepcopy(hd); d.update(fund='Bad Map', ticker='BAD', sectors=[it('Tech', 100)], holdings=[{'l': 'Apple', 'v': 10, 'sector': 'Technology'}]); w('h06_unknown_sector', d)

# ---------------- segments ----------------
sg = base('segments', 'Segco', 'SEG', 'Q3 2026', 'Jul 1 to Sep 30, 2026')
sg.update(revenue=[1000, 900], operating_income=[150, 120],
          segments=[{'l': 'A', 'revenue': [700, 600], 'operating_income': [200, 150]}, {'l': 'B', 'revenue': [300, 300], 'operating_income': [-20, 0]}],
          corporate=[it('Corporate', -30, -30)])
w('s01_baseline', sg)
d = copy.deepcopy(sg); d['segments'].append({'l': 'New venture', 'revenue': [0, 0], 'operating_income': [-50, -10]}); d['operating_income'] = [100, 110]; w('s02_zero_rev_segment', d)
d = copy.deepcopy(sg); d['segments'][1]['operating_income'] = [0, 0]; d['operating_income'] = [170, 120]; w('s03_segment_oi_zero', d)
d = copy.deepcopy(sg); d['segments'][0]['operating_income'] = [750, 150]; d['operating_income'] = [700, 120]; w('s04_seg_oi_exceeds_rev', d)
d = copy.deepcopy(sg); d['segments'] = [dict(d['segments'][0], revenue=[1100, 1000]), d['segments'][1]]; d['revenue'] = [1300, 1200]
d['other_revenue'] = [it('Intersegment eliminations', -100, -100)]; w('s05_eliminations', d)
d = copy.deepcopy(sg); d['operating_income'] = [-10, 120]; d['corporate'] = [it('Corporate', -190, -30)]; w('s06_total_oploss', d)
