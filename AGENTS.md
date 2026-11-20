# Agent instructions: set up and use sankey-financials

You are a coding agent. A user gave you this repository's link and asked you to set it up. Follow these steps in order. Do not modify anything outside the install locations named here.

## 1. Check requirements

Run `python3 --version` (needs 3.9+) and `node --version` (needs 18+). If either is missing, tell the user and stop. Playwright is optional (browser layout check); do not install it unless the user asks.

## 2. Get the code

Clone the repo (or use the clone you are already in). Do not run any script other than the ones named in this file.

## 3. Install for your environment

The skill lives in `skills/sankey-financials/`. It is a self-contained folder: `SKILL.md`, `scripts/`, `references/`, `examples/`.

- **Claude Code:** copy the folder to `~/.claude/skills/sankey-financials` (user-wide) or `<project>/.claude/skills/sankey-financials` (one project). Or install it as a plugin: `/plugin marketplace add <this repo URL>` then `/plugin install sankey-financials`.
- **Other agents (Codex, Cursor, Gemini CLI, Aider, etc.):** keep the folder anywhere stable and add a pointer to your instruction file (`AGENTS.md`, `.cursorrules`, `GEMINI.md`): "To chart company or fund financials, read `<path>/skills/sankey-financials/SKILL.md` and follow it."
- **No agent integration:** nothing to install. See `docs/without-an-llm.md`.

Ask the user which of these they want if it is not obvious. Do not overwrite an existing `sankey-financials` folder without asking.

## 4. Verify

```bash
cd skills/sankey-financials && ./run_tests.sh
```

Expect `ALL PASSED`. If it prints FAILURES, report the output to the user instead of editing the scripts.

## 5. Tell the user how to use it

Report where you installed it and give them these example prompts:

- "NVDA latest quarter" (income statement Sankey, GAAP)
- "AAPL cash flow Sankey"
- "MSFT balance sheet"
- "What's in QQQ?" (fund holdings)
- "Which Alphabet segment makes the money?" (segment profit)

## How to produce a chart (for later requests)

Follow `skills/sankey-financials/SKILL.md`. In short: find the numbers in a primary source, write a spec JSON per `references/spec-format.md`, then run `make.py`, `test.js` and `build.py --standalone`. If `make.py` reports a SPEC ERROR, the numbers do not reconcile: go back to the filing. Never hand-write chart code.
