# Spec format

A spec is a small JSON file of line items **as the filing reports them**. `scripts/make.py` turns it into
the chart config; all structure, signs and layout decisions are made by the script, not by hand.

Money is in **millions of the reporting currency** (`$ millions` for US filers). Each number can carry a prior-period value: either `[current, prior]` pairs
or `{"l": label, "v": current, "p": prior}` items. Use `null` for an unknown prior.

## Fields every spec has

| Field | Meaning |
|---|---|
| `flow` | `income`, `cashflow`, `balance`, `holdings` or `segments` |
| `company`, `ticker` | Names shown in the title and click-to-ask prompts |
| `period` | Short period name, e.g. `Q3 2026`, `FY2026` |
| `dates` | Subtitle, e.g. `Jul 1 to Sep 30, 2026` |
| `basis` | `GAAP` or `Non-GAAP` |
| `source` | Where the numbers came from (shown under the standalone page) |
| `title` | Optional override of `<TICKER> <period> <flow name>` |
| `currency` | Optional ISO code of the filing's currency, default `USD`. Chart in the currency the company reports in (`EUR` for SAP, `JPY` for Toyota); don't convert. |
| `end`, `prior_end` | End dates of the two columns, e.g. `2026-09-30` and `2025-12-31`. The switch label is derived: 12 months apart gives `Y/Y`, 3 months `Q/Q` (not for balance sheets), anything else `vs Dec 31`. Required for `balance` unless `cmp` is given. |
| `cmp`, `prev_label` | Optional comparison label (default `Y/Y`, `Year ago`), e.g. `vs Jun 30` / `Jun 30` |

Line items may also have `full` (long name for tooltips), `note` (tooltip text) and `group`
(items with the same group are summed into one node named after the group; zero items are dropped).

## income

```json
{"flow":"income", "views":{
   "Product":   {"items":[{"l":"Cloud","v":30709,"p":15157}, ...], "note":"optional caption"},
   "Business":  {"same":"Product", "note":"Reports a single segment, so this matches the product split."},
   "Geography": {"items":[...]}},
 "revenue":[127577,102346], "cogs":[51419,41369],
 "opex":[{"l":"R&D","v":20640,"p":15151}, {"l":"Restructuring gain","v":-2.8,"p":8.7}],
 "operating_income":[40576,31228],
 "nonop":[{"l":"Interest income","v":55,"p":76}, {"l":"Other expense","v":-8221,"p":12759}],
 "tax":[5887,9008], "net_income":[26468,34979],
 "notes":{"net_income":"optional tooltip"}}
```

No cost of revenue (banks, insurers, many service firms): omit `cogs` or set it to `[0, 0]`. The chart then
skips the gross-profit step and revenue flows straight into operating income and operating expenses;
put a bank's provision for credit losses in `opex`. `revenue_label` renames the first box
(e.g. `"Net revenue"`).

Signs: `opex` items are expenses as positive numbers; a **gain** inside opex is negative.
`nonop` items keep the filing's sign: income positive, expense negative. `tax` is positive for an
expense, negative for a benefit. View items must sum to revenue; a negative view item (a hedging loss)
is allowed and drawn as a gray branch off revenue.

Checks: views vs revenue, operating income, net income (each within $1M).
Handled automatically: gains entering mid-chart, an "Interest and other" group when there are 2+
non-operating expenses, tax benefits, and **operating losses** (a red "Operating loss" box feeds
operating expenses; the net loss goes in the subtitle).

## cashflow

```json
{"flow":"cashflow",
 "operating":[{"l":"Net income","v":132175,"p":112010}, {"l":"inventories","group":"Working capital","v":-8905,"p":1400}],
 "cfo":[145097,111482], "capex":[9041,12715],
 "other":[{"l":"Buybacks","v":-86390,"p":-90711}, {"l":"Debt issued","v":4000,"p":0}],
 "change_in_cash":[371,5991]}
```

`operating` items carry the filing's signs and must sum to `cfo`. `other` is every investing and
financing line except capex, signed as filed (outflows negative), plus FX effects if any.
Check: `cfo - capex + sum(other) = change_in_cash`. Negative operating items branch off in gray;
inflows and any cash drawdown feed a "Cash to deploy" box. `capex` is a positive number even though
the filing shows it in parentheses. When capex exceeds operating cash flow, the capex box is fed by all
of operating cash flow plus the pool, and the negative free cash flow goes in the subtitle.
Negative operating cash flow is refused.

## balance

```json
{"flow":"balance", "cmp":"vs Jun 30", "prev_label":"Jun 30",
 "assets":[...], "total_assets":[779403,758376],
 "liabilities":[...], "equity":[{"l":"Retained earnings","v":354795}, {"l":"AOCI","v":-3857}]}
```

Checks: assets sum to `total_assets`, assets = liabilities + equity. Negative components are netted
into the largest positive one in their group (label gets "(net)", tooltip lists what was netted). If
they outweigh it (Boeing's treasury stock), the lines they absorb are merged into one "(net)" box.
**Negative total equity** switches to a deficit layout: assets plus a red "Shareholders' deficit"
flow into total liabilities.

## holdings

```json
{"flow":"holdings", "fund":"Invesco QQQ", "count":104, "aum":461198.6, "min_weight":2,
 "sectors":[{"l":"Technology","v":55}, ...],
 "holdings":[{"l":"Apple","v":8.74,"sector":"Technology"}, ...]}
```

Weights in percent. Sectors must sum to about 100. Holdings at or above `min_weight` are shown
individually; the rest of each sector becomes "Other <sector>". Duplicate names in one sector are
merged (Alphabet's two share classes). Mapping holdings to sectors is a judgment call: say so.

## segments

```json
{"flow":"segments", "revenue":[127577,102346], "operating_income":[40576,31228],
 "segments":[{"l":"Google Cloud","revenue":[30709,15157],"operating_income":[11121,3594]}, ...],
 "other_revenue":[{"l":"Hedging gains","v":194,"p":-207}],
 "corporate":[{"l":"Alphabet-level costs","v":-7849,"note":"..."}]}
```

Intersegment sales (Intel's foundry selling to its product groups) go in
`"eliminations":[{"l":"Intersegment eliminations","v":-6291,"p":null}]`, negative as filed. Segment
boxes stay gross as reported; the subtitle states the eliminated amount; put the eliminations' profit
effect in `corporate`.

Checks: segment revenue + other revenue + eliminations = revenue; segment operating income + corporate items +
other revenue = operating income. Profitable segments split into profit (top) and costs (below);
a loss-making segment's revenue covers its own costs and its loss is drawn as a red outflow from the
profit pool.
