"""Labelled corpus for the undecree evals.

build(home, today) writes a fake $HOME and returns the expected cases.

Labels
  candidate  A dogma the scanner must surface and rank high. A person reviewing
             agent config would want to see it.
  low        Real text that mentions an absolute but is healthy, authored or
             prose. The scanner may surface it, but it must rank below candidates.
  excluded   Must not appear at all (fenced code, skills, node_modules, depth).

Each case: id, file (relative to $HOME), text (one or more lines), label, and
optional: cluster, exc (expected has_exception on its first line),
age (expected age_days), note.

Dates are relative to `today`, so the corpus never goes stale.
"""

from datetime import timedelta
from pathlib import Path


def d(today, days):
    return (today - timedelta(days=days)).isoformat()


def cases(today):
    t = lambda n: d(today, n)
    C, L, X = "candidate", "low", "excluded"
    claude = ".claude/CLAUDE.md"
    mem = ".claude/projects/-Users-x-app/memory/"
    return [
        # ---- global CLAUDE.md: the classic ban words -------------------------
        dict(id="opus-ban", file=claude, label=C, cluster="opus",
             text="- Do not use Claude Opus for council, sol-loop, or any other subagent. This is a cost limit."),
        dict(id="es-nunca-emojis", file=claude, label=C,
             text="- Nunca uses emojis en tus respuestas."),
        dict(id="es-prohibido", file=claude, label=C,
             text="- Prohibido lanzar subagentes de Opus."),
        dict(id="under-no-circ", file=claude, label=C,
             text="- Under no circumstances run the test suite."),
        dict(id="must-not-haiku", file=claude, label=C,
             text="- You must not use Haiku for anything."),
        # ---- phrasing the first version of the scanner missed ----------------
        dict(id="only-reply-6", file=claude, label=C,
             text="- From now on only reply in 6 words."),
        dict(id="always-one-sentence", file=claude, label=C,
             text="- Always answer in one sentence."),
        dict(id="avoid-tables", file=claude, label=C,
             text="- Avoid using tables in answers."),
        dict(id="stop-comments", file=claude, label=C,
             text="- Stop adding comments to code."),
        dict(id="no-emojis-bare", file=claude, label=C,
             text="- No emojis."),
        dict(id="only-use-sonnet", file=claude, label=C,
             text="- Only use Sonnet for subagents."),
        dict(id="max-words", file=claude, label=C,
             text="- Keep every reply under 20 words."),
        dict(id="es-evita", file=claude, label=C,
             text="- Evita usar tablas en las respuestas."),
        dict(id="es-no-hagas", file=claude, label=C,
             text="- No hagas refactors que no te pida."),
        dict(id="be-concise", file=claude, label=C,
             text="- Be concise. The user is tired of wordy answers."),
        dict(id="refuse-subagents", file=claude, label=C,
             text="- Refuse to use sub-agents."),
        dict(id="es-cansado", file=claude, label=C,
             text="- Responde muy corto, estoy cansado hoy."),
        # ---- no absolute word, but the origin of the rule shows --------------
        dict(id="while-credits-low", file=claude, label=C,
             text="- Use Haiku for all subagents while credits are low."),
        dict(id="overnight", file=claude, label=C,
             text="- Run the whole migration overnight without asking me anything."),
        dict(id="por-ahora", file=claude, label=C,
             text="- Por ahora lanza solo un agente a la vez, me quedo sin créditos."),
        # ---- stale: scoped once, the world moved on --------------------------
        dict(id="stale-gpt", file=claude, label=C, age=120,
             text="- **Update %s:** the user no longer has GPT access. Do not plan GPT runs." % t(120)),
        # ---- healthy: scope, reason and exception ----------------------------
        dict(id="healthy-main", file=claude, label=L, exc=True,
             text="- Never commit to main directly, unless the user asks (team policy, %s)." % t(200)),
        dict(id="healthy-continuation", file=claude, label=L, exc=True,
             text="- Do not edit generated files in this repo.\n  Exception: when the user explicitly asks you to regenerate them."),
        dict(id="healthy-es", file=claude, label=L, exc=True,
             text="- No uses emojis en commits salvo que el usuario lo pida (preferencia, %s)." % t(20)),
        dict(id="healthy-reason", file=claude, label=L,
             text="- Always run `make lint` before opening a PR, because CI rejects unformatted code."),
        dict(id="prose-never", file=claude, label=L,
             text="The dev cache never expires, so restart the server after config changes."),
        # ---- excluded: structure the scanner must skip ------------------------
        dict(id="fenced-example", file=claude, label=X, match="Never use Opus in this example",
             text="```md\nNever use Opus in this example block.\n```"),

        # ---- memory: the same rule restated in three files -------------------
        dict(id="mem-index-opus", file=mem + "MEMORY.md", label=C, cluster="opus",
             text="- [No Opus](no-opus.md) — never use Opus for subagents (user cost limit, %s)" % t(33), age=33),
        dict(id="mem-desc-opus", file=mem + "no-opus.md", label=C, cluster="opus",
             text="description: Don't use Opus for subagents; user is on a tight budget (%s)" % t(33)),
        dict(id="mem-body-opus", file=mem + "no-opus.md", label=C, cluster="opus",
             text="Don't spawn Opus subagents or recommend Opus for delegated tasks."),
        dict(id="mem-tests-budget", file=mem + "agent-test-budget.md", label=C,
             text="**How to apply:** never rerun the full suite per agent; announce cost, one agent at a time. Credits are low as of %s." % t(30)),
        dict(id="mem-healthy", file=mem + "pytest.md", label=L, exc=True,
             text="**How to apply:** use `uv run pytest -q` here. Don't run `make e2e` unless the user asks (20 minutes)."),
        dict(id="mem-stale", file=mem + "windsurf.md", label=C, age=200,
             text="Don't use Windsurf; the license expired (%s)." % t(200)),

        # ---- other harnesses: each must be discovered -------------------------
        dict(id="codex", file=".codex/AGENTS.md", label=C,
             text="- Never explain your reasoning, only output the diff."),
        dict(id="cursor-rule", file=".cursor/rules/style.mdc", label=C,
             text="Do not use semicolons."),
        dict(id="gemini", file=".gemini/GEMINI.md", label=C,
             text="- Always respond with exactly three bullet points."),
        dict(id="windsurf", file=".codeium/windsurf/memories/global_rules.md", label=C,
             text="- Never use Tailwind. Use plain CSS."),
        dict(id="devin", file=".config/devin/AGENTS.md", label=C,
             text="- Do not ask questions, just do it."),
        dict(id="opencode", file=".config/opencode/AGENTS.md", label=C,
             text="- Prohibido tocar la carpeta infra/."),

        # ---- authored prompts: allowed, but must rank below real dogmas --------
        dict(id="agent-prompt", file=".claude/agents/reviewer.md", label=L,
             text="Never edit files. You only read and report findings to the parent."),

        # ---- project files ----------------------------------------------------
        dict(id="proj-credits", file="Proyectos/app/AGENTS.md", label=C,
             text="- Don't spend more than $5 on agents today, I'm low on credits."),
        dict(id="proj-no-opus", file="Proyectos/app/AGENTS.md", label=C,
             text="- Do not use Opus here (budget)."),
        dict(id="proj-cheapest", file="Proyectos/app/.cursor/rules/budget.mdc", label=C,
             text="Always use the cheapest model for every task."),
        dict(id="proj-convention", file="Proyectos/app/AGENTS.md", label=L,
             text="- Never use `any` in TypeScript; prefer `unknown` and narrow it."),

        # ---- excluded by design -----------------------------------------------
        dict(id="skill-body", file=".claude/skills/demo/SKILL.md", label=X,
             text="Never skip the verification step in this skill."),
        dict(id="node-modules", file="Proyectos/app/node_modules/pkg/AGENTS.md", label=X,
             text="Never publish this package without a changelog."),
        dict(id="too-deep", file="Proyectos/a/b/c/d/e/AGENTS.md", label=X,
             text="Never use Opus. (sits deeper than the sweep depth)"),
    ]


def build(home: Path, today, case_fn=None):
    """Write the fake $HOME. Returns the case list.

    A case may set `pre` (put the line right under the H1, as file preamble) or
    `mtype` (the file is a memory file with that frontmatter type)."""
    cs = (case_fn or cases)(today)
    files = {}
    for c in cs:
        files.setdefault(c["file"], []).append(c)
    for rel, group in files.items():
        p = home / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        parts = []
        mtype = next((c["mtype"] for c in group if c.get("mtype")), None)
        if rel.endswith(".mdc"):
            parts.append("---\ndescription: fixture\nalwaysApply: true\n---\n")
        elif mtype:
            parts.append("---\nname: fixture\ndescription: fixture memory\nmetadata:\n  type: %s\n---\n" % mtype)
        parts.append("# Notes\n")
        for c in group:
            if c.get("pre"):
                parts.append(c["text"] + "\n")
        parts.append("Plain context line with nothing to flag.\n")
        for c in group:
            if c.get("pre"):
                continue
            parts.append(c["text"] + "\n")
            parts.append("Some ordinary text between rules.\n")
        p.write_text("\n".join(parts), encoding="utf-8")
    return cs


def holdout(today):
    """Fresh phrasings, written without looking at the scanner's patterns.

    The main corpus is a regression suite: the scanner was tuned until it passed.
    This one measures generalisation. When a case here fails and the fix is
    sensible, fix the scanner and move the case into cases() so it stays covered,
    then write new holdout cases. Cases labelled "hard" cannot be found from the
    words alone and are reported but not gated.
    """
    t = lambda n: d(today, n)
    C, L, X, H = "candidate", "low", "excluded", "hard"
    g = ".claude/CLAUDE.md"
    m = ".claude/projects/-Users-x-web/memory/"
    return [
        dict(id="h-please-dont", file=g, label=C, text="- Please don't touch the database migrations."),
        dict(id="h-rm-rf", file=g, label=C, text="- Never run `rm -rf` outside the repo."),
        dict(id="h-not-allowed", file=g, label=C, text="- You are not allowed to push to main."),
        dict(id="h-caps-not", file=g, label=C, text="- Do NOT use em dashes."),
        dict(id="h-make-sure-never", file=g, label=C, text="- Make sure you never leave TODO comments behind."),
        dict(id="h-skip-tests", file=g, label=C, text="- Skip the tests, I don't care about them right now."),
        dict(id="h-from-here-on", file=g, label=C, text="- From here on, answer in Spanish."),
        dict(id="h-only-at-end", file=g, label=C, text="- Respond in Spanish only."),
        dict(id="h-hates-long", file=g, label=C, text="- The user hates long answers."),
        dict(id="h-es-no-me", file=g, label=C, text="- No me expliques nada, solo haz el cambio."),
        dict(id="h-es-ya-no", file=g, label=C, text="- Ya no uses Devin, no tengo acceso."),
        dict(id="h-off-limits", file=g, label=C, text="- Opus is off limits for delegated work."),
        dict(id="h-anymore", file=g, label=C, text="- Forget about Devin, we don't have it anymore."),
        dict(id="h-x-only-for", file=g, label=C, text="- Haiku only for subagents."),
        dict(id="h-budget-tight", file=g, label=C, text="- Budget is tight, keep agents cheap."),
        dict(id="h-max-parallel", file=g, label=C, text="- Max 3 parallel agents."),
        dict(id="h-limit-to", file=g, label=C, text="- Limit yourself to one tool call per turn."),
        dict(id="h-ask-before", file=g, label=C, text="- Ask before every edit."),
        dict(id="h-banned", file=g, label=C, text="- GPT models are banned in this setup."),
        dict(id="h-es-harto", file=g, label=C, text="- Estoy harto de los comentarios largos en el código."),
        dict(id="h-no-tests", file=g, label=C, text="- No tests."),
        dict(id="h-mem-furious", file=m + "tests.md", label=C,
             text="**Why:** the user was furious that every agent re-ran the whole suite (%s)." % t(25)),
        dict(id="h-mem-expired", file=m + "vpn.md", label=C, age=90,
             text="Update %s: the VPN is gone. Don't plan anything that needs it." % t(90)),
        dict(id="h-mem-no-longer", file=m + "figma.md", label=C,
             text="The user no longer pays for Figma, so skip any Figma step."),
        # hard: no lexical marker at all
        dict(id="hard-pirate", file=g, label="hard", text="- Speak like a pirate."),
        dict(id="hard-approval", file=g, label="hard", text="- Wait for my approval on every step."),
        # low: must not outrank the candidates
        dict(id="h-low-prefer", file=g, label=L, text="- Prefer Sonnet over Opus for subagents."),
        dict(id="h-low-secrets", file=g, label=L, text="- Never log secrets (security policy, %s)." % t(300)),
        dict(id="h-low-hotfix", file=g, label=L, exc=True,
             text="- Don't merge without green CI, unless the user says it's a hotfix (%s)." % t(60)),
        # excluded
        dict(id="h-x-tilde-fence", file=g, label=X, match="Never ship this snippet",
             text="~~~\nNever ship this snippet to production.\n~~~"),
        dict(id="h-x-html-comment", file=g, label=X, match="Never use Opus again",
             text="<!--\nNever use Opus again (old rule, disabled).\n-->"),
    ]


def holdout2(today):
    """Second held-out round, written after the first round was folded into the scanner.

    Also carries "clean" cases: ordinary instructions with no dogma in them. The
    scanner should not surface them, so every one it flags counts as a false positive.
    """
    t = lambda n: d(today, n)
    C, L, X, N = "candidate", "low", "excluded", "clean"
    g = ".claude/CLAUDE.md"
    m = ".claude/projects/-Users-x-api/memory/"
    p = "Proyectos/api/AGENTS.md"
    return [
        dict(id="r2-never-want", file=g, label=C, text="- I never want to see a summary at the end of your reply."),
        dict(id="r2-quit", file=g, label=C, text="- Quit adding unit tests I didn't request."),
        dict(id="r2-must-fit", file=g, label=C, text="- Answers must fit on one screen."),
        dict(id="r2-no-more-than", file=g, label=C, text="- No more than two options per question."),
        dict(id="r2-cheapest-only", file=g, label=C, text="- Cheapest model only."),
        dict(id="r2-always-haiku", file=g, label=C, text="- Always Haiku."),
        dict(id="r2-es-nada-de", file=g, label=C, text="- Nada de preguntas, tú decide."),
        dict(id="r2-es-sin", file=g, label=C, text="- Sin emojis."),
        dict(id="r2-es-menos-de", file=g, label=C, text="- Responde en menos de 50 palabras."),
        dict(id="r2-es-quiero-cortas", file=g, label=C, text="- Quiero respuestas cortas, hoy no tengo tiempo."),
        dict(id="r2-this-week", file=g, label=C, text="- This week we're only fixing bugs, no new features."),
        dict(id="r2-shouldnt", file=g, label=C, text="- Agents shouldn't open PRs."),
        dict(id="r2-nobody-should", file=g, label=C, text="- Nobody should edit the lockfile by hand."),
        dict(id="r2-too-expensive", file=g, label=C, text="- Opus costs too much, so default to Sonnet."),
        dict(id="r2-stop-apologising", file=g, label=C, text="- Please stop apologising."),
        dict(id="r2-less-chatty", file=g, label=C, text="- Be less chatty."),
        dict(id="r2-flaky", file=g, label=C, text="- Disable the linter step, it's flaky this month."),
        dict(id="r2-mem-gone", file=m + "stripe.md", label=C, age=75,
             text="Update %s: we switched away from Stripe. Do not plan Stripe work." % t(75)),
        dict(id="r2-mem-never-ask", file=m + "style.md", label=C,
             text="**How to apply:** never ask for confirmation before editing files; the user finds it slow."),
        dict(id="r2-proj-launch", file=p, label=C, text="- Until the launch, never touch the payments module."),
        dict(id="r2-proj-no-opus", file=p, label=C, text="- Opus is too expensive for this repo."),
        dict(id="r2-hard-single-para", file=g, label="hard", text="- Keep it to a single paragraph."),
        dict(id="r2-hard-zero-emojis", file=g, label="hard", text="- Zero emojis, ever."),
        dict(id="r2-hard-delegate", file=g, label="hard", text="- Delegate everything to Sonnet."),
        # low
        dict(id="r2-low-secret", file=g, label=L, text="- Never print API keys in logs (security requirement)."),
        dict(id="r2-low-unless", file=g, label=L, exc=True,
             text="- Don't push to a shared branch unless the user says so (team rule, %s)." % t(90)),
        # clean: nothing to flag
        dict(id="n-ts-strict", file=g, label=N, text="- Use TypeScript strict mode for all new files."),
        dict(id="n-pytest", file=g, label=N, text="- Run tests with `uv run pytest -q`."),
        dict(id="n-conventional", file=g, label=N, text="- Commits follow Conventional Commits."),
        dict(id="n-small-prs", file=g, label=N, text="- Prefer small, focused PRs."),
        dict(id="n-branch", file=g, label=N, text="- The main branch is `develop`."),
        dict(id="n-tests-live", file=g, label=N, text="- Tests live in `tests/` and mirror the source tree."),
        dict(id="n-prettier", file=g, label=N, text="- Formatting is handled by Prettier."),
        dict(id="n-button", file=g, label=N, text="- Use the shared `Button` component from the design system."),
        dict(id="n-models", file=g, label=N, text="- Use sonnet for planning and haiku for mechanical edits."),
        dict(id="n-only-api", file=g, label=N, text="- Only the API package uses Redis."),
        dict(id="n-staging", file=g, label=N, text="- Staging deploys on every merge to develop."),
        dict(id="n-es-deploy", file=g, label=N, text="- El deploy se hace desde la rama main."),
        dict(id="n-xcode", file=g, label=N, text="- Open the project in Xcode 17 and build the `App` scheme."),
        dict(id="n-mem-fact", file=m + "api.md", label=N, text="The API paginates with cursors, 50 items per page."),
        dict(id="n-proj-layout", file=p, label=N, text="- Source lives in `src/`, generated clients in `gen/`."),
    ]


def holdout3(today):
    """Third round, untouched by any tuning. Its numbers are the honest estimate of
    how the scanner does on phrasing it has never seen. Fold failures into cases()
    only after reading the report, then write a fourth round.

    Its "clean" cases are deliberately nasty: ordinary descriptive text that happens
    to contain a trigger word (never, forbids, currently, banned).
    """
    t = lambda n: d(today, n)
    C, L, N = "candidate", "low", "clean"
    g = ".claude/CLAUDE.md"
    m = ".claude/projects/-Users-x-shop/memory/"
    p = "Proyectos/shop/AGENTS.md"
    return [
        dict(id="r3-dont-you-dare", file=g, label=C, text="- Don't you dare create new files unless it's absolutely necessary."),
        dict(id="r3-refrain", file=g, label=C, text="- Refrain from using the word 'delve'."),
        dict(id="r3-tight", file=g, label="hard", text="- Keep replies tight."),
        dict(id="r3-absolutely-no", file=g, label=C, text="- Absolutely no console.log left in committed code."),
        dict(id="r3-out-of-tokens", file=g, label=C, text="- One agent at a time. I'm out of tokens until Friday."),
        dict(id="r3-never-push", file=g, label=C, text="- Never push; I'll push myself."),
        dict(id="r3-no-go", file=g, label=C, text="- Opus is a no-go this month."),
        dict(id="r3-until-otherwise", file=g, label=C, text="- Run everything on Haiku until I tell you otherwise."),
        dict(id="r3-english", file=g, label="hard", text="- Respond in English even if I write in Spanish."),
        dict(id="r3-urgent", file=g, label="hard", text="- Treat every request as urgent."),
        dict(id="r3-any-circumstances", file=g, label=C, text="- Do not under any circumstances modify .env files."),
        dict(id="r3-es-ya-no-hace-falta", file=g, label=C, text="- Ya no hace falta que hagas tests."),
        dict(id="r3-es-prohibido-main", file=g, label=C, text="- Prohibido commitear a main."),
        dict(id="r3-es-jamas", file=g, label=C, text="- Jamás borres la carpeta data."),
        dict(id="r3-es-contesta", file=g, label=C, text="- Solo contesta con una palabra."),
        dict(id="r3-es-siempre-caps", file=g, label=C, text="- Responde SIEMPRE en español."),
        dict(id="r3-codex-breaks", file=g, label=C, text="- Don't use Codex, it keeps breaking my repo."),
        dict(id="r3-sonnet-from-now", file=g, label=C, text="- Only Sonnet 5.5 from now on."),
        dict(id="r3-weekend", file=g, label=C, text="- It's the weekend, so no deploys."),
        dict(id="r3-avoid-mocks", file=g, label=C, text="- Whatever you do, avoid mocks."),
        dict(id="r3-cap", file=g, label="hard", text="- Cap each answer at 3 bullets."),
        dict(id="r3-use-only", file=g, label=C, text="- Use only the standard library."),
        dict(id="r3-mem-stop-asking", file=m + "asking.md", label=C,
             text="The user said \"stop asking me things\" (%s)." % t(14)),
        dict(id="r3-mem-subagents", file=m + "agents.md", label=C,
             text="**How to apply:** do not use subagents for anything under 10 lines."),
        dict(id="r3-mem-linear", file=m + "linear.md", label=C,
             text="Update %s: Linear is dead for us. Use GitHub issues." % t(80)),
        dict(id="r3-mem-index-terse", file=m + "MEMORY.md", label=C,
             text="- [Terse replies](terse.md) — user wants one-liners until further notice"),
        dict(id="r3-proj-e2e", file=p, label=C, text="- Don't run the full e2e suite; it's too slow right now."),
        dict(id="r3-proj-cheap", file=p, label=C, text="- Keep the budget under control, use cheap models."),
        dict(id="r3-codex-no-tests", file=".codex/AGENTS.md", label=C, text="- Never write tests."),
        dict(id="r3-cursor-single-line", file=".cursor/rules/answers.mdc", label=C, text="Always answer in a single line."),
        # low
        dict(id="r3-low-env", file=g, label=L, text="- Never commit `.env` files (secrets, security policy)."),
        dict(id="r3-low-forget", file=g, label=L, text="- Do not forget to run `make setup` after cloning."),
        # clean: descriptive text with trigger words in it
        dict(id="n3-currently", file=g, label=N, text="- Currently the API is on v2; v3 ships in January."),
        dict(id="n3-today", file=g, label=N, text="- Today's standup is at 10:00 CET."),
        dict(id="n3-forbids", file=g, label=N, text="- The linter forbids unused imports."),
        dict(id="n3-never-restarts", file=g, label=N, text="- The server never restarts during deploys."),
        dict(id="n3-evicted", file=g, label=N, text="- Cache entries are never evicted in tests."),
        dict(id="n3-always-on", file=g, label=N, text="- An always-on VPN is required for staging."),
        dict(id="n3-banned-list", file=g, label=N, text="- The banned word list lives in `.ci/banned.txt`."),
        dict(id="n3-max-retries", file=g, label=N, text="- Max retries is 3 in `config.ts`."),
        dict(id="n3-compose", file=g, label=N, text="- Prefer composition over inheritance."),
        dict(id="n3-budgets", file=g, label=N, text="- Error budgets are tracked in Grafana."),
        dict(id="n3-tokens", file=g, label=N, text="- Session tokens expire after 15 minutes."),
        dict(id="n3-gateway", file=g, label=N, text="- Sonnet and Haiku are both available through the gateway."),
        dict(id="n3-es-hoy", file=g, label=N, text="- La API de pagos está documentada en `docs/pagos.md`."),
        dict(id="n3-mem-fact", file=m + "db.md", label=N, text="The orders table is partitioned by month."),
        dict(id="n3-proj-fact", file=p, label=N, text="- Checkout lives in `apps/web/checkout`."),
    ]


def holdout4(today):
    """Round 4. Written after round 3 was folded into the scanner and not tuned
    against since: this is the number to quote."""
    t = lambda n: d(today, n)
    C, L, N = "candidate", "low", "clean"
    g = ".claude/CLAUDE.md"
    m = ".claude/projects/-Users-x-ios/memory/"
    p = "Proyectos/ios/AGENTS.md"
    return [
        dict(id="r4-never-mention-ai", file=g, label=C, text="- Please never mention that you're an AI."),
        dict(id="r4-no-breaks", file=g, label=C, text="- Don't suggest breaks."),
        dict(id="r4-json-only", file=g, label=C, text="- Output JSON only, no prose."),
        dict(id="r4-skip-preamble", file=g, label=C, text="- The user is in a hurry. Skip the preamble."),
        dict(id="r4-airport", file=g, label=C, text="- Do everything in one go, I'm leaving for the airport."),
        dict(id="r4-overkill", file=g, label=C, text="- Opus is overkill for this, don't bother."),
        dict(id="r4-forget", file=g, label=C, text="- Forget what I said about tests."),
        dict(id="r4-off-table", file=g, label=C, text="- Writing docs is off the table."),
        dict(id="r4-no-prs", file=g, label=C, text="- No PRs before Monday."),
        dict(id="r4-pause-refactor", file=g, label=C, text="- Let's pause all refactoring while we ship v2."),
        dict(id="r4-never-ever", file=g, label=C, text="- Never, ever, apologise."),
        dict(id="r4-cursor-out", file=g, label=C, text="- Cursor is out. We use Claude Code only."),
        dict(id="r4-es-sin-presupuesto", file=g, label=C, text="- Estoy sin presupuesto: usa siempre el modelo más barato."),
        dict(id="r4-es-no-quiero", file=g, label=C, text="- No quiero tests nuevos."),
        dict(id="r4-es-deja-de", file=g, label=C, text="- Deja de preguntarme por permisos."),
        dict(id="r4-es-tienes-prohibido", file=g, label=C, text="- Tienes prohibido escribir documentación."),
        dict(id="r4-es-mientras", file=g, label=C, text="- Mientras dure el sprint, nada de refactors."),
        dict(id="r4-mem-burned", file=m + "bill.md", label="hard",
             text="**Why:** the user got burned by a surprise bill in October."),
        dict(id="r4-mem-dollars", file=m + "bill.md", label=C,
             text="**How to apply:** stay under $2 per task."),
        dict(id="r4-mem-index-dark", file=m + "MEMORY.md", label=C,
             text="- [Dark mode off](dark.md) — user can't stand dark themes"),
        dict(id="r4-gemini", file=".gemini/GEMINI.md", label=C, text="- Responde únicamente con código."),
        dict(id="r4-windsurf", file=".codeium/windsurf/memories/global_rules.md", label=C,
             text="- Don't touch Windsurf settings."),
        dict(id="r4-proj-redux", file=p, label=C, text="- Never use Redux in this repo."),
        dict(id="r4-proj-freeze", file=p, label=C, text="- We're freezing the schema until the audit ends."),
        dict(id="r4-cursor-classes", file=".cursor/rules/fp.mdc", label=C, text="Don't use classes, only functions."),
        dict(id="r4-low-legacy", file=g, label=L,
             text="- Do not rely on the legacy endpoint `/v1/orders` (removed in v3, policy)."),
        dict(id="r4-low-utc", file=g, label=L, text="- Always UTC in the database."),
        dict(id="r4-low-400", file=g, label=L, text="- Keep PRs under 400 lines."),
        dict(id="n4-drafts", file=g, label=N, text="- Users can't see drafts until they publish them."),
        dict(id="n4-neverending", file=g, label=N, text="- Never-ending lists are paginated by the API."),
        dict(id="n4-admins", file=g, label=N, text="- Only admins see the audit tab."),
        dict(id="n4-parallel", file=g, label=N, text="- Tests run in parallel by default."),
        dict(id="n4-deprecated", file=g, label=N, text="- The old pipeline is deprecated; see `docs/ci.md`."),
        dict(id="n4-flags", file=g, label=N, text="- Feature flags live in LaunchDarkly."),
        dict(id="n4-you-can", file=g, label=N, text="- You can run the app with `make dev`."),
        dict(id="n4-never-mind", file=g, label=N, text="- Never mind the formatting, the formatter runs on save."),
        dict(id="n4-default-model", file=g, label=N, text="- Sonnet 5.5 is the default model in this workspace."),
        dict(id="n4-finance", file=g, label=N, text="- Budget approvals go through Finance."),
        dict(id="n4-mem-fact", file=m + "api.md", label=N, text="The sync job runs at 03:00 UTC."),
        dict(id="n4-proj-fact", file=p, label=N, text="- The Xcode project is generated from `project.yml`."),
    ]


def holdout5(today):
    """Round 5. Written after round 4 was folded in, and not tuned against until
    its first run. Adds project files (the weak spot), memory types, "Why:" lines
    and file preambles."""
    t = lambda n: d(today, n)
    C, L, N = "candidate", "low", "clean"
    g = ".claude/CLAUDE.md"
    m = ".claude/projects/-Users-x-shop/memory/"
    p = "Proyectos/shop/CLAUDE.md"
    q = "Proyectos/shop/.github/copilot-instructions.md"
    return [
        dict(id="r5-zero-chatter", file=g, label=C, text="- Zero chatter, just the diff."),
        dict(id="r5-whatever", file=g, label=C, text="- Whatever you do, don't open a browser."),
        dict(id="r5-no-more-agents", file=g, label=C, text="- I don't want any more subagents today."),
        dict(id="r5-not-a-single", file=g, label=C, text="- Not a single comment in the code, please."),
        dict(id="r5-no-condition", file=g, label=C, text="- Under no condition touch prod."),
        dict(id="r5-cheaper-until", file=g, label=C, text="- Cheaper models only until the invoice clears."),
        dict(id="r5-dotfiles", file=g, label=C, text="- Never touch my dotfiles. Seriously."),
        dict(id="r5-stay-away", file=g, label=C, text="- Stay away from GraphQL."),
        dict(id="r5-under-words", file=g, label=C, text="- Reply in under 15 words."),
        dict(id="r5-mobile", file=g, label=C, text="- Keep answers to one sentence while I'm on mobile."),
        dict(id="r5-no-questions", file=g, label=C, text="- You must never ask clarifying questions."),
        dict(id="r5-gemini-gone", file=g, label=C, text="- Gemini is no longer part of the stack."),
        dict(id="r5-main-only", file=g, label=C, text="- All commits go straight to main, no branches."),
        dict(id="r5-delve", file=g, label=C, text="- Don't ever use the word 'delve'."),
        dict(id="r5-es-nunca-mas", file=g, label=C, text="- Nunca más uses Cursor."),
        dict(id="r5-es-prohibido", file=g, label=C, text="- Prohibido tocar producción hasta nuevo aviso."),
        dict(id="r5-es-decide", file=g, label=C, text="- No me preguntes, decide tú."),
        dict(id="r5-es-cero-gasto", file=g, label=C, text="- Hasta que acabe el trimestre, cero gastos en agentes."),
        dict(id="r5-mem-one-agent", file=m + "budget.md", mtype="feedback", label=C,
             text="**How to apply:** one agent at a time until the credit reset."),
        dict(id="r5-mem-stop-sonnet", file=m + "review.md", mtype="feedback", label=C,
             text="The user said \"stop using sonnet for review, it misses things\" (%s)." % t(14)),
        dict(id="r5-mem-index", file=m + "MEMORY.md", label=C,
             text="- [No browsers](no-browser.md) \u2014 never open a browser unprompted"),
        # project files: the weak spot
        dict(id="r5-p-budget", file=p, label=C, text="- We're low on budget, don't run the e2e suite."),
        dict(id="r5-p-redesign", file=p, label=C, text="- Until the redesign lands, no new pages."),
        dict(id="r5-p-tests", file=p, label=C, text="- Stop adding tests, the owner hates them."),
        dict(id="r5-p-billing", file=p, label=C, text="- Don't touch the billing module, the founder is rewriting it."),
        dict(id="r5-p-haiku", file=p, label=C, text="- Use only Haiku in this repo."),
        dict(id="r5-p-tailwind", file=p, label=C, text="- No Tailwind. The owner changed his mind."),
        dict(id="r5-p-lint", file=p, label=C, text="- Skip linting for now."),
        dict(id="r5-p-refactor", file=q, label=C, text="- Please do not refactor anything this month."),
        # low: must rank below the candidates
        dict(id="r5-low-secrets", file=p, label=L, text="- Never commit secrets (security policy)."),
        dict(id="r5-low-prod", file=p, label=L, text="- Only admins can run migrations in production (compliance)."),
        dict(id="r5-low-ref", file=m + "urls.md", mtype="reference", label=L,
             text="Never share the staging URL outside the team."),
        dict(id="r5-low-user", file=m + "profile.md", mtype="user", label=L,
             text="The user doesn't like meetings before 10am and never answers email on weekends."),
        dict(id="r5-low-why", file=m + "budget.md", mtype="feedback", label=L,
             text="**Why:** the user never wants to see raw logs in answers, they got burned twice."),
        # clean: must not be flagged
        dict(id="n5-cron", file=g, label=N, text="- The cron never runs on weekends."),
        dict(id="n5-legacy", file=g, label=N, text="- Nobody uses the legacy admin panel anymore."),
        dict(id="n5-two-eng", file=g, label=N, text="- Only two engineers have prod access."),
        dict(id="n5-docker", file=g, label=N, text="- The build doesn't need Docker."),
        dict(id="n5-always-on", file=g, label=N, text="- Always-on instances cost more than spot ones."),
        dict(id="n5-owner", file=g, label=N, text="- This service is no longer maintained by the infra team; see `docs/ownership.md`."),
        dict(id="n5-preamble", file=g, label=N, pre=True,
             text="Always applied. Overrides the defaults. Applies to new sessions."),
        dict(id="n5-mem-ref", file=m + "urls.md", mtype="reference", label=N,
             text="The staging dashboard lives at https://staging.example.com/ops and never needs a login."),
    ]


def holdout6(today):
    """Round 6. Written after round 5 was folded in; run once before any change.
    Aimed at the riskiest heuristic added in round 5: hiding lines that read as
    facts. Dogmas that are phrased as statements must still be found."""
    t = lambda n: d(today, n)
    C, L, N = "candidate", "low", "clean"
    g = ".claude/CLAUDE.md"
    m = ".claude/projects/-Users-x-site/memory/"
    p = "Proyectos/site/AGENTS.md"
    return [
        dict(id="r6-docs-off", file=g, label=C, text="- Documentation is off the table this quarter."),
        dict(id="r6-refactors-oos", file=g, label=C, text="- Refactors are out of scope until v2."),
        dict(id="r6-comments-banned", file=g, label=C, text="- Comments are banned in this setup."),
        dict(id="r6-tests-optional", file=g, label=C, text="- Tests are optional for now."),
        dict(id="r6-user-no-tests", file=g, label=C, text="- The user doesn't want tests written today."),
        dict(id="r6-nobody-deps", file=g, label=C, text="- Nobody should add dependencies until the audit ends."),
        dict(id="r6-every-short", file=g, label=C, text="- Every answer must be two lines max."),
        dict(id="r6-all-haiku", file=g, label=C, text="- All delegated work runs on Haiku."),
        dict(id="r6-es-sin-prisa", file=g, label=C, text="- Sin tests por ahora, tengo prisa."),
        dict(id="r6-es-solo-codigo", file=g, label=C, text="- Quiero solo el diff, nada de explicaciones."),
        dict(id="r6-mem-hate", file=m + "style.md", mtype="feedback", label=C,
             text="The user hates bullet lists in replies (%s)." % t(9)),
        dict(id="r6-mem-index", file=m + "MEMORY.md", label=C,
             text="- [No emojis](emojis.md) \u2014 the user finds them childish, none anywhere"),
        dict(id="r6-p-nofunds", file=p, label=C, text="- No money for paid APIs this month, mock everything."),
        dict(id="r6-p-owner", file=p, label=C, text="- The owner is against dark mode, so don't build it."),
        dict(id="r6-low-compliance", file=p, label=L, text="- Never store card numbers (PCI compliance)."),
        dict(id="r6-low-ref", file=m + "infra.md", mtype="reference", label=L,
             text="Never restart the primary database without a snapshot."),
        dict(id="n6-fact-runs", file=g, label=N, text="- The nightly job runs at 02:00 and never touches user data."),
        dict(id="n6-fact-only", file=g, label=N, text="- Only the payments service writes to the ledger."),
        dict(id="n6-fact-always", file=g, label=N, text="- The cache is always warm after a deploy."),
        dict(id="n6-fact-nobody", file=g, label=N, text="- Nobody owns the legacy importer right now."),
        dict(id="n6-fact-not-allowed", file=g, label=N, text="- The API gateway does not allow requests over 10 MB."),
        dict(id="n6-fact-no-longer", file=g, label=N, text="- The staging cluster no longer exists; use preview environments."),
        dict(id="n6-mem-fact", file=m + "infra.md", mtype="reference", label=N,
             text="The primary database is Postgres 16 and never sleeps."),
    ]


def holdout7(today):
    """Round 7. Tests structural edge cases (inline HTML comments, nested fences,
    CLAUDE.local.md, AGENTS.override.md) alongside fresh phrasing."""
    t = lambda n: d(today, n)
    C, L, N, X = "candidate", "low", "clean", "excluded"
    g = ".claude/CLAUDE.md"
    m = ".claude/projects/-Users-x-app/memory/"
    return [
        dict(id="r7-inline-comment", file=g, label=C, match="Never use Opus",
             text="<!-- old note --> - Never use Opus for anything."),
        dict(id="r7-multiline-comment-tail", file=g, label=C, match="Do not push",
             text="<!-- disabled note\n--> - Do not push to staging this week."),
        dict(id="r7-local-claude", file=".claude/CLAUDE.local.md", label=C,
             text="- Never run the slow integration suite, credits are tight."),
        dict(id="r7-codex-override", file=".codex/AGENTS.override.md", label=C,
             text="- Always use Haiku only."),
        dict(id="r7-nested-mem", file=m + "sub/cost.md", mtype="feedback", label=C,
             text="Don't spawn subagents until next month."),
        dict(id="r7-nested-fence", file=g, label=X, match="Never leak inside outer fence",
             text="````md\n```bash\necho hi\n```\nNever leak inside outer fence.\n````"),
        dict(id="r7-low-reminder", file=g, label=L,
             text="- Don't forget to run `make format` before pushing."),
        dict(id="n7-todays-deploy", file=g, label=N,
             text="- Today's release window opens at 16:00 UTC."),
        dict(id="n7-currently-fact", file=g, label=N,
             text="- Currently the worker pool runs 4 replicas."),
        dict(id="r7-es-presupuesto", file=g, label=C,
             text="- No tengo presupuesto, usa siempre el modelo más barato."),
    ]

