#!/usr/bin/env python3
"""find_dogmas — scan agent harnesses for "decrees": absolute directives
(never / do not / always / prohibido ...) that may be one-off comments
fossilized into permanent rules.

Prints candidate lines ranked by suspicion score, each with line-level
context flags (date, reason, exception, scope) read from the line and the
continuation lines under it. Global config is listed line by line; project
rule files are summarized per file (use --verbose for every line). Lines
that restate the same rule across files share a cluster id. The agent
reading this output must still open the files and judge — this is a
candidate finder, not a verdict.

What it scans (whatever exists under $HOME):
  - global rule files: CLAUDE.md, AGENTS.md, GEMINI.md, global_rules.md ...
  - memory dirs: ~/.claude/projects/*/memory/*.md and friends
  - rules/agents/prompts dirs of each detected harness
  - project sweep: CLAUDE.md / AGENTS.md / .cursor/rules / .devin / ...
    in $HOME and any --project roots

Skills dirs (SKILL.md and */skills/) are excluded by default — skill
bodies are task guidance, not user dogma. Pass --include-skills to scan
the global harness skill dirs too.

Usage:
    find_dogmas.py [--json] [--no-projects] [--project PATH]...
                   [--depth N] [--include-skills] [--all-tiers] [--verbose]
"""

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

HOME = Path.home()

SCAN_EXTS = {".md", ".mdc", ".markdown", ".txt"}

PROJECT_FILES = {
    "CLAUDE.md",
    "CLAUDE.local.md",
    "AGENTS.md",
    "GEMINI.md",
    "QWEN.md",
    ".cursorrules",
    ".windsurfrules",
    ".clinerules",
    "copilot-instructions.md",
}

PROJECT_DOTDIRS = {".claude", ".cursor", ".devin", ".windsurf", ".codex", ".agents", ".github"}

# Subdirectories inside agent dot-dirs whose .md files are config, not docs.
CONFIG_SUBDIRS = {"rules", "agents", "memory", "prompts", "commands"}

HARNESS_TARGETS = [
    # Claude Code
    ("claude-code", "global-rules", ".claude/CLAUDE.md"),
    ("claude-code", "memory", ".claude/projects"),
    ("claude-code", "rules", ".claude/rules"),
    ("claude-code", "agents", ".claude/agents"),
    # Codex
    ("codex", "global-rules", ".codex/AGENTS.md"),
    ("codex", "agents", ".codex/agents"),
    ("codex", "prompts", ".codex/prompts"),
    # Cursor
    ("cursor", "rules", ".cursor/rules"),
    # Windsurf
    ("windsurf", "memory", ".codeium/windsurf/memories"),
    # Gemini
    ("gemini", "global-rules", ".gemini/GEMINI.md"),
    # Whole config dirs: only doc files are read; skills/ is pruned below.
    ("devin", "config", ".config/devin"),
    ("opencode", "config", ".config/opencode"),
]

SKILLS_TARGETS = [
    ("claude-code", ".claude/skills"),
    ("codex", ".codex/skills"),
    ("cursor", ".cursor/skills"),
    ("gemini", ".gemini/skills"),
    ("devin", ".config/devin/skills"),
    ("opencode", ".config/opencode/skills"),
    ("agents", ".agents/skills"),
]

PRUNE_DIRS = {
    "node_modules", ".git", ".hg", ".svn", "dist", "build", ".next",
    ".nuxt", ".turbo", ".cache", "cache", "logs", "log", "tmp", "temp",
    "__pycache__", ".venv", "venv", "target", "Library", ".Trash",
    "Pictures", "Photos Library", "Music", "Movies", "Applications",
    "archived_sessions", "attachments", "history", "sessions",
}

PROJECT_PRUNE_DIRS = PRUNE_DIRS | {
    ".cargo", ".rustup", ".npm", ".nvm", ".pyenv", ".rbenv", ".volta",
    ".docker", ".kube", ".ollama", ".vscode", ".idea", ".expo",
    "skills", "references", "assets", "examples", "templates",
}

# Tier 1: bans and prohibitions.
TIER1_EN = re.compile(
    r"\b(?:never|do not|don't|does not|must not|mustn't|shall not|cannot|can not"
    r"|is not allowed|are not allowed|not allowed|under no circumstances"
    r"|in no case|on no account|prohibited|forbidden|no uses"
    r"|avoid|refrain from|refuse to|no more|stop (?:\w+ing|using|adding|doing)"
    r"|off[- ]limits|banned|ban on|no-go|out of bounds|forbid\w*"
    r"|quit \w+ing|should(?: not|n'?t)|(?:nobody|no one|nothing) should|absolutely no"
    r"|off the table|forget (?:what|about|everything|that)|pause (?:all )?\w+|freez\w+|frozen"
    r"|no (?:deploys?|deployments?|commits?|pushes|merges?|tests?|comments?|emojis?|tables?|docs?"
    r"|questions?|refactors?|new files?|new dependencies))\b",
    re.IGNORECASE,
)
# A bullet that is just "No <thing>" ("- No emojis."). Case-sensitive on purpose.
BARE_NO = re.compile(r"^\s*(?:[-*+\u2022]\s*|\d+[.)]\s*)?(?:\*\*)?(?:No|Sin|Nada de|Zero)\s+[A-Za-z`][^.]{0,60}\.?\s*$")
TIER1_ES = re.compile(
    r"\b(?:nunca|jam[aá]s|prohibid[oa]s?|bajo ninguna circunstancia"
    r"|en ning[uú]n caso|ning[uú]n caso|no uses?|no debes|no deber[ií]as"
    r"|evit(?:a|ar|es)|deja(?:r)? de"
    r"|no (?:hagas|pongas|a[nñ]adas|incluyas|escribas|ejecutes|toques|borres|crees"
    r"|menciones|digas|llames|lances|generes|modifiques|edites|instales|preguntes"
    r"|expliques|quiero))\b",
    re.IGNORECASE,
)
# Tier 2: absolutes without a negation, and limits on how to answer.
TIER2 = re.compile(
    r"\b(?:always|every time|only ever|only (?:use|reply|respond|answer|write|speak|say|output|return)"
    r"|exclusively|from now on|from here on|going forward|henceforth|must |should always"
    r"|use only|be (?:concise|brief|terse|short|less \w+)|less chatty|tone it down|skip (?:the |any |all |every )"
    r"|(?:\w+ )only (?:for|in|on|when|with)|max(?:imum)?\.? \d+|limit (?:yourself |it |them )?to"
    r"|ask (?:me )?before (?:every|each|any|running|editing|touching)"
    r"|keep (?:\w+ ){0,3}(?:short|brief|concise|terse)"
    r"|(?:under|below|at most|no more than|up to|max(?:imum)?(?: of)?) \d+ (?:words|lines|sentences|paragraphs)"
    r"|(?:in|with) (?:only )?\d+ words|exactly \d+"
    r"|siempre|tiene que|hay que|debe |solo (?:responde|contesta|usa|escribe|habla)|[uú]nicamente"
    r"|menos de \d+ palabras|m[aá]ximo (?:de )?\d+ (?:palabras|l[ií]neas|frases))\b",
    re.IGNORECASE,
)
ONLY_END = re.compile(r"\b\w+ only(?:[.!,;]|\s*$)", re.IGNORECASE)
IDIOMS = re.compile(r"\bnever[- ]?(?:mind|ending)\b|\bnevertheless\b|\bnever-\w+|\w+-never\b", re.IGNORECASE)
# The origin of a rule showing through: time-bound or emotional context. A line with
# one of these is worth a look even when it has no absolute word at all.
TEMPORAL = re.compile(
    r"\b(?:tonight|overnight|for now|for today|today|this week|this month|temporar\w*"
    r"|until further notice|until i say|i'?m tired|tired of|low on credits|out of credits"
    r"|credits? (?:are|is) (?:low|tight|limited)|while (?:\w+ ){0,2}(?:are|is) (?:low|tight|limited)"
    r"|me quedo sin|estoy cansad[oa]|por ahora|de momento|hasta nuevo aviso|este mes|esta semana|hoy"
    r"|i'?m (?:leaving|in a hurry|in a meeting|about to|on my way|offline|busy)|in a hurry"
    r"|while we\b|until the \w+|mientras (?:dure|dura|estemos|tengamos|\w+mos)|\$\d+ (?:per|a) \w+|under \$\d+"
    r"|until (?:i (?:tell|say)|further|otherwise|told|next \w+|\w+day)|out of (?:tokens|credits|budget|quota)"
    r"|(?:is|are) (?:dead|gone|retired|deprecated|discontinued)|(?:switched|migrated) (?:away )?from"
    r"|(?:save|saving|cut|reduce) (?:money|tokens|credits|costs?)|cheap(?:er|est)? models?|budget under control"
    r"|too (?:expensive|costly|slow|verbose|long|chatty|much)|costs? too much|car[ií]simo|muy caro|demasiado caro"
    r"|right now|currently|anymore|any more|no longer|budget (?:is|are) (?:tight|low|limited)"
    r"|hates?|furious|angry|annoyed|frustrated|fed up|sick of|can'?t stand"
    r"|harto|harta|odia|odio|me molesta|me cansa|ya no)\b",
    re.IGNORECASE,
)

DATE_RE = re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b|\b(?:19|20)\d{2}\b")
REASON_RE = re.compile(
    r"\b(?:why|because|reason|user said|owner said|the user|budget|cost"
    r"|expensive|caro|tokens?|cr[eé]dito|tired|once|just this|porquer[ií]a)\b",
    re.IGNORECASE,
)
EXCEPTION_RE = re.compile(
    r"\b(?:unless|except|when the user|if the user|only if|as long as"
    r"|provided that|salvo|excepto|a menos que|cuando el usuario"
    r"|solo si|si el usuario)\b",
    re.IGNORECASE,
)
SCOPE_RE = re.compile(
    r"\b(?:for |in this|in the|when |during |only |subagents?|council"
    r"|sol-loop|this repo|this project|here|per |each |within )\b",
    re.IGNORECASE,
)


# Topics where a one-off comment most often fossilizes into a ban.
TOPIC_RE = re.compile(
    r"\b(?:opus|sonnet|haiku|fable|gpt|gemini|codex|devin|subagents?|delegate"
    r"|budget|cost|credits?|expensive|cheap\w*|quota|tokens?|cr[eé]ditos?|caro|presupuesto)\b",
    re.IGNORECASE,
)
STYLE_RE = re.compile(
    r"\b(?:verbose|wordy|concise|emoji|comments?|only reply|words)\b", re.IGNORECASE)
ISO_DATE_RE = re.compile(r"\b((?:19|20)\d{2})-(\d{2})-(\d{2})\b")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
STALE_AFTER_DAYS = 60
DURABLE_RE = re.compile(
    r"\b(?:security|secrets?|credentials?|policy|compliance|legal|license|production|CI|lint|privacy|gdpr)\b",
    re.IGNORECASE,
)


def kind_for(path: Path, kind_hint: str) -> str:
    parts = set(path.parts)
    if "memory" in parts:
        return "memory-index" if path.name == "MEMORY.md" else "memory"
    if "skills" in parts or path.name == "SKILL.md":
        return "skills"
    if "agents" in parts and any(p.startswith(".") for p in parts):
        return "agents"
    return kind_hint


def flags_for(text: str) -> dict:
    return {
        "has_date": bool(DATE_RE.search(text)),
        "has_reason": bool(REASON_RE.search(text)),
        "has_exception": bool(EXCEPTION_RE.search(text)),
        "maybe_scoped": bool(SCOPE_RE.search(text)),
    }


def age_days(text: str):
    """Age in days of the newest ISO date in text, or None."""
    best = None
    for y, m, d in ISO_DATE_RE.findall(text):
        try:
            dt = date(int(y), int(m), int(d))
        except ValueError:
            continue
        best = dt if best is None or dt > best else best
    return (date.today() - best).days if best else None


def window(lines: list, i: int) -> str:
    """The line plus its continuation lines (until blank or the next bullet)."""
    out = [lines[i]]
    for nxt in lines[i + 1:i + 3]:
        if not nxt.strip() or re.match(r"\s*(?:[-*+]|\d+[.)]|#)\s", nxt) and not nxt.startswith("  "):
            break
        out.append(nxt)
    return "\n".join(out)


IMPERATIVE_START = re.compile(
    r"^(?:please\s+)?(?:never|don'?t|do|dont|no|always|only|stop|avoid|keep|use|run|make|respond|answer|reply"
    r"|write|be|quit|skip|ask|limit|refrain|refuse|cap|treat|speak|delegate|default|set|put|add|remove|delete"
    r"|create|prefer|follow|check|confirm|forget|whatever|absolutely|from|until|under|max|nunca|jam[aá]s|siempre"
    r"|solo|responde|contesta|evita|usa|haz|deja|prohibido|sin|nada|habla|escribe|quiero|ya|por|nadie|zero)\b",
    re.IGNORECASE,
)
USER_VOICE = re.compile(
    r"\b(?:you|your|you're|i|i'm|i'll|i've|me|my|we|we're|we've|our|us|user|owner|founder"
    r"|yo|mi|mis|t[uú]|tus?|nosotros|usuario)\b",
    re.IGNORECASE,
)


def shape_of(line: str) -> str:
    """imperative / user (someone is speaking) / descriptive (states how something is).

    "The server never restarts during deploys." describes a system; it is not a
    rule for the agent, so it ranks below "Never restart the server."."""
    t = re.sub(r"^\s*(?:[-*+\u2022]|\d+[.)])?\s*(?:\*\*[^*]+\*\*:?\s*)?", "", line).strip()
    if IMPERATIVE_START.match(t):
        return "imperative"
    if USER_VOICE.search(t):
        return "user"
    return "descriptive"


def score_for(tier: int, flags: dict, harness: str, kind: str, text: str,
              topic: bool, style: bool, age, signals=(), shape="imperative") -> int:
    sc = 0
    if harness != "project":
        sc += 3          # global config binds every session
    if kind in ("agents", "skills"):
        sc -= 4          # authored task prompts, rarely a user dogma
    if tier == 1:
        sc += 1
    if "temporal" in signals:
        sc += 2          # the rule carries its own expiry date, unspoken
    sc += 3 if topic else (1 if style else 0)
    if not flags["has_exception"]:
        sc += 2
    else:
        sc -= 2
    if not flags["has_reason"] and not flags["has_date"]:
        sc += 1
    if flags["has_date"] and age is not None and age > STALE_AFTER_DAYS:
        sc += 1          # old enough that the world may have moved on
    if shape == "descriptive":
        sc -= 3          # states a fact about a system, not a rule for the agent
    if DURABLE_RE.search(text):
        sc -= 2          # a lasting reason (security, policy, CI), not a mood
    n = len(text)
    sc += 1 if n <= 160 else (-2 if n > 300 else 0)   # dogmas are short
    return sc


UNFLAGGED = []   # directive-shaped lines in global files that no pattern matched
RULE_FILES = {"CLAUDE.md", "AGENTS.md", "GEMINI.md", "QWEN.md", "global_rules.md"}
BULLET_RE = re.compile(r"^\s*(?:[-*+\u2022]|\d+[.)])\s+\S")


def keep_unflagged(path: Path, kind: str, line: str) -> bool:
    """Global files are short. A line no pattern matched can still be a dogma
    ("Speak like a pirate."), so hand it to the agent instead of dropping it."""
    t = line.strip()
    if len(t.split()) < 3 or t.startswith("#") or t.startswith("---") or t.startswith("|"):
        return False
    if kind in ("memory", "memory-index"):
        return not re.match(r"^(?:name|metadata|type):", t.lower())
    if path.name in RULE_FILES or kind == "rules":
        return not re.match(r"^[A-Za-z_-]+:\s", t) or t.lower().startswith("description:")
    return False


def scan_file(path: Path, harness: str, kind: str, findings: list, seen: set) -> None:
    try:
        real = path.resolve()
    except OSError:
        return
    if real in seen or not path.is_file():
        return
    seen.add(real)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    if not text.strip():
        return

    file_kind = kind_for(path, kind)
    file_has_exception = bool(EXCEPTION_RE.search(text))

    lines = text.splitlines()
    in_fence = False
    in_comment = False
    for i, line in enumerate(lines):
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if "<!--" in line:
            if "-->" not in line.split("<!--", 1)[1]:
                in_comment = True
            line = line.split("<!--", 1)[0]
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if re.match(r"^\s*(?:name|type|metadata|originSessionId)\s*:", line):
            continue          # frontmatter keys, not rules
        signals = []
        cleaned = IDIOMS.sub(" ", line)   # "never mind" is not a ban
        if TIER1_EN.search(cleaned) or TIER1_ES.search(cleaned) or BARE_NO.match(line):
            signals.append("ban")
        if TIER2.search(line) or ONLY_END.search(line):
            signals.append("absolute")
        if TEMPORAL.search(line):
            signals.append("temporal")
        if not signals:
            if harness != "project" and keep_unflagged(path, file_kind, line):
                UNFLAGGED.append({"harness": harness, "kind": file_kind, "path": str(path),
                                  "line": i + 1, "text": line.strip()[:300]})
            continue
        tier = 1 if "ban" in signals else 2
        win = window(lines, i)
        flags = flags_for(win)
        shape = shape_of(line)
        topic = bool(TOPIC_RE.search(win))
        style = bool(STYLE_RE.search(win))
        age = age_days(win)
        findings.append({
            "harness": harness,
            "kind": file_kind,
            "path": str(path),
            "line": i + 1,
            "tier": tier,
            "signals": signals,
            "shape": shape,
            "text": line.strip()[:300],
            "flags": flags,
            "file_has_exception": file_has_exception,
            "topic": topic,
            "age_days": age,
            "score": score_for(tier, flags, harness, file_kind, line.strip(), topic, style, age, signals, shape),
        })


def walk_docs(root: Path, harness: str, kind: str, findings: list, seen: set,
              only_skill_md: bool = False, skip_skills: bool = True) -> None:
    if not root.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in PRUNE_DIRS and not (skip_skills and d == "skills")
        ]
        for name in filenames:
            if only_skill_md and name != "SKILL.md":
                continue
            p = Path(dirpath) / name
            if p.suffix.lower() in SCAN_EXTS:
                scan_file(p, harness, kind, findings, seen)


def scan_claude_projects(findings: list, seen: set) -> None:
    base = HOME / ".claude" / "projects"
    if not base.is_dir():
        return
    for proj in base.iterdir():
        mem = proj / "memory"
        if mem.is_dir():
            for p in sorted(mem.glob("*.md")):
                scan_file(p, "claude-code", "memory", findings, seen)


def collect_harness_files(findings: list, seen: set, include_skills: bool) -> set:
    harnesses = set()
    for harness, kind, rel in HARNESS_TARGETS:
        path = HOME / rel
        if not path.exists():
            continue
        harnesses.add(harness)
        if path.is_file():
            scan_file(path, harness, kind, findings, seen)
        elif rel.endswith("/projects"):
            scan_claude_projects(findings, seen)
        else:
            walk_docs(path, harness, kind, findings, seen, skip_skills=not include_skills)
    if include_skills:
        for harness, rel in SKILLS_TARGETS:
            path = HOME / rel
            if path.is_dir():
                harnesses.add(harness)
                walk_docs(path, harness, "skills", findings, seen,
                          only_skill_md=True, skip_skills=False)
    return harnesses


def scan_project_dir(root: Path, findings: list, seen: set, max_depth: int) -> None:
    root = root.resolve()
    if not root.is_dir():
        return

    def recurse(d: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = list(d.iterdir())
        except OSError:
            return
        for e in entries:
            try:
                if e.is_dir():
                    if e.name in PROJECT_PRUNE_DIRS:
                        continue
                    if e.name.startswith(".") and e.name not in PROJECT_DOTDIRS:
                        continue
                    recurse(e, depth + 1)
                elif e.is_file():
                    name = e.name
                    suffix = e.suffix.lower()
                    in_dotdir = any(part in PROJECT_DOTDIRS for part in e.parts)
                    if name in PROJECT_FILES and (suffix in SCAN_EXTS or suffix == ""):
                        scan_file(e, "project", "project-rules", findings, seen)
                    elif (in_dotdir and suffix in SCAN_EXTS
                          and (suffix == ".mdc"
                               or any(part in CONFIG_SUBDIRS for part in e.parts))):
                        scan_file(e, "project", "project-rules", findings, seen)
            except OSError:
                continue

    recurse(root, 0)


STOP = set("""a an the and or of to in on for with without by at as is are be been this that these those
it its not no never do does don dont any all every each other another one only just use used using
user users always must should shall will would can could cannot may might from into than then so
if when unless except because since while also more most less than over under per via you your we our
i me my he she they them their there here what which who how why
description name metadata type feedback apply update""".split())


def _terms(text: str) -> set:
    """Distinctive words of a rule: lowercase, plural folded, no dates, no stopwords."""
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", text.lower())
    out = set()
    for w in re.findall(r"[a-z\u00e0-\u00ff][a-z\u00e0-\u00ff0-9-]{2,}", text):
        w = w.strip("-")
        if w.endswith("s") and len(w) > 4:
            w = w[:-1]
        if w not in STOP:
            out.add(w)
    return out


def cluster(findings: list) -> None:
    """Give the same rule, restated in several files, a shared cluster id.

    Two lines in different files join when they share at least two distinctive
    words and those words cover at least a third of the shorter line. Joins are
    transitive, so an index line, a description and a body line that each overlap
    a neighbour end up in one cluster.
    """
    terms = [_terms(f["text"]) for f in findings]
    parent = list(range(len(findings)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(findings)):
        if len(terms[i]) < 3:
            continue
        for j in range(i + 1, len(findings)):
            if len(terms[j]) < 3 or findings[i]["path"] == findings[j]["path"]:
                continue
            shared = len(terms[i] & terms[j])
            if shared >= 2 and shared / min(len(terms[i]), len(terms[j])) >= 0.3:
                parent[root(i)] = root(j)

    groups = {}
    for i in range(len(findings)):
        groups.setdefault(root(i), []).append(i)
    n = 0
    for members in groups.values():
        paths = {findings[i]["path"] for i in members}
        if len(members) > 1 and len(paths) > 1:
            n += 1
            for i in members:
                findings[i]["cluster"] = n
        else:
            for i in members:
                findings[i]["cluster"] = None


def fmt_flags(flags: dict) -> str:
    return " ".join(
        f"{label}:{'Y' if flags[key] else '-'}"
        for key, label in (("has_date", "date"), ("has_reason", "reason"),
                           ("has_exception", "exc"), ("maybe_scoped", "scope?"))
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    ap.add_argument("--no-projects", action="store_true",
                    help="skip the project-file sweep under $HOME")
    ap.add_argument("--project", action="append", default=[], metavar="PATH",
                    help="extra project root to scan (repeatable)")
    ap.add_argument("--depth", type=int, default=4,
                    help="max depth for project sweep (default 4)")
    ap.add_argument("--include-skills", action="store_true",
                    help="also scan SKILL.md files in harness skill dirs")
    ap.add_argument("--all-tiers", action="store_true",
                    help="include tier-2 hits (always/must/debe ...) in output")
    ap.add_argument("--unflagged", action="store_true",
                    help="also list global-config lines no pattern matched, so nothing hides behind the regexes")
    ap.add_argument("--unflagged-all", action="store_true",
                    help="with --unflagged, include memory file bodies too")
    ap.add_argument("--verbose", action="store_true",
                    help="list every directive line in project files (default: top few)")
    args = ap.parse_args()

    findings = []
    seen = set()
    harnesses = collect_harness_files(findings, seen, args.include_skills)

    project_roots = []
    if not args.no_projects:
        project_roots.append(HOME)
    project_roots.extend(Path(p).expanduser() for p in args.project)
    for root in project_roots:
        scan_project_dir(root, findings, seen, args.depth)

    if not args.all_tiers:
        # Global config is small: show every candidate. Project rule files are large and
        # mostly authored conventions: keep bans, and weaker hits only on risky topics.
        findings = [f for f in findings if f["tier"] == 1 or f["harness"] != "project"
                    or f["topic"] or "temporal" in f["signals"]]
    findings.sort(key=lambda f: (-f["score"], f["path"], f["line"]))
    cluster(findings)

    if args.json:
        print(json.dumps({
            "harnesses": sorted(harnesses),
            "files_with_findings": len({f["path"] for f in findings}),
            "findings": findings,
            "unflagged": UNFLAGGED,
        }, indent=2))
        return 0

    if not harnesses:
        print("No agent harness config dirs found under", HOME)
    else:
        print("Harnesses found: " + ", ".join(sorted(harnesses)))

    def short(p: str) -> str:
        return p.replace(str(HOME), "~", 1)

    glob = [f for f in findings if f["harness"] != "project"]
    proj = [f for f in findings if f["harness"] == "project"]

    print(f"\n== global config: {len(glob)} candidates, best first ==")
    for f in glob:
        mark = "!!" if f["tier"] == 1 and not f["flags"]["has_exception"] else "  "
        extra = []
        if f["cluster"]:
            extra.append(f"cluster#{f['cluster']}")
        if f["age_days"] is not None:
            extra.append(f"{f['age_days']}d old")
        if f["topic"]:
            extra.append("topic")
        print(f"  {mark} [{f['score']:>2}] {short(f['path'])}:{f['line']}  "
              f"[{fmt_flags(f['flags'])}] {' '.join(extra)}")
        print(f"        {f['text']}")

    by_file = {}
    for f in proj:
        by_file.setdefault(f["path"], []).append(f)
    print(f"\n== project rule files: {len(proj)} candidates in {len(by_file)} files ==")
    for path, hits in sorted(by_file.items(), key=lambda kv: -max(h["score"] for h in kv[1])):
        top = [h for h in hits if h["score"] >= 4 or h["topic"]]
        print(f"  {short(path)}: {len(hits)} directives, {len(top)} on risky topics")
        for h in (hits if args.verbose else top[:3]):
            print(f"      L{h['line']:<4} [{h['score']}] {h['text'][:140]}")

    if args.unflagged or args.unflagged_all:
        shown = [u for u in UNFLAGGED if args.unflagged_all or u["kind"] != "memory"]
        print(f"\n== global config lines no pattern matched: {len(shown)} ==")
        if not args.unflagged_all:
            print("   (memory bodies left out: --unflagged-all adds %d more lines)" % (len(UNFLAGGED) - len(shown)))
        for u in shown:
            print(f"  {short(u['path'])}:{u['line']}  {u['text'][:150]}")
    else:
        print(f"\n{len(UNFLAGGED)} more lines in global config matched no pattern (--unflagged lists rule files and memory indexes, --unflagged-all adds memory bodies).")
    print("\n!! = tier-1 absolute with no exception in its own lines. [score] ranks suspicion.")
    print("cluster#N = same rule restated in several files (fix together).")
    print("Flags are read from the line and its continuation lines. Open the file before judging.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
