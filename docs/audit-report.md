# sankey-financials: adversarial audit

Branch `claude/audit-break-it-79eefb`, November 20, 2026. Nothing has been pushed or merged.

## Summary

I tried to break the skill with 78 hand-built specs, plus the 10 specs from the first pass. They cover all
five chart types, many industries and points in time, and bad or hostile input. I ran every spec through
the full pipeline (`make.py`, `test.js`, `build.py --standalone`, `browser_check.py`) and looked at the
rendered charts, not just the exit codes. I also probed dark mode, phone width, keyboard use, printing
and the clipboard.

**What I found:** 19 bugs, 9 limitations and 8 UX nits. The worst problems are the ones where the
skill **draws a wrong chart without any warning**:

1. **Prior-year figures were never checked.** Only the current-period numbers were reconciled. A
   mistyped prior figure went straight into every Y/Y percentage.
2. **Every chart said USD and "$".** A SAP chart in euros or a Toyota chart in yen was labelled as
   US dollars ("$48.04T · USD").
3. **When capex was larger than operating cash flow, the capex box showed the wrong amount and the
   wrong Y/Y.** For example, $1.5B of capex (+150%) was drawn as "$1.00B, +66.7%". The same defect
   was in the Boeing 9-month chart.
4. **Balance sheets compared with Dec 31 were labelled "Y/Y".**
5. **A label or title containing HTML ran as code** in the generated page. Copying text from a
   hostile web page into a spec would be enough to trigger it.

**What I fixed:** 14 commits on the branch prototype fixes for all 19 bugs and for the 7 known gaps.
`./run_tests.sh` prints ALL PASSED. There are 19 new regression examples (8 of them are bad specs that
must be refused, and each must be refused with the expected message). Each fix is its own commit, so
you can take or leave each one (list in section 3).

**Not fixed:** the limitations are listed in section 4. For each one the skill refuses with a clear
message, so none of them can produce a wrong chart. The open design questions are in section 5.

### Words used below

- **Silent wrong output**: the chart is drawn and looks fine, but a number or label on it is wrong.
  This is the worst kind of failure.
- **Loud refusal**: `make.py` stops with a `SPEC ERROR` that says what is wrong. This is acceptable.
- **Crash**: a Python traceback or a broken page. This is not acceptable, but at least the user sees it.
- **Prior / comparison column**: the second number in each `[current, prior]` pair. It drives the
  Y/Y figures.

## 1. Test matrix

The spec files are in `docs/audit-specs/matrix/` (my cases) and `docs/audit-specs/first-pass/` (the
first pass). `docs/audit-specs/tools/` has the generator (`gen.py`), the pipeline runner (`run.py`) and
the UI probe (`ui.py`). `docs/audit-specs/results-after-fixes.txt` has the final run, one line per spec.

**Before** is the original skill (`main`) and **After** is this branch.
Results: **pass** means the chart was drawn and is correct. **refused** means a clear SPEC ERROR.
**FAIL** means a crash, a test.js error, or a wrong chart. **SILENT** means the chart was drawn, but
something on it is wrong.

Figures marked *approx* are public figures I recalled and rounded. They are realistic but not
verified, so use them only as test data. All other figures are synthetic.

| # | Company / period | Flow | Scenario | Before | After | Severity |
|---|---|---|---|---|---|---|
| i01 | Testco Q2 | income | Baseline | pass | pass | – |
| i02 | Testco Q2 | income | One opex prior mistyped (implied OI prior 290, reported 190) | **SILENT** (wrong Y/Y) | refused | high |
| i03 | Testco Q2 | income | Product-view priors don't sum to prior revenue | **SILENT** | refused | high |
| i04 | Testco Q2 | income | No operating_income / net_income given, R&D mistyped | **SILENT** (nothing checked) | refused (totals required) | high |
| i05 | JPM Q3 2025 *approx* | income | Bank, COGS = 0 | FAIL (test.js; browser said OK) | pass, no gross-profit step | high |
| i06 | JPM Q3 2025 *approx* | income | Bank, `cogs` key omitted | FAIL (KeyError traceback) | pass | med |
| i07 | Biotech, Q1 | income | Zero revenue | refused, message said "Gross loss" | refused, clear message | low |
| i08 | Biotech, Q1 | income | $5M revenue, $145M operating loss, no COGS | FAIL (10,000px tall, empty COGS box) | pass, 556px | med |
| i09 | Testco | income | Negative revenue | refused ("Gross loss", misleading) | refused, clear | low |
| i10 | Testco | income | Tax above pretax income (net loss with operating profit) | FAIL (test.js) | refused, clear | med |
| i11 | Testco | income | Profit-to-loss flip from a big non-operating impairment | refused | refused | limitation |
| i12 | Testco | income | Loss-to-profit flip | pass | pass | – |
| i13 | Testco | income | Profit-to-operating-loss flip | pass | pass | – |
| i14 | Walmart FY2025 *approx* | income | Non-controlling interest | **SILENT** (ends at consolidated NI) | pass with `after_tax` | high |
| i15 | Testco | income | Discontinued ops put in nonop | **SILENT** (drawn as pretax, taxed) | pass with `after_tax` | med |
| i16 | SAP FY2024 *approx* | income | IFRS, EUR | **SILENT** ("$", "USD") | pass, "€", "EUR" | high |
| i17 | Toyota FY2025 *approx* | income | 20-F, JPY, ¥48 trillion revenue | **SILENT** ("$48.04T · USD") | pass, "¥48.04T · JPY" | high |
| i18 | Microcap Q1 | income | $850K revenue; net income wrong by $0.8M | **SILENT** (inside the $1M tolerance), "$0.8M" labels | refused; "$850K" labels | med |
| i19 | Testco | income | 30 opex lines | pass (1,889px tall, warned) | same | nit |
| i20 | Testco | income | 100-character labels, Japanese, emoji | FAIL: chart drawn **mirrored** (revenue on the right) | pass, labels wrap | med |
| i21 | Testco | income | `<script>`, `</script>`, `onerror` in title, labels, notes, source | **FAIL: code ran** (9 alert() dialogs), chart blank | pass, shown as text | high |
| i22 | Testco | income | `"1,200"` as a number | FAIL (traceback) | refused, clear | low |
| i23–24 | Testco | income | NaN as value or prior | FAIL (invalid JSON crashed test.js; browser said OK) | refused | low |
| i25 | Testco | income | Missing ticker | FAIL (KeyError traceback) | refused, clear | low |
| i26 | Testco | income | `"flow":"Income"` | refused | refused | – |
| i27 | Testco | income | Duplicate labels, zero lines with non-zero priors | **SILENT** (prior lost) | refused (priors inconsistent) | med |
| i28 | Zero | income | Every number zero | refused ("Gross loss") | refused, clear | low |
| i29 | Testco | income | Scalars and 1-element pairs | pass | pass | – |
| i30 | Testco | income | `"same"` names a view that doesn't exist | FAIL (page errors) | refused | low |
| i31 | Testco | income | Single-item view | pass | pass | – |
| i32 | Testco | income | Operating gain in a loss quarter | refused | refused | limitation |
| i33 | Testco Q2 vs Q1 | income | Sequential comparison | **SILENT** (said "Y/Y") | pass, "Q/Q" via dates | med |
| i34 | Testco | income | First quarter after IPO, no priors | pass (switch hidden) | pass | – |
| i35 | Testco FY (53 wk) | income | 53-week year | pass | pass | – |
| i36 | Testco | income | Equity-method income, after tax, put in nonop | **SILENT** (drawn as pretax) | pass via `after_tax` | med |
| c01 | Cashco FY | cashflow | Baseline | pass | pass | – |
| c02 | Cashco | cashflow | Capex entered negative "as filed" | refused, pointed at change in cash | refused, names capex sign | med |
| c03 | Cashco | cashflow | Capex zero | FAIL (test.js; browser OK) | pass | med |
| c04 | Cashco | cashflow | Capex $1.5B > CFO $1.0B | **SILENT** ("$1.00B, +66.7%") | pass ("$1.50B, +150%") | high |
| c05 | Cashco | cashflow | Financing 70× CFO | FAIL (27,700px tall) | pass, 700px | high |
| c06 | Cashco | cashflow | Negative CFO | refused | refused | limitation |
| c07 | Cashco | cashflow | FCF exactly zero | FAIL (test.js) | pass | low |
| c08–c10 | Cashco | cashflow | Inflows only / drawdown / negative FCF + drawdown | pass | pass | – |
| c11 | Cashco | cashflow | Tiny FX line | pass | refused: my prior change_in_cash was off by 2 (correct catch) | – |
| c12 | SaaS | cashflow | Deferred revenue, SBC, working capital | pass | pass | – |
| c13 | Cashco | cashflow | Net loss, positive CFO | pass | pass | – |
| b01 | Balco Q3 | balance | 10-Q, no comparison label given | **SILENT** (said "Y/Y" vs Dec 31) | dates required; "vs Dec 31" | high |
| b02 | Balco | balance | Treasury stock larger than any equity line | FAIL (test.js; browser OK) | pass, lines merged | high |
| b03 | Balco | balance | Assets ≠ L + E | refused | refused | – |
| b04 | Balco | balance | Prior column doesn't balance | **SILENT** | refused | high |
| b05 | Balco | balance | Negative asset line (accumulated depreciation) | pass | pass | – |
| b06 | Balco | balance | Manual cmp label | pass | pass | – |
| b07 | Balco | balance | Total equity exactly zero | FAIL (test.js) | pass | low |
| b08 | JPM *approx* | balance | $4.56 trillion bank | pass | pass | – |
| b09 | McDonald's-like | balance | Negative equity (deficit layout) | pass (after I fixed my spec) | pass | – |
| h01 | Single-stock ETF | holdings | One holding | pass | pass | – |
| h02 | 500-stock ETF | holdings | min_weight 0.3 | pass, 5,930px tall (warned) | same | limitation |
| h03 | 500-stock ETF | holdings | min_weight 0 (some weights round to 0) | FAIL (56 errors), 19,000px | pass, 18,000px (warned) | limitation |
| h04 | Long/short fund | holdings | Short positions, negative sector | refused, confusing message | same | limitation |
| h05 | 2× leveraged ETF | holdings | 200% exposure, −100% cash | refused, confusing message | same | limitation |
| h06 | Bad map | holdings | Holding maps to an unknown sector | refused | refused | – |
| s01 | Segco Q3 | segments | Baseline, one loss-making segment | pass | pass | – |
| s02 | Segco | segments | Pre-revenue segment with a loss | FAIL (test.js) | pass | med |
| s03 | Segco | segments | Segment OI exactly zero | FAIL (test.js) | pass | low |
| s04 | Segco | segments | Segment OI above its revenue | FAIL (test.js) | refused, clear | low |
| s05/s07 | Intel-like Q3 | segments | Intersegment eliminations | refused / FAIL | pass with `eliminations` | high |
| s06 | Segco | segments | Total operating loss | refused | refused | limitation |
| 1a–1c | JPM (first pass) | income | Bank views and COGS = 0 | refused / FAIL | refused (spec) / pass | – |
| 2 | Walmart (first pass) | income | NCI | SILENT | pass (as before; now expressible) | – |
| 3, 3b | Boeing (first pass) | balance | Treasury netting | FAIL / pass | pass / pass | – |
| 4 | Boeing 9M (first pass) | cashflow | Capex > CFO, huge financing | **SILENT** + 2,100px | pass, 800px, correct capex | – |
| 5 | Amazon (first pass) | segments | Baseline | pass | pass | – |
| 6, 6b | Intel (first pass) | segments | Eliminations | refused / FAIL | refused, names the `eliminations` field | – |

**UI probes** (a standalone chart in headless Chromium, plus one chart opened in the in-app browser):

| Area | Finding | Severity |
|---|---|---|
| Dark mode | Renders correctly; text and colors adapt. | – |
| Phone (375px wide) | The chart scales down to fit, so 12px labels become about **5.4px**. That is unreadable. Tapping a box shows no tooltip. | nit (high reach) |
| Keyboard | Only the Y/Y switch can be reached with Tab. Boxes can't get focus, so tooltips and click-to-ask need a mouse. The tabs have no `role="tab"` or `aria-selected`. The only text alternative is the title. | nit (accessibility) |
| Contrast | Value labels on the light background: green 2.7:1, orange 3.1:1, blue 4.3:1. WCAG AA asks for 4.5:1. In dark mode, green and orange pass and blue is 4.1:1. | nit |
| Print | No print stylesheet. A printout captures whatever is on screen: the hover highlight, an open tooltip, the "copied" toast and the controls. | nit |
| Clipboard | The standalone page always said "Question copied", even when the copy failed. **Fixed:** if the copy fails, it now shows the question to copy by hand. | nit |
| Y/Y label | The label was set by hand. **Fixed:** it is now derived from the dates (see G5). | – |

## 2. Ranked gaps

The order is how likely a real user is to hit the problem, then how bad it is. Silent wrong output
comes first. **Status** gives the commit with the prototype fix.

| Rank | Gap | Type | Repro specs | Status |
|---|---|---|---|---|
| G1 | Prior-period figures never reconciled | bug, silent | i02, i03, b04, i27 | fixed `82c3577` |
| G2 | Lines that are zero now lost their prior, so prior totals and their Y/Y were wrong | bug, silent | examples/aapl_cash ("Debt issued" 0 vs 4,481), i27 | fixed `82c3577` |
| G3 | Currency always "$"/"USD" | bug, silent | i16, i17 | fixed `a41c3e6` |
| G4 | Capex capped at CFO: wrong value and wrong Y/Y | bug, silent | c04, first-pass/4 | fixed `5ecac87` |
| G5 | Comparison label defaults to Y/Y (balance vs Dec 31, Q/Q income) *(known e)* | bug, silent | b01, i33 | fixed `509e2b3` |
| G6 | Totals optional, so nothing was checked | bug, silent | i04 | fixed `82c3577` |
| G7 | After-tax items drawn as pretax; no NCI step *(known d)* | bug, silent | i14, i15, i36 | fixed `4482839` |
| G8 | Flat $1M tolerance, so small companies were effectively unchecked | bug, silent | i18 | fixed `82c3577` |
| G9 | Code injection: title, source, summary unescaped; `</script>` in a label breaks out | bug, security | i21 | fixed `1a623b8` |
| G10 | Huge charts when one column dwarfs the hub *(known f)* | bug, unusable | c05, i08, first-pass/4 | fixed `ffc3886` |
| G11 | Bank / no-COGS income: fake "Gross profit", empty "Cost of revenue", test.js error *(known c)* | bug | i05, i06, i08 | fixed `4bf8d6d` |
| G12 | make.py accepts charts it can't draw, so test.js fails with cryptic messages | bug | c03, c07, b07, s02, s03, s04, i10, h03 | fixed `0665020` |
| G13 | Balance netting turns a line negative *(known a)* | bug | b02, first-pass/3 | fixed `dff3fd1` |
| G14 | browser_check says OK for charts test.js rejects *(known g)* | bug (tooling) | i05, c03 | fixed `5acb064` |
| G15 | Segment eliminations can't be expressed *(known b)* | bug | s05, s07, first-pass/6 | fixed `4cda577` |
| G16 | Long label mirrors the whole chart | bug | i20 | fixed `ffc3886`, `d3ed7d5` |
| G17 | Capex entered negative, as filed, gives a misleading error | bug, loud | c02 | fixed `4ce82e8` |
| G18 | Tracebacks or invalid JSON for missing fields, `"1,200"`, NaN; bad `same` reference | bug, loud | i06, i22–i25, i30 | fixed `0665020` |
| G19 | Misleading "Gross loss" message for zero or negative revenue | bug, loud | i07, i09, i28 | fixed `0665020` |
| L1 | Pretax loss despite operating profit (big impairment or debt loss) | limitation | i11 | not fixed, recommended next |
| L2 | Negative operating cash flow (growth companies, biotech) | limitation | c06 | not fixed, recommended next |
| L3 | Net loss from tax above pretax income (valuation allowance) | limitation | i10 | not fixed |
| L4 | Gross loss (early EV makers) | limitation | – | not fixed |
| L5 | Zero-revenue company | limitation | i07 | not fixed |
| L6 | Total operating loss in the segment view | limitation | s06 | not fixed |
| L7 | Operating gain in a loss quarter | limitation | i32 | not fixed |
| L8 | Short, leveraged, negative-weight funds; the message is confusing ("total 0.00% but the sector is -5.00%") | limitation | h04, h05 | not fixed |
| L9 | Hundreds of named holdings, 6,000–18,000px tall, only a warning | limitation | h02, h03 | not fixed |
| N1–N8 | Phone width, keyboard, contrast, print, subtitle width, duplicate adjacent boxes, "$ millions" in one error message, long merged equity label | nits | UI probes | not fixed (one fixed: clipboard toast) |

## 3. Root cause and fix for each gap

Each fix is one commit on `claude/audit-break-it-79eefb`, oldest first.

**G9: code injection (`1a623b8`).** `build.py` pasted the title, source and summary into the HTML as
they were. `json.dumps` also left `</script>` inside label strings, and the browser treats that as the
end of the script, so the rest of the data is parsed as HTML. *Fix:* `html.escape` the three text values,
and write `<\/` for `</` in the embedded data. The data stays the same string in JavaScript. Verified:
the old build opened 9 alert() dialogs and drew an empty chart; the new build opens none and draws the
full chart. The same commit makes the "Question copied" toast honest. Regression:
`examples/synth_xss_labels.json`.

**G14: browser_check passed broken charts (`5acb064`).** browser_check only measured label overlaps.
It never checked the numbers. *Fix:* it now pulls the chart data out of the page and runs `test.js` on
it. It also reports pages that open dialogs, or that draw no boxes, instead of crashing with
IndexError.

**G12, G18, G19: make.py let undrawable charts through (`0665020`).** make.py built boxes with
value 0 or below and relied on test.js to complain, in test.js terms ("cogs value 0 must be positive;
restructure"). *Fix:* make.py now drops zero-value boxes. A zero capex or zero-weight holding simply
disappears. Then it checks every box: if a box is negative or doesn't balance, make.py refuses and
names the line, with a hint (for example, "Net income is negative although pretax income is positive
(tax above pretax income)"). The same commit adds friendly errors for missing fields, wrong types,
NaN and a bad `same` reference. It also adds a clear zero-revenue message. In `run_tests.sh`, a
`synth_bad_*` spec can now name an `expect_error` text, and the refusal must contain it. Five new
`synth_bad_*` examples and `synth_cash_zero_capex.json`.

**G1, G2, G6, G8: reconciliation (`82c3577`).**
- *G1:* each `check()` compared the current column only. *Fix:* every check now also runs on the
  prior column whenever the priors are present. Restated priors are fine: the check uses whatever
  numbers the spec gives.
- *G2:* `grouped()` drops lines whose current value is 0, and their prior went with them. So when a
  one-off charge was 0 this year but not last year, operating income's prior was wrong, and so was its
  Y/Y. The new check found this in the shipped `aapl_cash` example: "Debt issued" is 0 now and 4,481 a
  year ago. That example's chart was not affected, because the box involved shows no Y/Y. *Fix:* prior
  totals are now summed from the raw lines.
- *G6:* `operating_income`/`net_income`, `total_assets`, and segment `revenue`/`operating_income` are
  now required.
- *G8:* the tolerance is $1M when the statement's largest figure is about $200M or more. Below that it
  shrinks with the figures, down to $5K.

Two synthetic examples needed the newly required totals added. Regressions:
`synth_bad_prior_mismatch`, `synth_bad_tiny_company`.

**G3: currency (`a41c3e6`).** The subtitle had "USD" hardcoded, and the number formatter had "$"
hardcoded. *Fix:* a new optional field, `currency` (ISO code). It sets the symbol for 17 common
currencies, and for any other code it uses the code itself. The same commit shows amounts below 1M as
"$850K" (before: "$0.8M"). Regression: `synth_eur_income.json`.

**G4: capex (`5ecac87`).** When FCF was negative, the capex box was cut down to the size of operating
cash flow, but its prior was the full prior-year capex. *Fix:* when capex is larger than operating
cash flow, it is one box with the true amount. All of operating cash flow and the "Cash to deploy"
pool both flow into it. The negative FCF goes in the subtitle; the red "shortfall" box is gone.
Covered by the existing `synth_cash_negfcf` example.

**G17: capex sign (`4ce82e8`).** A targeted refusal for negative capex. Regression:
`synth_bad_capex_sign`.

**G10, G16: layout (`ffc3886`, `d3ed7d5`).**
- *G10:* link widths were scaled to the hub box. *Fix:* they are now scaled to the tallest column.
  Charts whose hub is already the tallest column don't change. In the existing examples, heights moved
  by −376 to +30px.
- *G16:* left and right labels never wrapped. One long label pushed the first column to the right of
  the last one, and the whole chart was drawn backwards. *Fix:* these labels now wrap at 160px. CJK
  characters and emoji now count as full width.

Regressions: `synth_cash_huge_financing`, `synth_income_tiny_revenue_big_loss`,
`synth_long_unicode_labels`.

**G5: comparison label (`509e2b3`).** New optional fields, `end` and `prior_end`. The label is
derived from them:

| Dates are | Label |
|---|---|
| 12 months apart | "Y/Y" |
| 3 months apart | "Q/Q" (not for balance sheets) |
| Anything else | "vs Dec 31", with "Dec 31, 2025" in tooltips |

A balance sheet without dates or an explicit `cmp` is now refused. Regression:
`synth_balance_vs_dec31.json`.

**G11: no COGS (`4bf8d6d`).** *Fix:* `cogs` is now optional. If it is absent or zero, the gross-profit
column is skipped and revenue flows straight to operating income and operating expenses.
`revenue_label` can rename the first box. Regression: `synth_bank_no_cogs.json`.

**G13: balance netting (`dff3fd1`).** *Fix:* negatives first absorb the largest positive line, then
the next one. If more than one line is used up, those lines become one box, for example "Additional
paid-in capital and Retained earnings (net)", and its tooltip shows the breakdown. Then no single line
is shown with a misleading net figure. Regression: `synth_balance_treasury_spill.json`.

**G15: eliminations (`4cda577`).** *Fix:* a new `eliminations` list, entered as negative numbers. It
counts in the revenue check but not in operating income. The segment boxes stay gross, as the filing
shows them, and the subtitle says "Segments before $6.29B of intersegment eliminations". Regression:
`synth_segments_eliminations.json`.

**G7: after-tax lines (`4482839`).** *Fix:* a new `after_tax` list, signed as filed. The chart now
goes from "Consolidated net income" to "Net income to shareholders" (`net_income_label` can rename it).
The minority share and losses branch off; gains join. Regression: `synth_income_after_tax.json`.

## 4. Not fixed, and why

- **L1 pretax loss with operating profit, L2 negative operating cash flow.** Real users will hit
  these. Examples: a large impairment, a loss on debt extinguishment, any growth-stage or biotech cash
  flow. Each needs a new layout (a red "pretax loss" box fed from the left, as the operating-loss case
  already has; a "cash burned" source for cash flow). These are design work, not bug fixes. I recommend
  doing them next. The refusals are honest meanwhile.
- **L3–L7** are rarer. They refuse clearly, and the reply can describe the numbers in text.
- **L8 short, leveraged and negative-weight funds.** A Sankey can't draw negative weights honestly
  without a separate design. The message should at least say "short or negative positions are not
  supported" (a one-line change).
- **L9 hundreds of holdings.** A cap on named holdings (for example the top 25, with the rest in
  "Other") is easy, but it changes the chart. Your call.
- **N1 phone width.** A real fix is a different layout under about 500px, for example a stacked list
  or a horizontal scroll with a minimum width. That is a design decision, not a patch.
- **N2–N3 keyboard and contrast.** Fixable: `tabindex` and `role` on boxes, focus tooltips, and darker
  label shades on light backgrounds. But they change the look and the interaction. I listed them rather
  than changing the visual design without your input.
- **N4 subtitle width** is not checked by test.js. A very long `dates` text could be clipped.
  **N5** shows "Operating income" and "Pretax income" as two identical boxes when there are no
  non-operating items. Both are cosmetic.
- I did not add holdings fixes or the redesigns above because the task asked for minimal fixes, and
  each changes what users see.

## 5. Open questions for Kevin

1. **Bank labels.** With no cost of revenue, the chart now reads Net revenue → Operating income →
   Pretax income → Net income, with "Provision for credit losses" as an operating expense. Is
   "Operating income" right for a bank? The alternative is "Pre-provision profit", which needs
   provisions as their own step. And should `revenue_label` default to "Net revenue" for banks?
2. **Balance sheets merged by netting.** Boeing now shows "Additional paid-in capital and Retained
   earnings (net) $1.48B". The alternatives are a plain "Equity components (net)" label, or no equity
   breakdown at all when the netting spills over. Which do you prefer?
3. **Required fields.** Totals are now required, and so are balance-sheet dates. This is stricter than
   before: old specs without them will be refused. Is that the right trade, or should a missing total
   be a warning?
4. **Currency.** I chart in the reporting currency and do not convert. Should the reply also give a
   USD equivalent, or should conversion be an option?
5. **Negative FCF.** The red "Free cash flow shortfall" box is replaced by one honest capex box, with
   the negative FCF in the subtitle. Do you want the red box kept as well?
6. **Phone users.** Is a phone layout worth building? Today a phone gets an unreadable chart.
7. **Tolerance.** $1M, shrinking with the figures for companies below about $200M. Some companies
   that report in $ millions and have about $50M of revenue may now get rounding refusals. Is that
   acceptable?
