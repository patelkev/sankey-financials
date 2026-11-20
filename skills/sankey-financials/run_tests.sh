#!/usr/bin/env bash
# Regression suite: every spec in examples/ must generate, pass static checks and (if Playwright
# is installed) pass the browser check. synth_bad* specs must be refused.
cd "$(dirname "$0")"; OUT=${OUT:-/tmp/sankey-financials-tests}; mkdir -p "$OUT"; fail=0
have_pw=$(python3 -c "import playwright" 2>/dev/null && echo 1 || echo 0)
[[ $have_pw == 1 ]] || echo "(Playwright not installed: skipping browser checks)"
for s in examples/*.json; do
  n=$(basename "$s" .json); printf '%-22s ' "$n"
  if ! python3 scripts/make.py "$s" "$OUT/$n.cfg.json" >/dev/null 2>"$OUT/$n.err"; then
    if [[ $n == synth_bad* ]]; then echo "refused as expected"; continue; fi
    echo "FAIL"; cat "$OUT/$n.err"; fail=1; continue
  fi
  [[ $n == synth_bad* ]] && { echo "FAIL (bad spec was accepted)"; fail=1; continue; }
  r=$(node scripts/test.js "$OUT/$n.cfg.json" -q) || { echo "FAIL"; echo "$r"; fail=1; continue; }
  python3 scripts/build.py "$OUT/$n.cfg.json" "$OUT/$n.html" >/dev/null
  if [[ $have_pw == 1 ]]; then
    b=$(python3 scripts/browser_check.py "$OUT/$n.html" "$OUT/$n" 2>&1) || { echo "FAIL"; echo "$b"; fail=1; continue; }
  fi
  echo "ok"
done
[[ $fail == 0 ]] && echo "ALL PASSED (screenshots in $OUT)" || echo "FAILURES ABOVE"; exit $fail
