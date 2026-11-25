---
name: undecree
description: Finds "dogmas" in agent config — one-off comments fossilized into absolute rules ("never use Opus", "only reply in 6 words") with no scope, reason or exception — across Claude Code, Codex, Cursor, Windsurf, Gemini, Devin, OpenCode and project CLAUDE.md/AGENTS.md files, then has the user keep, rewrite or delete each one, in the chat by default or in an HTML review page if they ask for it. Use when an agent refuses something it used to do, when asked to audit or clean agent rules, memory or harness config, or on "quita esa regla", "limpia mis dogmas", "por qué no usas X", "why won't you use X", "eso ya no aplica", "undecree".
license: MIT
compatibility: Requires Python 3.9+ (stdlib only) to run bundled scripts.
metadata:
  version: "1.0.1"
---

# undecree

![mark](assets/mark.svg)

A **dogma** is an absolute directive that lost its context: a one-off comment ("I'm low on credits", "just run this overnight", "I'm tired") saved as a permanent rule. Agents then enforce it forever.

Workflow: **scan → triage with your own judgment → review (in the chat, or an HTML page if the user wants it) → apply what the user marks.** The user gets the final say on every item; your job is to do the reading so they only decide.

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
python3 -I <skill-dir>/scripts/find_dogmas.py [--file PATH]... [--project PATH]... [--json] [--top N] [--all] [--verbose] [--unflagged | --unflagged-all] [--include-skills] [--all-tiers]
```

Covers `~/.claude`, `.codex`, `.cursor`, `.codeium`, `.gemini`, `.hermes`, `.grok`, `.commandcode`, `.qwen`, `.kiro`, `.continue`, `.roo`, Cline, Goose, Amp, `.config/devin`, `.config/opencode`, `.agents`, plus a project sweep of `$HOME` (depth 4). The first line of the report lists the harnesses it found. **If the user runs an agent that is not in that list, look for where it keeps rules or memory (`ls -a ~`, `~/.config`) and run the scanner on it with `--project PATH`, then add it to `HARNESS_TARGETS`.** Output is ranked by a suspicion score:

- Global config is listed best first, **one entry per rule**: the same rule restated in other files (a small cluster), or several hits inside one memory file, collapse into the best line with the rest listed under it. `--top N` caps the list (default 40, `0` = all), `--all` turns the collapsing off, `--json` always has every line. Project rule files are summarized per file (`--verbose` for every line).
- `signals` say why a line was flagged: `ban` (never / don't / avoid / prohibido), `absolute` (always / only / must / limits like "under 20 words"), `temporal` (the rule carries its origin: "for now", "I'm tired", "credits are low", "no longer").
- `!!` = absolute with no exception in its own lines. `[N]` = score. Global config, model/cost words, no exception, short lines and old dates raise it. Descriptive text ("The server never restarts") and lasting reasons (security, policy, CI) lower it.
- `cluster#N` = the same rule restated in several files. Fix them as one item. A cluster of more than 6 lines is several rules chained together by shared words, so it is not tagged or collapsed.
- `memory:feedback|user|reference|project` is the memory file's own `type`. `user` and `reference` memories are facts, so they rank lower; `feedback` ranks higher. A `**Why:**` line explains a rule written elsewhere in the file, so it ranks lower than the rule.
- Flags come from the line and its continuation lines, not the whole file. They are hints, not verdicts.

**The patterns are a ranking aid, not a guarantee.** On phrasing they had never seen, they caught about two thirds of the dogmas. So global config is never judged from the pattern hits alone:

- Read `~/.claude/CLAUDE.md`, `AGENTS.md`, `GEMINI.md` and each `MEMORY.md` index whole. They are short.
- Run with `--unflagged` to list the lines in those files that no pattern matched ("Speak like a pirate."). It also holds the lines the scanner judged to be plain facts ("The cron never runs on weekends.") and the file's preamble, which are kept out of the ranked list. `--unflagged-all` adds memory bodies.
- Project rule files have no such safety net. Only tier-1 hits and risky topics are shown there.

## Step 2 — triage (your judgment)

Open the top candidates and read around them; memory files are small, read them whole. Then pick what goes to review:

- Include plausible fossils / under-scoped / stale rules from global config (CLAUDE.md, AGENTS.md, memory files, rules dirs, agent defs that pin a model).
- Skip authored task prompts (`*/agents/*`, SKILL.md bodies, plugin files) unless they pin a model or ban a tool the user might want.
- **One card per rule, not per file.** An index line, a memory description and the CLAUDE.md line for the same rule are ONE item; the canonical file is `file`, the rest go in `also`.
- Project rule files: at most a few cards for likely fossils, or one `verdict:"file"` item. Never dump hundreds of lines.
- **Keep the review short.** Aim for 12 cards or fewer. If more, take the 12 worst and say how many you left.
- Healthy rules never get a card: list them separately as clean, each with its path, line, and why it is fine.
- Write a proposed rewrite for every card you suggest rewriting, one sentence on why it is a problem (no file inventories, no restating the rule), and what happens in practice if the user deletes it.

## Step 2b — review: chat by default, HTML only on request

**Do not generate or open an HTML page on your own.** Ask once, in one short line, and wait:

> ¿Lo revisamos aquí en el chat o prefieres una página HTML con vista de lista y tarjetas?

Match the user's language. If they already said how they want it, don't ask. If they don't answer the question and just talk about the rules, use the chat.

**In the chat (default).** Show each card as a compact numbered block, worst first, 12 at most:

```
1. ~/.claude/CLAUDE.md:7  [fossil]
   - Do not use Claude Opus for council, sol-loop, or any other subagent.
   Problema: un comentario de créditos bajos quedó como prohibición universal.
   Si lo borras: vuelves a poder usar Opus sin tener que pedirlo.
   Propuesta: - Default to Sonnet/Haiku for subagents (límite de coste, 2026-10-22). Excepción: Opus si lo pides.
   Sugerido: reescribir
```

Then list the healthy rules you skipped in one line each (path, why fine). Tell the user they can answer in short form: `1 reescribir, 2 borrar, 3 mantener`, `todo sugerido`, or `3 reescribir pero con "..."`; anything not mentioned stays untouched. Treat free text about a card as its `comment`. **End your turn there; don't edit anything yet.** Map the answer to the same actions as Step 3 (`reescribir`→`rescope`, `borrar`→`delete`, `mantener`→`keep`, `investigar`→`review`).

**HTML page (only if the user asks).** Read [references/review-page.md](references/review-page.md) for the `items.json` schema and page generator command. **End your turn after opening the page; don't edit anything yet.**

## Step 3 — apply

The user answers in the chat (short form above) or pastes `{ "decisions": [...] }` from the page. Per decision:

| action | do |
|---|---|
| `keep` | nothing |
| `rescope` | write `text` (the user may have edited the proposal); apply to `file` and adapt it for each `also` file, honoring its own format |
| `delete` | remove the line. For a memory file, also remove its `MEMORY.md` index line; for a whole-file item, delete the file |
| `review` | investigate now and report back; change nothing yet |
| `pending` | the user skipped it; leave it alone |

A non-empty `comment` is context from the user. Read it before acting. Show a short diff, then re-run the scanner on the touched files (`find_dogmas.py --file <path>`) to confirm the rule no longer reads as absolute.

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
- Both scripts are stdlib-only Python 3 and use `Path.home()`.
