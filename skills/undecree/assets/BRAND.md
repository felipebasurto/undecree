# undecree — brand

**Idea:** a gavel strikes a stone tablet and the tablet cracks. Decrees get un-decreed.
**Tagline:** *Strike the dogma.* / *Rompe el dogma.*

## Mark

[mark.svg](mark.svg) — a liquid-glass app icon: a continuous-corner squircle in soft green, with two
translucent glass shapes on it, a gavel and a tablet with a crack. Colours are fixed inside the SVG,
so it reads the same everywhere and works as a favicon. No outer shadow. Use it at 24px and up.

[mark-flat.svg](mark-flat.svg) — flat, themed by CSS variables, for print or monochrome.

**Wordmark:** `undecree` in Figtree 600; `un` in brand green, `decree` in ink.

## The page is flat

A flat, hairline-and-soft-fill system, inverted onto graphite: one flat page on graphite, no gradients, **no shadows**.
Depth comes from 1px hairlines and soft fills.

| Token | Value | Use |
|---|---|---|
| ground | `#27292d` | page (graphite) |
| card | `#303338` | cards |
| ink | `#f5f5f7` | text |
| soft ink | `#dfe1e6` | explanations, option labels |
| muted | `#c4c7ce` | paths, hints (7.5:1 on card) |
| line | `#454850` | hairlines, card borders |
| soft | white at 8% | notes, outcome box, grey pills |
| accent | `#7ab8ff` | links and focus only, never a fill |
| brand | `#4fd08a` | the mark and the `un`. Carries no meaning |

**Old vs new rule.** Two clearly different hues, each with its own label ("Ahora" / "Propuesta"):
old `#432820` with text `#ffe3d8`, new `#1b3a2a` with text `#d9f8e6` (11:1). The label carries the meaning,
the hue helps. Body text never goes below 7:1.

**Pastel pairs.** Each state is one fill with its dark ink from the same hue:
keep `#d9e8ff`/`#0b3d91`, rewrite `#d9f3e4`/`#14583a`, delete and fossil `#f9dccb`/`#5c2e1a`,
investigate and unscoped `#fbefc8`/`#5e4400`. The label is always in the text; colour never
carries the state alone.

**Type.** Figtree only (400, 500, 600), loaded from Google Fonts with a system fallback. Mono for
rule text. Headings tighten with size (-0.02em).

**Shape.** Card 14px, pill 999px, row 8px. Spacing steps 4, 8, 12, 16, 24.

## Voice

Short, plain, no drama. Say what the rule is and what it should become. No "Oops", no emoji,
no "AI-powered".

## The page

A title row ("Por decidir", with the count), then one flat card per decree that needs a decision:
old rule, rewrite, one line of why, a four-option segmented control. Healthy items never get a
card. No stripes, uppercase labels or decorative badges. If an element does not help the user
decide, remove it.

This skill is green on purpose: the red one is taken by another skill.
