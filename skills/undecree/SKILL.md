---
name: undecree
description: Finds "dogmas" in agent config — one-off comments fossilized into absolute rules ("never use Opus", "only reply in 6 words") with no scope, reason or exception — across Claude Code, Codex, Cursor, Windsurf, Gemini, Devin, OpenCode and project CLAUDE.md/AGENTS.md files, then opens a review page where the user keeps, rewrites or deletes each one. Use when an agent refuses something it used to do, when asked to audit or clean agent rules, memory or harness config, or on "quita esa regla", "limpia mis dogmas", "por qué no usas X", "why won't you use X", "eso ya no aplica", "undecree".
---

# undecree

![mark](assets/mark.svg)

A **dogma** is an absolute directive that lost its context: a one-off comment ("I'm low on credits", "just run this overnight", "I'm tired") saved as a permanent rule. Agents then enforce it forever.

Workflow: **scan → triage with your own judgment → review page → apply what the user marks.** The user gets the final say on every item; your job is to do the reading so they only decide.

Brand (mark, palette, voice): [assets/BRAND.md](assets/BRAND.md). Don't restyle the page, and don't add copy it doesn't need.

## Health check

A directive should carry three things. Missing any is a red flag:

| Element | Looks like |
|---|---|
| Scope | "for subagents", "in this repo", "when X" |
| Reason + date | "(user cost limit, 2026-10-22)" |
| Exception / revisit | "unless the user asks", "revisit when Y" |

- **healthy** — all three. Goes in `clean`, never gets a card.
- **under-scoped** — a real rule that reads as absolute. Add the exception.
- **fossil** — a one-off generalized into a ban. Rewrite with scope, or delete.
- **stale** — was scoped, but the world changed (lost access, switched tools). Confirm with the user.

## Step 1 — scan

```bash
python3 -I <skill-dir>/scripts/find_dogmas.py [--project PATH]... [--json] [--top N] [--all] [--verbose] [--unflagged | --unflagged-all] [--include-skills] [--all-tiers]
```

Covers `~/.claude`, `.codex`, `.cursor`, `.codeium`, `.gemini`, `.hermes`, `.grok`, `.commandcode`, `.qwen`, `.kiro`, `.continue`, `.roo`, Cline, Goose, Amp, `.config/devin`, `.config/opencode`, `.agents`, plus a project sweep of `$HOME` (depth 4). The first line of the report lists the harnesses it found. **If the user runs an agent that is not in that list, look for where it keeps rules or memory (`ls -a ~`, `~/.config`) and run the scanner on it with `--project PATH`, then add it to `HARNESS_TARGETS`.** Output is ranked by a suspicion score:

- Global config is listed best first, **one entry per rule**: the same rule restated in other files (a small cluster), or several hits inside one memory file, collapse into the best line with the rest listed under it. `--top N` caps the list (default 40, `0` = all), `--all` turns the collapsing off, `--json` always has every line. Project rule files are summarized per file (`--verbose` for every line).
- `signals` say why a line was flagged: `ban` (never / don't / avoid / prohibido), `absolute` (always / only / must / limits like "under 20 words"), `temporal` (the rule carries its origin: "for now", "I'm tired", "credits are low", "no longer").
- `!!` = absolute with no exception in its own lines. `[N]` = score. Global config, model/cost words, no exception, short lines and old dates raise it. Descriptive text ("The server never restarts") and lasting reasons (security, policy, CI) lower it.
- `cluster#N` = the same rule restated in several files. Fix them as one item. A cluster of more than 6 lines is several rules chained together by shared words, so it is not tagged or collapsed.
- `memory:feedback|user|reference|project` is the memory file's own `type`. `user` and `reference` memories are facts, so they rank lower; `feedback` ranks higher. A `**Why:**` line explains a rule written elsewhere in the file, so it ranks lower than the rule.
- Flags come from the line and its continuation lines, not the whole file. They are hints, not verdicts.

**The patterns are a ranking aid, not a guarantee.** On phrasing they had never seen, they caught about two thirds of the dogmas (see Evals). So global config is never judged from the pattern hits alone:

- Read `~/.claude/CLAUDE.md`, `AGENTS.md`, `GEMINI.md` and each `MEMORY.md` index whole. They are short.
- Run with `--unflagged` to list the lines in those files that no pattern matched ("Speak like a pirate."). It also holds the lines the scanner judged to be plain facts ("The cron never runs on weekends.") and the file's preamble, which are kept out of the ranked list. `--unflagged-all` adds memory bodies.
- Project rule files have no such safety net. Only tier-1 hits and risky topics are shown there.

## Step 2 — triage (your judgment)

Open the top candidates and read around them; memory files are small, read them whole. Then pick what goes to review:

- Include plausible fossils / under-scoped / stale rules from global config (CLAUDE.md, AGENTS.md, memory files, rules dirs, agent defs that pin a model).
- Skip authored task prompts (`*/agents/*`, SKILL.md bodies, plugin files) unless they pin a model or ban a tool the user might want.
- **One card per rule, not per file.** An index line, a memory description and the CLAUDE.md line for the same rule are ONE item; the canonical file is `file`, the rest go in `also`.
- Project rule files: at most a few cards for likely fossils, or one `verdict:"file"` item. Never dump hundreds of lines.
- **Keep the page short.** Aim for 12 cards or fewer. If more, take the 12 worst and say how many you left.
- Healthy rules go in `clean` (or leave them out). A `healthy` item is folded into `clean` automatically.
- Write `proposal` for every card you suggest rewriting; the user edits it in place. Write `context` as **one sentence**: why it's a problem. No file inventories, no restating the rule.

Write `items.json`, render and open:

```bash
python3 <skill-dir>/scripts/make_review.py items.json -o review.html --open
```

Then tell the user to mark each card and paste back the copied JSON. **End your turn there; don't edit anything yet.**

## items.json

```json
{
  "title": "2026-11-24",
  "lang": "es",
  "items": [
    {
      "file": "~/.claude/CLAUDE.md",
      "line": 7,
      "rule": "- Do not use Claude Opus for council, sol-loop, or any other subagent. This is a cost limit.",
      "context": "A low-credits comment turned into a universal ban with no exception.",
      "verdict": "fossil",
      "suggested": "rescope",
      "proposal": "- Default to Sonnet/Haiku for subagents — user cost limit, 2026-10-22.\n  Exception: use Opus when the user explicitly asks for it or names it.",
      "also": [{"file": "~/.claude/projects/x/memory/MEMORY.md", "line": 6, "proposal": "optional per-file rewrite"}]
    }
  ],
  "clean": [{"file": "~/.claude/CLAUDE.md", "line": 5, "rule": "the line as written", "note": "why it is fine"}]
}
```

- `verdict`: `fossil` | `under-scoped` | `stale` | `file`
- `suggested`: `keep` | `rescope` | `delete` | `review`. Marked "sugerido" on the card. The user still has to choose, or hit "Aceptar sugeridos".
- `lang`: `es` or `en`. Match the user's language. Defaults to `$LANG`.
- `id` is optional (auto-numbered); `line`, `context`, `proposal`, `also` are optional.
- `outcome` (optional): what happens in practice if the rule is deleted. Shown on the card as "Si lo borras". Write it for every card.
- `clean` is shown collapsed as "Revisadas, sin problema". Give each entry a real path and `line`, the rule as written in `rule`, and in `note` why it is fine (scope, reason, date, exception). The user must be able to tell where each came from. Entries that are not rules (empty files, task prompts) get a `note` and no `rule`.

## Step 3 — apply

The user pastes `{ "decisions": [...] }`. Per decision:

| action | do |
|---|---|
| `keep` | nothing |
| `rescope` | write `text` (the user may have edited the proposal); apply to `file` and adapt it for each `also` file, honoring its own format |
| `delete` | remove the line. For a memory file, also remove its `MEMORY.md` index line; for a whole-file item, delete the file |
| `review` | investigate now and report back; change nothing yet |
| `pending` | the user skipped it; leave it alone |

A non-empty `comment` is context from the user. Read it before acting. Show a short diff, then re-run the scanner on the touched files to confirm the rule no longer reads as absolute.

Rescope template:

```
- <default behavior>: <what to do> (<reason>, <date>).
  Exception: <when it lifts, e.g. "when the user explicitly asks for X">.
```

In memory files keep the `**Why:**` / `**How to apply:**` structure and update the frontmatter `description` and the `MEMORY.md` index line. Those load first, and they are where a stale "never" does the damage even when the body has an exception.

## Prevention — rules that don't fossilize

Before saving anything to memory / CLAUDE.md / rules:

1. One-off? ("tonight", "I'm tired", "low on credits") → don't save it, or save it with an expiry.
2. Preference or fact? → save with scope: "prefers X when Y".
3. Always record what, why, date, and when it stops applying.

Bad: `Never use Opus.`
Good: `Default to Sonnet/Haiku for subagents — user cost limit, 2026-10-22. Opus allowed when the user names it.`

## Notes

- The harness map lives in `scripts/find_dogmas.py` (`HARNESS_TARGETS`, `SKILLS_TARGETS`, `PROJECT_FILES`, `PROJECT_DOTDIRS`, `CONFIG_SUBDIRS`). Add paths there for new harnesses.
- Both scripts are stdlib-only Python 3 and use `Path.home()`. The page is a single HTML file: no server. It works offline (Figtree is optional and falls back to system fonts). State lives in `localStorage`.
- The page has two views, switched at the top right and remembered per browser. **Lista** shows every card. **Tarjetas** is one card at a time, Tinder style: left = delete, right = keep, up = rewrite with the suggested text, down = investigate. It works by dragging with the mouse or finger, by a fast flick, by a two-finger trackpad swipe, by the arrow keys or by the buttons; `z` undoes. The proposed text is edited with the "Editar" link on the card, so the rest of the card stays draggable. A card with no `proposal` has nothing to rewrite to, so up means investigate. Both views write the same decisions.
- List shortcuts: `j`/`k` move, `1`–`4` choose (keep, rewrite, delete, investigate) and jump to the next undecided card.

## Evals

```bash
python3 <skill-dir>/evals/run_evals.py [-v] [--suite scanner|holdout|holdout2|holdout3|holdout4|holdout5|holdout6|page] [--gate-holdout] [--json]
```

`evals/corpus.py` builds a fake `$HOME` with labelled lines (dates are relative to today, so it never goes stale) and runs the real scanner on it. Labels: `candidate` (must be found), `low` (healthy or authored text, must rank below candidates), `clean` (ordinary text, counts as a false positive if flagged), `excluded` (fences, comments, skills, `node_modules`, too deep; must not appear), `hard` (no marker at all, reported only).

Metrics: lexical **recall**, **global coverage** (pattern hits plus `--unflagged` lines), recall inside the top 40, project recall, **ranking** (candidate above healthy and above clean), exclusion leaks, false-positive rate, cluster and line-level flag checks, and a `page` suite that feeds hostile input to `make_review.py` and checks the HTML.

- `scanner` is the regression suite and gates the exit code. `holdout` to `holdout6` were each written fresh, then folded into the scanner after a failing round. Once folded, a round is regression too (`--gate-holdout`), so **write a new round before trusting the numbers**: a round is only an honest estimate before it is tuned against.
- When the scanner changes, run the evals before and after. A fix for one phrasing that raises false positives shows up in the `clean` cases.

