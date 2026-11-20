# Regenerating the gallery

From the repo root:

```bash
S=skills/sankey-financials
OUT=/tmp/sankey-gallery; mkdir -p $OUT
for s in $S/examples/*.json; do n=$(basename $s .json); case $n in synth_*) continue;; esac
  python3 $S/scripts/make.py $s $OUT/$n.cfg.json
  node $S/scripts/test.js $OUT/$n.cfg.json -q
  python3 $S/scripts/build.py $OUT/$n.cfg.json gallery/$n.html --standalone
  python3 $S/scripts/build.py $OUT/$n.cfg.json $OUT/$n.widget.html
  python3 $S/scripts/browser_check.py $OUT/$n.widget.html assets/$n     # needs Playwright
done
```
