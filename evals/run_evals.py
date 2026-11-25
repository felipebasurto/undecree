#!/usr/bin/env python3
"""Evals for the undecree scripts. Stdlib only, Python 3.9+.

    python3 evals/run_evals.py            # run everything, print the report
    python3 evals/run_evals.py --json     # machine-readable result
    python3 evals/run_evals.py -v         # list every case, not only failures

Suites
  scanner   build a fake $HOME from corpus.py, run find_dogmas.py --json on it and
            score detection (recall), ranking (candidates above healthy text),
            exclusions (fences, skills, node_modules, depth), clusters, line-level
            flags and age.
  page      feed make_review.py hostile and edge-case items.json files and check
            the generated HTML (payload integrity, healthy folding, ids, i18n,
            syntax of the embedded script).

Exit code 1 if a threshold fails, so it can gate a change.
"""

import argparse
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
SCRIPTS = REPO_ROOT / "skills" / "undecree" / "scripts"
sys.path.insert(0, str(HERE))
import corpus  # noqa: E402

TOP_K = 40          # how many global findings the agent is expected to read
MIN_RECALL = 1.0    # every labelled dogma must be found
MIN_TOP_RECALL = 1.0
MIN_AUC = 0.9       # candidates should outrank healthy text (main corpus only)
MIN_HOLDOUT_RECALL = 0.85   # folded holdout rounds are regression suites


def run(cmd, home=None, **kw):
    env = dict(os.environ)
    if home:
        env["HOME"] = str(home)
    return subprocess.run(cmd, env=env, capture_output=True, text=True, **kw)


# --------------------------------------------------------------------------- scanner

def match_key(case):
    if case.get("match"):
        return case["match"]
    first = case["text"].splitlines()[0].strip()
    return first[2:] if first.startswith("- ") else first


def find(findings, case):
    key = match_key(case)
    hits = [f for f in findings if f["path"].endswith(case["file"]) and key in f["text"]]
    return hits[0] if hits else None


def scanner_suite(today, case_fn=None):
    tmp = Path(tempfile.mkdtemp(prefix="undecree-eval-"))
    try:
        cases = corpus.build(tmp, today, case_fn)
        res = run([sys.executable, "-I", str(SCRIPTS / "find_dogmas.py"), "--json"], home=tmp)
        if res.returncode != 0:
            return {"error": res.stderr[-800:]}, []
        data = json.loads(res.stdout)
        findings = data["findings"]
        unflagged = data.get("unflagged", [])
        # rank = position in the order the agent reads: global first, then project
        glob = [f for f in findings if f["harness"] != "project"]
        glob.sort(key=lambda f: -f.get("score", 0))
        rank = {id(f): i + 1 for i, f in enumerate(glob)}

        rows = []
        for c in cases:
            f = find(findings, c)
            u = find(unflagged, c) if not f else None
            rows.append({"case": c, "finding": f, "unflagged": bool(u),
                         "rank": rank.get(id(f)) if f else None})

        cand = [r for r in rows if r["case"]["label"] == "candidate"]
        clean_rows = [r for r in rows if r["case"]["label"] == "clean"]
        low = [r for r in rows if r["case"]["label"] == "low"]
        excl = [r for r in rows if r["case"]["label"] == "excluded"]

        found = [r for r in cand if r["finding"]]
        covered = [r for r in cand if r["finding"] or r["unflagged"]]
        glob_files = lambda r: not r["case"]["file"].startswith("Proyectos/")
        glob_all = [r for r in cand + [x for x in rows if x["case"]["label"] == "hard"] if glob_files(r)]
        glob_covered = [r for r in glob_all if r["finding"] or r["unflagged"]]
        glob_cand = [r for r in cand if r["finding"] and r["finding"]["harness"] != "project"]
        top = [r for r in glob_cand if r["rank"] <= TOP_K]
        proj_cand = [r for r in cand if r["case"]["file"].startswith("Proyectos/")]
        proj_found = [r for r in proj_cand if r["finding"]]

        # pairwise ranking: candidate score vs healthy score, same scope
        pairs = good = 0
        for a, b in itertools.product(cand, low):
            fa, fb = a["finding"], b["finding"]
            if not fa or not fb:
                continue
            if (fa["harness"] == "project") != (fb["harness"] == "project"):
                continue
            pairs += 1
            good += 1 if fa["score"] > fb["score"] else (0.5 if fa["score"] == fb["score"] else 0)
        auc = good / pairs if pairs else 1.0

        pairs2 = good2 = 0
        for a, b in itertools.product(cand, clean_rows):
            fa, fb = a["finding"], b["finding"]
            if not fa or not fb:
                continue
            pairs2 += 1
            good2 += 1 if fa["score"] > fb["score"] else (0.5 if fa["score"] == fb["score"] else 0)
        clean_auc = good2 / pairs2 if pairs2 else 1.0
        leaks = [r for r in excl if r["finding"]]
        hard = [r for r in rows if r["case"]["label"] == "hard"]
        clean = [r for r in rows if r["case"]["label"] == "clean"]
        fp = [r for r in clean if r["finding"]]

        checks = []

        def check(name, ok, detail=""):
            checks.append({"name": name, "ok": bool(ok), "detail": detail})

        # clusters: every case with the same tag shares one non-null id; tags differ
        by_tag = {}
        for r in rows:
            tag = r["case"].get("cluster")
            if tag and r["finding"]:
                by_tag.setdefault(tag, []).append(r["finding"].get("cluster"))
        for tag, ids in by_tag.items():
            n = len([r for r in rows if r["case"].get("cluster") == tag])
            check("cluster '%s' groups all %d restatements" % (tag, n),
                  len(ids) == n and None not in ids and len(set(ids)) == 1, "ids=%s" % ids)
        tagged = {r["finding"]["cluster"] for r in rows
                  if r["case"].get("cluster") and r["finding"] and r["finding"].get("cluster")}
        stray = [r["case"]["id"] for r in rows if r["finding"] and r["finding"].get("cluster") in tagged
                 and not r["case"].get("cluster")]
        check("unrelated rules never join a cluster", not stray, "strays=%s" % stray)

        # line-level flags
        for r in rows:
            c, f = r["case"], r["finding"]
            if "exc" in c and f:
                check("exception flag for '%s' is %s" % (c["id"], c["exc"]),
                      f["flags"]["has_exception"] == c["exc"])
            if "age" in c and f:
                got = f.get("age_days")
                check("age_days for '%s' is about %d" % (c["id"], c["age"]),
                      got is not None and abs(got - c["age"]) <= 1, "got=%s" % got)

        # the top of the list should be dogmas, not healthy text
        top5 = sorted(glob, key=lambda f: -f["score"])[:5]
        healthy_keys = [match_key(r["case"]) for r in low]
        in_top5 = [f["text"][:50] for f in top5 if any(k in f["text"] for k in healthy_keys)]
        check("top 5 holds no healthy or authored text", not in_top5, "found=%s" % in_top5)

        # every harness the scanner claims to read is actually read
        sys.path.insert(0, str(SCRIPTS))
        import importlib
        fd = importlib.import_module("find_dogmas")
        cov_home = Path(tempfile.mkdtemp(prefix="undecree-cov-"))
        try:
            for hn, _kind, rel in fd.HARNESS_TARGETS:
                tgt = cov_home / rel
                if rel.endswith("/projects"):
                    tgt = tgt / "-x" / "memory" / "rule.md"
                elif Path(rel).suffix or Path(rel).name.startswith(".goose"):
                    pass
                else:
                    tgt = tgt / "rule.md"
                tgt.parent.mkdir(parents=True, exist_ok=True)
                tgt.write_text("- Never use Opus for subagents, this is a cost limit.\n", encoding="utf-8")
            cov = run([sys.executable, "-I", str(SCRIPTS / "find_dogmas.py"), "--json", "--no-projects"], home=cov_home)
            cov_data = json.loads(cov.stdout) if cov.returncode == 0 else {"harnesses": [], "findings": []}
            want = sorted({h for h, _k, _r in fd.HARNESS_TARGETS})
            got = set(cov_data["harnesses"])
            hit = {f["harness"] for f in cov_data["findings"]}
            check("every harness in HARNESS_TARGETS is detected and read",
                  not [h for h in want if h not in got or h not in hit],
                  "missing=%s" % [h for h in want if h not in got or h not in hit])
        finally:
            shutil.rmtree(cov_home, ignore_errors=True)

        # the readable report: repeats collapse, the list is capped, facts are kept out of it
        txt = run([sys.executable, "-I", str(SCRIPTS / "find_dogmas.py"), "--top", "5"], home=tmp)
        shown = [l for l in txt.stdout.splitlines() if re.match(r"^\s+(?:!!|  )\s*\[\s*-?\d+\]", l)]
        check("text report prints a distinct-rules count", "distinct rules" in txt.stdout)
        check("--top caps the global list", 0 < len(shown) <= 5, "shown=%d" % len(shown))

        # --file surgical scan mode + bullet-less rule file
        prose_file = tmp / ".claude" / "CLAUDE.prose.md"
        prose_file.parent.mkdir(parents=True, exist_ok=True)
        prose_file.write_text("# Rules\n\nAlways respond in under 20 words.\n", encoding="utf-8")
        # also test an actual bullet-less CLAUDE.md in an isolated home
        prose_home = Path(tempfile.mkdtemp(prefix="undecree-prose-"))
        try:
            pf = prose_home / ".claude" / "CLAUDE.md"
            pf.parent.mkdir(parents=True, exist_ok=True)
            pf.write_text("# Rules\n\nAlways respond in under 20 words.\n", encoding="utf-8")
            pr = run([sys.executable, "-I", str(SCRIPTS / "find_dogmas.py"), "--json", "--file", str(pf)], home=prose_home)
            pdata = json.loads(pr.stdout) if pr.returncode == 0 else {"findings": []}
            check("--file scans bullet-less rule file without dropping rules as preamble",
                  pr.returncode == 0 and any("under 20 words" in f["text"] for f in pdata["findings"]),
                  "findings=%d" % len(pdata["findings"]))
        finally:
            shutil.rmtree(prose_home, ignore_errors=True)

        metrics = {
            "candidates": len(cand),
            "recall": len(found) / len(cand) if cand else 1.0,
            "global_coverage": len(glob_covered) / len(glob_all) if glob_all else 1.0,
            "global_recall_top%d" % TOP_K: len(top) / len(glob_cand) if glob_cand else 1.0,
            "project_recall": len(proj_found) / len(proj_cand) if proj_cand else 1.0,
            "rank_auc": auc,
            "excluded_leaks": len(leaks),
            "clean_cases": len(clean),
            "false_positive_rate": len(fp) / len(clean) if clean else 0.0,
            "clean_auc": clean_auc,
            "checks_passed": sum(1 for c in checks if c["ok"]),
            "checks_total": len(checks),
            "findings_total": len(findings),
        }
        return {"metrics": metrics, "checks": checks, "leaks": [r["case"]["id"] for r in leaks],
                "missed": [r["case"]["id"] for r in cand if not r["finding"]],
                "false_positives": [r["case"]["id"] for r in fp],
                "hard_found": [r["case"]["id"] for r in hard if r["finding"]],
                "hard_missed": [r["case"]["id"] for r in hard if not r["finding"]],
                "hard_unflagged": [r["case"]["id"] for r in hard if r["unflagged"]],
                "uncovered": [r["case"]["id"] for r in glob_all if not (r["finding"] or r["unflagged"])],
                "outside_top": [r["case"]["id"] for r in glob_cand if r["rank"] > TOP_K]}, rows
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- page

def page_suite():
    tmp = Path(tempfile.mkdtemp(prefix="undecree-page-"))
    results = []

    def check(name, ok, detail=""):
        results.append({"name": name, "ok": bool(ok), "detail": detail})

    def build(obj, *args):
        src = tmp / "items.json"
        out = tmp / "out.html"
        src.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        r = run([sys.executable, str(SCRIPTS / "make_review.py"), str(src), "-o", str(out), *args])
        return r, (out.read_text(encoding="utf-8") if out.exists() else "")

    def payload(html):
        m = re.search(r"const DATA = (.*?);\nconst T = DATA", html, re.S)
        return json.loads(m.group(1)) if m else None

    try:
        hostile = "</script><img src=x onerror=alert(1)> {{DATA}} __DATA__   `${x}`"
        obj = {"title": "<b>t</b> & co", "items": [
            {"id": 1, "file": "~/a.md", "line": 3, "rule": hostile, "context": hostile,
             "verdict": "fossil", "suggested": "edit", "proposal": hostile,
             "also": [{"file": "~/b.md", "line": 1, "proposal": hostile}]},
            {"id": 1, "file": "~/c.md", "rule": "dup id", "verdict": "under-scoped", "suggested": "delete"},
            {"file": "~/ok.md", "rule": "healthy one", "verdict": "healthy", "context": "fine"},
            {"file": "~/d.md", "line": None, "rule": "whole file", "verdict": "file", "suggested": "bogus"},
        ], "clean": [{"file": "~/clean.md", "note": "ok"}]}
        r, html = build(obj, "--lang", "en")
        check("generator exits 0 on hostile input", r.returncode == 0, r.stderr[-200:])
        data = payload(html)
        check("DATA payload parses as JSON", data is not None)
        if data:
            items = data["items"]
            ids = [i["id"] for i in items]
            check("healthy item is folded into clean, not a card",
                  len(items) == 3 and any(c.get("file") == "~/ok.md" for c in data["clean"]))
            check("duplicate ids are renumbered", len(set(ids)) == len(ids), "ids=%s" % ids)
            check("'edit' suggestion becomes 'rescope'", items[0]["suggested"] == "rescope")
            check("unknown suggestion falls back to 'review'", items[-1]["suggested"] == "review")
            check("hostile text survives intact", items[0]["rule"] == hostile)
            check("English strings selected", data["t"]["keep"] == "Keep")
            check("both views and the clean section are in the page",
                  'id="deck"' in html and 'data-v="deck"' in html and 'data-v="list"' in html
                  and data["t"].get("cleanTitle") and data["t"].get("viewDeck"))
        check("only the one real </script> in the page", html.count("</script>") == 1,
              "count=%d" % html.count("</script>"))
        check("title is HTML-escaped", "<b>t</b>" not in html and "&lt;b&gt;t&lt;/b&gt;" in html)

        r, html = build({"items": [{"file": "x", "rule": "y", "verdict": "healthy"}]})
        check("all-healthy input stops with a clear message", r.returncode == 1 and "nothing to review" in r.stderr)

        r, html = build({"items": [{"file": "x", "rule": "y"}]}, "--lang", "es")
        d2 = payload(html)
        check("Spanish strings selected", d2 and d2["t"]["keep"] == "Mantener")

        r, html = build({"lang": "es", "items": [{"file": "x", "rule": "y"}]})
        check("lang from items.json is honoured", payload(html)["t"]["keep"] == "Mantener")

        # invalid ids, missing file/rule, hostile verdict
        r, html = build({"items": [
            {"id": "not-an-int", "rule": "missing file"},
            {"id": True, "file": "~/x.md", "verdict": 'bad" onclick="alert(1)'},
            {"id": 0, "file": "~/y.md", "rule": "zero id", "outcome": "something happens"},
        ]}, "--lang", "en")
        d3 = payload(html)
        check("non-int ids and missing fields normalize cleanly",
              r.returncode == 0 and d3 is not None
              and all(isinstance(i["id"], int) and not isinstance(i["id"], bool) and i["id"] > 0 for i in d3["items"])
              and len({i["id"] for i in d3["items"]}) == 3
              and d3["items"][1]["verdict"] == "")

        # the embedded script must at least parse
        if shutil.which("node"):
            r, html = build(obj, "--lang", "en")
            m = re.search(r"<script>(.*?)</script>", html, re.S)
            js = tmp / "page.js"
            js.write_text(m.group(1) if m else "", encoding="utf-8")
            c = run(["node", "--check", str(js)])
            check("embedded script passes node --check", c.returncode == 0, c.stderr[-200:])
        else:
            check("embedded script passes node --check (node missing, skipped)", True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return results


# --------------------------------------------------------------------------- repo / manifests

def repo_suite():
    """Validate skill spec, plugin manifests, version sync and local links."""
    results = []

    def check(name, ok, detail=""):
        results.append({"name": name, "ok": bool(ok), "detail": detail})

    skill_dir = REPO_ROOT / "skills" / "undecree"
    skill_md = skill_dir / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    fm, meta = {}, {}
    if m:
        in_meta = False
        for line in m.group(1).splitlines():
            if not line.strip():
                continue
            if line.startswith((" ", "\t")):
                if in_meta and ":" in line:
                    mk, mv = line.split(":", 1)
                    meta[mk.strip()] = mv.strip().strip('"').strip("'")
                continue
            in_meta = False
            if ":" in line:
                k, v = line.split(":", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                fm[k] = v
                if k == "metadata":
                    in_meta = True

    allowed_keys = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    check("SKILL.md has valid YAML frontmatter", bool(m) and set(fm).issubset(allowed_keys),
          "keys=%s" % sorted(fm))
    check("SKILL.md name matches directory", fm.get("name") == skill_dir.name, "name=%r" % fm.get("name"))
    desc = fm.get("description", "")
    check("SKILL.md description is non-empty and <= 1024 chars", 0 < len(desc) <= 1024, "len=%d" % len(desc))
    check("SKILL.md is <= 500 lines and <= 5000 approx tokens",
          len(text.splitlines()) <= 500 and len(text) // 4 <= 5000,
          "lines=%d tokens~%d" % (len(text.splitlines()), len(text) // 4))

    manifests = {}
    json_paths = [
        REPO_ROOT / "plugin.json",
        REPO_ROOT / ".claude-plugin" / "plugin.json",
        REPO_ROOT / ".claude-plugin" / "marketplace.json",
        REPO_ROOT / ".cursor-plugin" / "plugin.json",
        REPO_ROOT / "gemini-extension.json",
        REPO_ROOT / "examples" / "demo" / "items.json",
        REPO_ROOT / "evals" / "triggers.json",
    ]
    bad_json = []
    for jp in json_paths:
        try:
            manifests[jp.relative_to(REPO_ROOT).as_posix()] = json.loads(jp.read_text(encoding="utf-8"))
        except Exception as e:
            bad_json.append(f"{jp.name}: {e}")
    check("all JSON manifests, triggers and demo items parse cleanly", not bad_json, "; ".join(bad_json))

    if len(manifests) == len(json_paths):
        ap = manifests["plugin.json"]
        cp = manifests[".claude-plugin/plugin.json"]
        mp = manifests[".claude-plugin/marketplace.json"]
        cur = manifests[".cursor-plugin/plugin.json"]
        gem = manifests["gemini-extension.json"]
        trig = manifests["evals/triggers.json"]

        ap_allowed = {"$schema", "name", "version", "description", "author", "homepage", "repository", "license", "keywords", "extensions"}
        check("root plugin.json conforms to Agent Plugins 1.0 schema",
              ap.get("$schema") == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
              and set(ap).issubset(ap_allowed)
              and ap.get("name") == skill_dir.name,
              "keys=%s" % sorted(ap))
        versions = {
            "SKILL.md": meta.get("version"),
            "plugin.json": ap.get("version"),
            ".claude-plugin/plugin.json": cp.get("version"),
            ".cursor-plugin/plugin.json": cur.get("version"),
            "gemini-extension.json": gem.get("version"),
        }
        check("all manifests share the same semver version",
              len(set(versions.values())) == 1 and bool(re.fullmatch(r"\d+\.\d+\.\d+(?:[-+].+)?", str(cp.get("version", "")))),
              str(versions))
        mp_names = [p.get("name") for p in mp.get("plugins", [])]
        check("marketplace.json references plugin name and valid source dir",
              cp.get("name") in mp_names and all((REPO_ROOT / p.get("source", "")).resolve().is_dir() for p in mp.get("plugins", [])))
        cur_allowed = {"name", "description", "version", "author", "homepage", "repository", "license", "keywords", "logo", "rules", "agents", "skills", "commands", "hooks", "mcpServers", "variables"}
        check(".cursor-plugin/plugin.json uses official fields and existing paths",
              set(cur).issubset(cur_allowed)
              and (REPO_ROOT / cur.get("logo", "")).is_file()
              and (REPO_ROOT / cur.get("skills", "")).is_dir(),
              "extra=%s" % sorted(set(cur) - cur_allowed))
        check(".claude-plugin/plugin.json icon exists",
              not cp.get("icon") or (REPO_ROOT / cp["icon"]).is_file(),
              str(cp.get("icon")))
        seen_tids = set()
        bad_trig = []
        for c in trig:
            cid = c.get("id")
            if not cid or cid in seen_tids or not isinstance(c.get("query"), str) or not isinstance(c.get("should_trigger"), bool):
                bad_trig.append(str(cid))
            seen_tids.add(cid)
        pos_n = sum(1 for c in trig if c.get("should_trigger") is True)
        neg_n = sum(1 for c in trig if c.get("should_trigger") is False)
        check("evals/triggers.json is valid with positive and near-miss cases",
              not bad_trig and pos_n >= 3 and neg_n >= 3,
              f"pos={pos_n} neg={neg_n} bad={bad_trig}")

    # OpenAI Codex agents/openai.yaml checks
    oai_path = skill_dir / "agents" / "openai.yaml"
    oai = oai_path.read_text(encoding="utf-8") if oai_path.is_file() else ""
    sd_m = re.search(r'^\s*short_description:\s*"([^"]+)"\s*$', oai, re.M)
    dp_m = re.search(r'^\s*default_prompt:\s*"([^"]+)"\s*$', oai, re.M)
    il_m = re.search(r'^\s*icon_large:\s*"([^"]+)"\s*$', oai, re.M)
    sd = sd_m.group(1) if sd_m else ""
    dp = dp_m.group(1) if dp_m else ""
    check("agents/openai.yaml follows Codex constraints",
          25 <= len(sd) <= 64
          and f"${skill_dir.name}" in dp
          and (not il_m or (skill_dir / il_m.group(1)).is_file()),
          f"short_description_len={len(sd)} has_dollar={f'${skill_dir.name}' in dp}")

    broken = []
    md_files = [REPO_ROOT / "README.md", skill_md, skill_dir / "assets" / "BRAND.md",
                *sorted((skill_dir / "references").glob("*.md"))]
    for mf in md_files:
        content = mf.read_text(encoding="utf-8")
        for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", content):
            href = match.group(1).split("#", 1)[0]
            if not href or href.startswith(("http://", "https://")):
                continue
            if not (mf.parent / href).resolve().exists():
                broken.append(f"{mf.relative_to(REPO_ROOT)} -> {href}")
        for match in re.finditer(r'src="([^"]+)"', content):
            href = match.group(1)
            if href.startswith(("http://", "https://")):
                continue
            if not (mf.parent / href).resolve().exists():
                broken.append(f"{mf.relative_to(REPO_ROOT)} -> {href}")
    check("all local markdown links and image srcs resolve", not broken, "; ".join(broken))
    return results


# --------------------------------------------------------------------------- report

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--gate-holdout", action="store_true",
                    help="fail the run when the holdout suite misses a candidate")
    ap.add_argument("--suite", choices=["scanner", "holdout", "holdout2", "holdout3", "holdout4", "holdout5", "holdout6", "holdout7", "page", "repo", "all"], default="all")
    args = ap.parse_args()

    today = date.today()
    out = {}
    failed = []

    suites = (
        ("scanner", None), ("holdout", corpus.holdout), ("holdout2", corpus.holdout2),
        ("holdout3", corpus.holdout3), ("holdout4", corpus.holdout4),
        ("holdout5", corpus.holdout5), ("holdout6", corpus.holdout6), ("holdout7", corpus.holdout7),
    )
    for name, fn in suites:
        if args.suite not in (name, "all"):
            continue
        s, rows = scanner_suite(today, fn)
        out[name] = s
        out["_rows_" + name] = rows
        gate = name == "scanner" or args.gate_holdout
        if "error" in s:
            failed.append(name + " crashed")
            continue
        m = s["metrics"]
        problems = []
        floor = MIN_RECALL if name == "scanner" else MIN_HOLDOUT_RECALL
        if m["recall"] < floor:
            problems.append("recall %.0f%% < %.0f%%" % (100 * m["recall"], 100 * floor))
        if m["global_coverage"] < 1.0:
            problems.append("global coverage %.0f%%" % (100 * m["global_coverage"]))
        if m["global_recall_top%d" % TOP_K] < MIN_TOP_RECALL:
            problems.append("global recall in top %d too low" % TOP_K)
        if name == "scanner" and m["rank_auc"] < MIN_AUC:
            problems.append("ranking auc %.2f < %.2f" % (m["rank_auc"], MIN_AUC))
        if m["excluded_leaks"]:
            problems.append("%d excluded cases leaked" % m["excluded_leaks"])
        problems += ["check: " + c["name"] for c in s["checks"] if not c["ok"]]
        s["problems"] = problems
        if gate:
            failed += [name + ": " + p for p in problems]

    if args.suite in ("page", "all"):
        p = page_suite()
        out["page"] = p
        failed += ["page: " + c["name"] for c in p if not c["ok"]]

    if args.suite in ("repo", "all"):
        rp = repo_suite()
        out["repo"] = rp
        failed += ["repo: " + c["name"] for c in rp if not c["ok"]]

    out["failed"] = failed

    if args.json:
        for k in [k for k in out if k.startswith("_rows")]:
            out.pop(k)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 1 if failed else 0

    for name, _ in suites:
        rows = out.pop("_rows_" + name, [])
        if name not in out or "metrics" not in out[name]:
            continue
        s = out[name]
        m = s["metrics"]
        gated = name == "scanner" or args.gate_holdout
        print("%s%s  (%d labelled candidates, %d findings)" % (
            name.upper(), "" if gated else " (informational)", m["candidates"], m["findings_total"]))
        print("  recall                %5.1f%%   missed: %s" % (100 * m["recall"], ", ".join(s["missed"]) or "none"))
        print("  global coverage       %5.1f%%   (pattern hits + unflagged lines)   uncovered: %s" % (
            100 * m["global_coverage"], ", ".join(s["uncovered"]) or "none"))
        print("  global recall top %-3d %5.1f%%   outside: %s" % (TOP_K, 100 * m["global_recall_top%d" % TOP_K],
                                                                ", ".join(s["outside_top"]) or "none"))
        print("  project recall        %5.1f%%" % (100 * m["project_recall"]))
        print("  ranking (candidate > healthy) %.2f" % m["rank_auc"])
        print("  excluded leaks        %d   %s" % (m["excluded_leaks"], ", ".join(s["leaks"]) or ""))
        if m["clean_cases"]:
            print("  false positives       %5.1f%%   flagged: %s" % (
                100 * m["false_positive_rate"], ", ".join(s["false_positives"]) or "none"))
            print("  ranking (candidate > clean)   %.2f" % m["clean_auc"])
        if s["hard_found"] or s["hard_missed"]:
            print("  hard (no marker)      by pattern: %s   only via --unflagged: %s" % (
                ", ".join(s["hard_found"]) or "none", ", ".join(s["hard_unflagged"]) or "none"))
        print("  checks                %d/%d" % (m["checks_passed"], m["checks_total"]))
        for c in s["checks"]:
            if not c["ok"] or args.verbose:
                print("    %s %s %s" % ("ok " if c["ok"] else "FAIL", c["name"], c["detail"]))
        if args.verbose:
            print("\n  case                          label      found  rank  score  signals")
            for r in rows:
                c, f = r["case"], r["finding"]
                print("  %-29s %-10s %-6s %-5s %-6s %s" % (c["id"], c["label"], "yes" if f else "no",
                      r["rank"] or "-", f["score"] if f else "-", ",".join(f["signals"]) if f else ""))
        print()
    for label, key in (("PAGE", "page"), ("REPO", "repo")):
        if key in out:
            p = out[key]
            ok = sum(1 for c in p if c["ok"])
            print("\n%-8s %d/%d checks" % (label, ok, len(p)))
            for c in p:
                if not c["ok"] or args.verbose:
                    print("    %s %s %s" % ("ok " if c["ok"] else "FAIL", c["name"], c["detail"]))

    print("\n" + ("PASS" if not failed else "FAIL: " + "; ".join(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
