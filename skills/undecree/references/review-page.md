# HTML review page (optional)

Read this file only when the user asks for the HTML review page instead of reviewing in the chat.

Brand (mark, palette, voice): [../assets/BRAND.md](../assets/BRAND.md). Don't restyle the page, and don't add copy it doesn't need.

## Generate and open

Write `items.json`, then render and open:

```bash
python3 <skill-dir>/scripts/make_review.py items.json -o review.html --open
```

Tell the user to mark each card and paste back the copied JSON. **End your turn there; don't edit anything yet.**

## `items.json` schema

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
      "outcome": "Subagents may pick Opus by default again and spend rises, but agents stop refusing Opus when you ask for it.",
      "verdict": "fossil",
      "suggested": "rescope",
      "proposal": "- Default to Sonnet/Haiku for subagents — user cost limit, 2026-10-22.\n  Exception: use Opus when the user explicitly asks for it or names it.",
      "also": [
        {
          "file": "~/.claude/projects/x/memory/MEMORY.md",
          "line": 6,
          "proposal": "optional per-file rewrite"
        }
      ]
    }
  ],
  "clean": [
    {
      "file": "~/.claude/CLAUDE.md",
      "line": 5,
      "rule": "the line as written",
      "note": "why it is fine"
    }
  ]
}
```

- `verdict`: `fossil` | `under-scoped` | `stale` | `file`
- `suggested`: `keep` | `rescope` | `delete` | `review`. Shown as the suggestion on the card; the user still decides or clicks "Accept suggested".
- `lang`: `es` or `en`. Match the user's language. Defaults to `$LANG`.
- `id` is optional (auto-numbered positive integer); `line`, `context`, `proposal`, `also` are optional.
- `outcome`: what happens in practice if the rule is deleted. Shown as "Si lo borras" / "If you delete it". Write it for every card.
- `clean`: shown collapsed as "Revisadas, sin problema" / "Reviewed, all fine". Give each entry a real path and `line`, the rule as written in `rule`, and in `note` why it is fine (scope, reason, date, exception). Entries that are not rules (empty files, task prompts) get a `note` and no `rule`.

## Page behavior

- Single self-contained HTML file: no server, works offline (Figtree falls back to system fonts), state saved in `localStorage`.
- Two views, switched at the top right and remembered per browser:
  - **Lista / List**: all cards. Shortcuts: `j`/`k` move, `1`–`4` choose (keep, rewrite, delete, investigate) and advance to the next undecided card.
  - **Tarjetas / Cards**: one card at a time. Left = delete, right = keep, up = rewrite with the suggested text (or investigate if there is no `proposal`), down = investigate, `z` = undo. Works via mouse/touch drag, flick, two-finger trackpad swipe, arrow keys or buttons. Use the "Editar" / "Edit" link on the card to edit the proposed text.
- Both views stay synced and export the same `{ "decisions": [...] }` JSON.
