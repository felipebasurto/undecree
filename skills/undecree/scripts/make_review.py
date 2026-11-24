#!/usr/bin/env python3
"""make_review — turn an undecree items.json into a self-contained review page.

One card per decree that needs a decision: the old rule, the proposed rewrite
(editable in place), and four choices. Healthy items never become cards; they
are folded into a collapsed "reviewed, fine" list. The page exports the
decisions as JSON to paste back to the agent.

Usage:
    make_review.py items.json [-o review.html] [--title T] [--lang es|en] [--open]

items.json schema (see SKILL.md):
{
  "title": "2026-11-24",                       // optional, shown in the header
  "lang": "es",                                // optional: es | en
  "items": [
    {"id": 1, "file": "~/.claude/CLAUDE.md", "line": 7,
     "rule": "Do not use Claude Opus ...",
     "context": "one sentence: why this is a problem",   // optional
     "outcome": "what happens in practice if the rule is deleted",   // optional
     "verdict": "fossil",                      // fossil|under-scoped|stale|file
     "suggested": "rescope",                   // keep|rescope|delete|review
     "proposal": "replacement text",           // optional, editable in the page
     "also": [{"file": "...", "line": 6, "proposal": "..."}]}  // same rule elsewhere
  ],
  "clean": [{"file": "...", "line": 5, "rule": "the line as written", "note": "why it is fine"}]    // reviewed, shown collapsed
}
"""

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

VERDICTS = ["fossil", "under-scoped", "stale", "file", "healthy"]
ACTIONS = ["keep", "rescope", "delete", "review"]
ALIASES = {"edit": "rescope"}

SKILL_DIR = Path(__file__).resolve().parent.parent
MARK_PATH = SKILL_DIR / "assets" / "mark.svg"
FALLBACK_MARK = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
                 '<rect x="6" y="36" width="52" height="22" rx="4" fill="#c8452c"/></svg>')

STRINGS = {
    "es": {
        "keep": "Mantener", "rescope": "Reescribir", "delete": "Eliminar",
        "review": "Investigar", "suggested": "sugerido",
        "fossil": "Fósil", "under-scoped": "Sin alcance", "stale": "Caducada",
        "file": "Archivo", "healthy": "Sana",
        "note": "+ nota", "notePh": "por qué, matiz…",
        "textPh": "Escribe el texto nuevo",
        "accept": "Aceptar sugeridos", "copy": "Copiar decisiones",
        "copied": "¡Copiado!", "of": "de", "decided": "decididas",
        "moreFiles": "archivos más", "moreFile": "archivo más",
        "clean": "revisados, sin problema", "cleanTitle": "Revisadas, sin problema",
        "cleanIntro": "Las marcó el escáner o las leí yo. Tienen alcance y motivo, o no son reglas: no hace falta decidir nada.",
        "edit": "Editar", "outHint": "Pega esto en el chat del agente.",
        "keys": "j/k mover · 1–4 elegir", "pendingWarn": "sin decidir: se omiten",
        "done": "Todo decidido", "heading": "Por decidir",
        "viewList": "Lista", "viewDeck": "Tarjetas", "undo": "Deshacer", "toList": "Ver lista",
        "keysDeck": "← eliminar · → mantener · ↑ reescribir · ↓ investigar · z deshacer",
        "now": "Ahora", "proposed": "Propuesta", "ifDelete": "Si lo borras", "suggestedIs": "Sugerido:",
    },
    "en": {
        "keep": "Keep", "rescope": "Rewrite", "delete": "Delete",
        "review": "Investigate", "suggested": "suggested",
        "fossil": "Fossil", "under-scoped": "Unscoped", "stale": "Stale",
        "file": "File", "healthy": "Healthy",
        "note": "+ note", "notePh": "why, nuance…",
        "textPh": "Write the new text",
        "accept": "Accept suggested", "copy": "Copy decisions",
        "copied": "Copied!", "of": "of", "decided": "decided",
        "moreFiles": "more files", "moreFile": "more file",
        "clean": "reviewed, all fine", "cleanTitle": "Reviewed, all fine",
        "cleanIntro": "The scanner flagged these or I read them. They have scope and a reason, or are not rules: nothing to decide.",
        "edit": "Edit", "outHint": "Paste this into the agent chat.",
        "keys": "j/k move · 1–4 choose", "pendingWarn": "undecided: skipped",
        "done": "All decided", "heading": "To decide",
        "viewList": "List", "viewDeck": "Cards", "undo": "Undo", "toList": "View list",
        "keysDeck": "← delete · → keep · ↑ rewrite · ↓ investigate · z undo",
        "now": "Now", "proposed": "Proposed", "ifDelete": "If you delete it", "suggestedIs": "Suggested:",
    },
}

TEMPLATE = r"""<!DOCTYPE html>
<html lang="{{LANG}}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>undecree · {{TITLE}}</title>
<meta name="color-scheme" content="dark">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600&display=swap">
<link rel="icon" href="data:image/svg+xml,{{FAVICON}}">
<style>
  /* flat on graphite: hairlines, soft fills, pastel pairs, no shadows */
  :root {
    color-scheme: dark;
    --ground:#27292d; --card:#303338; --ink:#f5f5f7; --soft-ink:#dfe1e6; --muted:#c4c7ce; --line:#454850;
    --soft:rgba(255,255,255,.08); --track:#22242a; --accent:#7ab8ff; --brand:#4fd08a;
    --del:#432820; --del-ink:#ffe3d8; --del-lab:#ffab97;
    --add:#1b3a2a; --add-ink:#d9f8e6; --add-lab:#7fe0a8;
    --keep-bg:#d9e8ff;  --keep-ink:#0b3d91;
    --rewrite-bg:#d9f3e4; --rewrite-ink:#14583a;
    --delete-bg:#f9dccb; --delete-ink:#5c2e1a;
    --look-bg:#fbefc8;  --look-ink:#5e4400;
    --sans:Figtree,-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif;
    --mono:ui-monospace,SFMono-Regular,Menlo,monospace;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--ground); color:var(--ink); font:400 16px/1.5 var(--sans); }
  button { font:inherit; color:inherit; cursor:pointer; }
  :focus-visible { outline:2px solid var(--accent); outline-offset:2px; }

  header { position:sticky; top:0; z-index:10; background:var(--ground); border-bottom:1px solid var(--line); }
  .bar { max-width:760px; margin:0 auto; padding:12px 20px; display:flex; align-items:center; gap:8px; }
  .brand { display:flex; align-items:center; gap:8px; margin-right:auto; }
  .brand svg { width:30px; height:30px; flex:none; margin:-2px -3px -4px; }
  .word { font:600 17px/1 var(--sans); letter-spacing:-.02em; }
  .word i { font-style:normal; color:var(--brand); }
  .pill { border:0; border-radius:999px; height:36px; padding:0 16px; font-size:14px; font-weight:500;
          background:var(--soft); color:var(--ink); transition:background .15s ease-out; }
  .pill:hover { background:rgba(255,255,255,.14); }
  .pill.primary { background:var(--rewrite-bg); color:var(--rewrite-ink); font-weight:600; }
  .pill.primary:hover { background:#c6ebd5; }

  main { max-width:760px; margin:0 auto; padding:28px 20px 72px; }
  .head { display:flex; align-items:baseline; justify-content:space-between; margin-bottom:16px; }
  h1 { margin:0; font:600 28px/1.2 var(--sans); letter-spacing:-.02em; }
  .count { font-size:14px; color:var(--muted); font-variant-numeric:tabular-nums; }

  .card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px; margin-bottom:12px; scroll-margin-top:84px; }
  .card.focus { border-color:var(--accent); }

  .meta { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:12px; }
  .tag { font:500 13px/1 var(--sans); padding:6px 10px; border-radius:999px; }
  .tag.fossil { background:var(--delete-bg); color:var(--delete-ink); }
  .tag.under-scoped { background:var(--look-bg); color:var(--look-ink); }
  .tag.stale { background:var(--keep-bg); color:var(--keep-ink); }
  .tag.file,.tag.healthy { background:var(--soft); color:var(--ink); }
  .where { font:12.5px var(--mono); color:var(--muted); word-break:break-all; }
  .where b { color:var(--ink); font-weight:600; }
  .link { background:none; border:0; padding:0; font-size:14px; color:var(--accent); }
  .link:hover { text-decoration:underline; text-underline-offset:3px; }
  .more { margin-left:auto; }

  .diff { display:grid; gap:8px; font:14px/1.55 var(--mono); }
  .ln { display:flex; flex-direction:column; gap:4px; padding:10px 12px 12px; border-radius:10px; }
  .ln .lab { font:600 12px/1.2 var(--sans); }
  .ln.del { background:var(--del); color:var(--del-ink); } .ln.del .lab { color:var(--del-lab); }
  .ln.add { background:var(--add); color:var(--add-ink); } .ln.add .lab { color:var(--add-lab); }
  .ln .tx { white-space:pre-wrap; word-break:break-word; min-width:0; }
  .card[data-action=delete] .ln.del .tx { text-decoration:line-through; text-decoration-color:var(--del-lab); }
  .card[data-action=keep] .ln.add, .card[data-action=delete] .ln.add,
  .card[data-action=review] .ln.add { opacity:.45; }
  .ln textarea { width:100%; min-width:0; background:transparent; color:inherit; border:0; outline:0;
          resize:none; font:inherit; padding:0; overflow:hidden; }
  .ln.add:focus-within { outline:2px solid var(--accent); outline-offset:0; }
  .ln.add[hidden] { display:none; }

  .why { color:var(--soft-ink); font-size:15px; margin:12px 0 0; }
  .outcome { margin:12px 0 0; padding:10px 12px 12px; border-radius:10px; background:var(--soft); }
  .outcome b { display:block; font:600 12px/1.2 var(--sans); color:var(--ink); margin-bottom:4px; }
  .outcome p { margin:0; font-size:15px; color:var(--ink); }
  .also { margin:8px 0 0; padding:0; list-style:none; font:12.5px var(--mono); color:var(--muted); }
  .also li { padding:2px 0; word-break:break-all; }
  .also[hidden] { display:none; }

  .choose { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-top:16px; }
  .seg { display:inline-flex; flex-wrap:wrap; padding:3px; border-radius:999px; background:var(--track); border:1px solid var(--line); }
  .hint { font-size:14px; color:var(--muted); }
  .opt { position:relative; border:0; background:transparent; color:var(--soft-ink); padding:0 16px; height:36px;
         border-radius:999px; font-size:15px; font-weight:500; white-space:nowrap;
         transition:background .15s ease-out, color .15s ease-out; }
  .opt:hover:not([aria-checked=true]) { background:var(--soft); color:var(--ink); }
  .opt[aria-checked=true] { font-weight:600; }
  .opt[aria-checked=true][data-a=keep] { background:var(--keep-bg); color:var(--keep-ink); }
  .opt[aria-checked=true][data-a=rescope] { background:var(--rewrite-bg); color:var(--rewrite-ink); }
  .opt[aria-checked=true][data-a=delete] { background:var(--delete-bg); color:var(--delete-ink); }
  .opt[aria-checked=true][data-a=review] { background:var(--look-bg); color:var(--look-ink); }
  .note-toggle { margin-left:auto; }
  textarea.note { display:block; width:100%; margin-top:12px; background:var(--soft); color:var(--ink);
         border:0; border-radius:8px; padding:10px 12px; font:15px/1.45 var(--sans); resize:vertical; min-height:42px; }
  textarea.note[hidden] { display:none; }

  details.clean { margin-top:28px; padding-top:8px; border-top:1px solid var(--line); }
  details.clean summary { cursor:pointer; padding:10px 0; font-size:15px; font-weight:600; color:var(--ink); }
  details.clean ul { margin:0; padding:0; list-style:none; }
  details.clean li { padding:12px 0; border-top:1px solid var(--line); }
  details.clean li.intro { border-top:0; padding:0 0 12px; color:var(--soft-ink); font-size:14px; }
  .cl-rule { margin:6px 0 0; padding:8px 10px; border-radius:8px; background:var(--soft); font:12.5px/1.5 var(--mono);
             color:var(--soft-ink); display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
  .cl-note { margin-top:6px; font-size:14px; color:var(--soft-ink); }
  #out { margin-top:20px; }
  #out[hidden] { display:none; }
  #out textarea { width:100%; min-height:200px; background:var(--soft); color:var(--ink); border:0;
         border-radius:8px; padding:12px; font:12px/1.45 var(--mono); }
  .foot { margin-top:28px; color:var(--muted); font-size:13px; text-align:center; }

  .tools { display:flex; align-items:center; gap:14px; }
  .views { padding:2px; }
  .vopt { border:0; background:transparent; color:var(--soft-ink); height:30px; padding:0 14px; border-radius:999px;
          font-size:14px; font-weight:500; }
  .vopt:hover:not([aria-checked=true]) { background:var(--soft); color:var(--ink); }
  .vopt[aria-checked=true] { background:rgba(255,255,255,.16); color:var(--ink); font-weight:600; }

  /* card view: swipe left delete, right keep, up rewrite, down investigate */
  #deck { display:none; max-width:560px; margin:0 auto; }
  body.v-deck #deck { display:block; }
  body.v-deck #items { display:none; }
  .stack { position:relative; padding-bottom:14px; }
  .dk { position:relative; z-index:1; overflow:hidden; background:var(--card); border:1px solid var(--line); border-radius:20px;
        padding:16px; cursor:grab; touch-action:none; user-select:none; -webkit-user-select:none; will-change:transform;
        animation:pop .2s ease-out; }
  .dk:active { cursor:grabbing; }
  @keyframes pop { from { transform:scale(.96); } to { transform:none; } }
  .dk.back { position:absolute; inset:0 0 14px 0; z-index:0; cursor:default; pointer-events:none; animation:none;
             transform-origin:50% 0; transform:translateY(14px) scale(.95); opacity:.55; }
  .dk textarea { user-select:text; -webkit-user-select:text; cursor:text; touch-action:auto; }
  .tint { position:absolute; inset:0; z-index:2; opacity:0; pointer-events:none; }
  .dk .more-files { margin:-4px 0 12px; font-size:14px; }
  .dk .more-files summary { cursor:pointer; color:var(--accent); }
  .dk .more-files ul { margin:6px 0 0; padding:0; list-style:none; font:12.5px var(--mono); color:var(--muted); }
  .dk .more-files li { padding:2px 0; word-break:break-all; }
  .ln .lab { display:flex; justify-content:space-between; align-items:center; }
  .ln .edit { background:none; border:0; padding:0; color:var(--add-ink); font:500 12px var(--sans);
              text-decoration:underline; text-underline-offset:3px; }
  .stamp { position:absolute; z-index:3; padding:9px 18px; border-radius:999px; font:600 20px/1 var(--sans);
           opacity:0; pointer-events:none; }
  .s-right { top:18px; left:18px; transform:rotate(-8deg); background:var(--keep-bg); color:var(--keep-ink); }
  .s-left { top:18px; right:18px; transform:rotate(8deg); background:var(--delete-bg); color:var(--delete-ink); }
  .s-up { top:18px; left:50%; margin-left:-60px; background:var(--rewrite-bg); color:var(--rewrite-ink); }
  .s-down { bottom:18px; left:50%; margin-left:-60px; background:var(--look-bg); color:var(--look-ink); }
  .dactions { display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-top:20px; }
  .big { border:0; border-radius:999px; height:48px; padding:0 22px; font:600 16px var(--sans); transition:filter .15s ease-out; }
  .big:hover { filter:brightness(.94); }
  .big.keep { background:var(--keep-bg); color:var(--keep-ink); }
  .big.rescope { background:var(--rewrite-bg); color:var(--rewrite-ink); }
  .big.delete { background:var(--delete-bg); color:var(--delete-ink); }
  .dsub { display:flex; gap:20px; justify-content:center; margin-top:14px; }
  .dsub .link[disabled] { color:var(--muted); cursor:default; text-decoration:none; opacity:.6; }
  .deckdone { text-align:center; padding:40px 20px; background:var(--card); border:1px solid var(--line); border-radius:20px; }
  .deckdone h2 { margin:0 0 6px; font:600 22px/1.3 var(--sans); letter-spacing:-.02em; }
  .deckdone p { margin:0 0 20px; color:var(--soft-ink); font-size:15px; }
  .deckdone .row { display:flex; gap:8px; justify-content:center; flex-wrap:wrap; }
  @media (prefers-reduced-motion: reduce) { .big, .vopt { transition:none; } .dk { animation:none; } }
</style>
</head>
<body>
<header>
  <div class="bar">
    <div class="brand">{{MARK}}<span class="word"><i>un</i>decree</span></div>
    <button class="pill" id="accept"></button>
    <button class="pill primary" id="copy"></button>
  </div>
</header>
<main>
  <div class="head"><h1 id="h1"></h1><div class="tools"><div class="seg views" role="radiogroup"><button type="button" role="radio" class="vopt" data-v="list"></button><button type="button" role="radio" class="vopt" data-v="deck"></button></div><span class="count" id="count"></span></div></div>
  <div id="items"></div>
  <div id="deck"></div>
  <details class="clean" id="clean" hidden><summary id="cleanSummary"></summary><ul id="cleanList"></ul></details>
  <div id="out" hidden><textarea id="outText" readonly></textarea><p class="foot" id="outHint"></p></div>
  <p class="foot" id="keys"></p>
</main>
<script>
const DATA = {{DATA}};
const T = DATA.t, ITEMS = DATA.items, CLEAN = DATA.clean;
const LS = "undecree:" + DATA.key;
const ACTIONS = ["keep","rescope","delete","review"];
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

let state = {};
try { state = JSON.parse(localStorage.getItem(LS) || "{}"); } catch (e) {}
const st = id => state[id] || (state[id] = {action:null, text:null, comment:"", note:false});
const save = () => { try { localStorage.setItem(LS, JSON.stringify(state)); } catch (e) {} };

function place(file, line) {
  const parts = file.split("/");
  const short = parts.length > 4 ? "…/" + parts.slice(-3).join("/") : file;
  const i = short.lastIndexOf("/");
  const head = esc(short.slice(0, i + 1)), base = esc(short.slice(i + 1));
  return `<span class="where" title="${esc(file)}">${head}<b>${base}</b>${line ? ":" + line : ""}</span>`;
}

function card(it) {
  const s = st(it.id);
  const opts = ACTIONS.map((a, i) =>
    `<button type="button" role="radio" class="opt"
      data-id="${it.id}" data-a="${a}" title="${i + 1}">${esc(T[a])}</button>`).join("");
  const also = (it.also || []);
  const alsoBtn = also.length
    ? `<button type="button" class="link more" data-more="${it.id}">+${also.length} ${also.length > 1 ? T.moreFiles : T.moreFile}</button>` : "";
  const alsoList = also.length
    ? `<ul class="also" id="also${it.id}" hidden>${also.map(a =>
        `<li>${esc(a.file)}${a.line ? ":" + a.line : ""}${a.proposal ? `<br>→ ${esc(a.proposal)}` : ""}</li>`).join("")}</ul>` : "";
  const text = s.text ?? it.proposal ?? "";
  return `<article class="card" id="c${it.id}" data-id="${it.id}">
    <div class="meta">${it.verdict ? `<span class="tag ${it.verdict}">${esc(T[it.verdict] || it.verdict)}</span>` : ""}
      ${place(it.file, it.line)}${alsoBtn}</div>
    <div class="diff">
      <div class="ln del"><span class="lab">${esc(T.now)}</span><span class="tx">${esc(it.rule)}</span></div>
      <div class="ln add" id="add${it.id}"><span class="lab">${esc(T.proposed)}</span><textarea rows="1" data-text="${it.id}" placeholder="${esc(T.textPh)}">${esc(text)}</textarea></div>
    </div>
    ${it.context ? `<p class="why">${esc(it.context)}</p>` : ""}${alsoList}
    ${it.outcome ? `<div class="outcome"><b>${esc(T.ifDelete)}</b><p>${esc(it.outcome)}</p></div>` : ""}
    <div class="choose"><div class="seg" role="radiogroup">${opts}</div>${it.suggested ? `<span class="hint">${esc(T.suggestedIs)} ${esc(T[it.suggested])}</span>` : ""}
      <button type="button" class="link note-toggle" data-note="${it.id}">${esc(T.note)}</button></div>
    <textarea class="note" id="note${it.id}" data-comment="${it.id}" placeholder="${esc(T.notePh)}" hidden>${esc(s.comment)}</textarea>
  </article>`;
}

function grow(t) { t.style.height = "auto"; t.style.height = t.scrollHeight + "px"; }

function sync() {
  let done = 0;
  ITEMS.forEach(it => {
    const s = st(it.id), c = $("c" + it.id);
    if (s.action) done++;
    c.dataset.action = s.action || "";
    c.querySelectorAll(".opt").forEach(b => b.setAttribute("aria-checked", b.dataset.a === s.action));
    $("add" + it.id).hidden = !(it.proposal || s.text || s.action === "rescope");
    const n = $("note" + it.id);
    n.hidden = !(s.note || s.comment);
  });
  const total = ITEMS.length;
  $("count").textContent = done === total && total ? T.done : `${done} ${T.of} ${total}`;
  document.querySelectorAll(".ln.add textarea").forEach(grow);
}

function choose(id, a) { st(id).action = a; save(); sync(); }

function decisions() {
  return ITEMS.map(it => {
    const s = st(it.id), a = s.action || "pending";
    const d = {id: it.id, file: it.file, line: it.line ?? null, verdict: it.verdict || "",
               action: a, text: a === "rescope" ? (s.text ?? it.proposal ?? "") : "",
               comment: s.comment || ""};
    if (it.also && it.also.length) d.also = it.also.map(x => ({file: x.file, line: x.line ?? null}));
    return d;
  });
}

async function copyOut() {
  const json = JSON.stringify({decisions: decisions()}, null, 2);
  const pending = ITEMS.filter(it => !st(it.id).action).length;
  let ok = false;
  try { await navigator.clipboard.writeText(json); ok = true; } catch (e) {}
  if (!ok) {
    $("out").hidden = false; $("outText").value = json; $("outHint").textContent = T.outHint;
    $("outText").select();
    try { ok = document.execCommand("copy"); } catch (e) {}
  }
  const b = $("copy"), prev = T.copy;
  b.textContent = ok ? T.copied + (pending ? ` (${pending} ${T.pendingWarn})` : "") : prev;
  setTimeout(() => b.textContent = prev, 2200);
}

function build() {
  $("items").innerHTML = ITEMS.map(card).join("");
  $("h1").textContent = T.heading; $("accept").textContent = T.accept; $("copy").textContent = T.copy; $("keys").textContent = T.keys;
  document.querySelectorAll(".vopt").forEach(b => b.textContent = b.dataset.v === "deck" ? T.viewDeck : T.viewList);
  if (CLEAN.length) {
    $("clean").hidden = false;
    $("cleanSummary").textContent = `${T.cleanTitle} · ${CLEAN.length}`;
    $("cleanList").innerHTML = `<li class="intro">${esc(T.cleanIntro)}</li>` + CLEAN.map(c => {
      const o = typeof c === "string" ? {file: c} : c;
      const where = !o.file ? "" : /^\S+$/.test(o.file) ? place(o.file, o.line) : `<span class="where">${esc(o.file)}</span>`;
      return `<li>${where}${o.rule ? `<div class="cl-rule">${esc(o.rule)}</div>` : ""}${o.note ? `<div class="cl-note">${esc(o.note)}</div>` : ""}</li>`;
    }).join("");
  }
  sync();
  setView(view);
}

document.addEventListener("click", e => {
  const o = e.target.closest(".opt"); if (o) { choose(+o.dataset.id, o.dataset.a); focusCard(+o.dataset.id, false); return; }
  const m = e.target.closest("[data-more]"); if (m) { const l = $("also" + m.dataset.more); l.hidden = !l.hidden; return; }
  const n = e.target.closest("[data-note]");
  if (n) { const id = +n.dataset.note; st(id).note = true; save(); sync(); $("note" + id).focus(); return; }
  const c = e.target.closest(".card"); if (c) focusCard(+c.dataset.id, false);
});
document.addEventListener("input", e => {
  const t = e.target;
  if (t.dataset.text) {
    const s = st(+t.dataset.text); s.text = t.value; s.action = "rescope"; save(); sync();
  } else if (t.dataset.comment) {
    st(+t.dataset.comment).comment = t.value; save();
  }
});
$("accept").onclick = () => {
  ITEMS.forEach(it => { const s = st(it.id); if (!s.action) s.action = it.suggested || "review"; });
  save(); sync();
  if (view === "deck") { pos = firstUndecided(); renderDeck(); }
};
$("copy").onclick = copyOut;

/* ---- card view ---- */
let view = "list", pos = 0, hist = [], drag = null, busy = false, wh = null, lockUntil = 0;
try { if (localStorage.getItem(LS + ":view") === "deck") view = "deck"; } catch (e) {}
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const TH = 110;
const TINT = {right: "122,184,255", left: "255,171,151", up: "127,224,168", down: "251,239,200"};
const firstUndecided = () => { const i = ITEMS.findIndex(it => !st(it.id).action); return i < 0 ? ITEMS.length : i; };
const actionFor = (it, dir) => dir === "left" ? "delete" : dir === "right" ? "keep"
  : dir === "up" ? (it.proposal ? "rescope" : "review") : "review";
const dirOfAction = a => ({delete: "left", keep: "right", rescope: "up", review: "down"})[a];
const head = it => `<div class="meta">${it.verdict ? `<span class="tag ${it.verdict}">${esc(T[it.verdict] || it.verdict)}</span>` : ""}${place(it.file, it.line)}</div>`;

function deckBack(it) {
  return `<div class="dk back" aria-hidden="true">${head(it)}<div class="diff"><div class="ln del"><span class="lab">${esc(T.now)}</span><span class="tx">${esc(it.rule)}</span></div></div></div>`;
}

function deckCard(it) {
  const s = st(it.id), text = s.text ?? it.proposal ?? "", also = it.also || [];
  const up = it.proposal ? T.rescope : T.review;
  return `<article class="dk" data-id="${it.id}"><div class="tint"></div>
    <span class="stamp s-right">${esc(T.keep)}</span><span class="stamp s-left">${esc(T.delete)}</span>
    <span class="stamp s-up">${esc(up)}</span><span class="stamp s-down">${esc(T.review)}</span>
    ${head(it)}
    ${also.length ? `<details class="more-files"><summary>+${also.length} ${also.length > 1 ? T.moreFiles : T.moreFile}</summary><ul>${also.map(a =>
      `<li>${esc(a.file)}${a.line ? ":" + a.line : ""}</li>`).join("")}</ul></details>` : ""}
    <div class="diff">
      <div class="ln del"><span class="lab">${esc(T.now)}</span><span class="tx">${esc(it.rule)}</span></div>
      ${it.proposal ? `<div class="ln add"><span class="lab">${esc(T.proposed)}<button type="button" class="edit" data-dedit="${it.id}">${esc(T.edit)}</button></span><span class="tx" data-ptx="${it.id}">${esc(text)}</span></div>` : ""}
    </div>
    ${it.context ? `<p class="why">${esc(it.context)}</p>` : ""}
    ${it.outcome ? `<div class="outcome"><b>${esc(T.ifDelete)}</b><p>${esc(it.outcome)}</p></div>` : ""}
    <textarea class="note" data-comment="${it.id}" placeholder="${esc(T.notePh)}" ${s.comment ? "" : "hidden"}>${esc(s.comment)}</textarea>
    <div class="dsub" style="margin-top:12px"><button type="button" class="link" data-dnote="1">${esc(T.note)}</button></div>
  </article>`;
}

function renderDeck() {
  const d = $("deck");
  if (pos >= ITEMS.length) {
    const n = {}; ITEMS.forEach(it => { const a = st(it.id).action; if (a) n[a] = (n[a] || 0) + 1; });
    const sum = ACTIONS.filter(a => n[a]).map(a => `${n[a]} ${T[a]}`).join(" · ");
    d.innerHTML = `<div class="deckdone"><h2>${esc(T.done)}</h2><p>${esc(sum)}</p>
      <div class="row"><button type="button" class="pill primary" data-dcopy="1">${esc(T.copy)}</button>
      <button type="button" class="pill" data-dlist="1">${esc(T.toList)}</button>
      ${hist.length ? `<button type="button" class="pill" data-undo="1">${esc(T.undo)}</button>` : ""}</div></div>`;
    return;
  }
  const it = ITEMS[pos], up = it.proposal ? T.rescope : T.review;
  d.innerHTML = `<div class="stack">${pos + 1 < ITEMS.length ? deckBack(ITEMS[pos + 1]) : ""}${deckCard(it)}</div>
    <div class="dactions">
      <button type="button" class="big delete" data-dir="left">← ${esc(T.delete)}</button>
      <button type="button" class="big rescope" data-dir="up">↑ ${esc(up)}</button>
      <button type="button" class="big keep" data-dir="right">${esc(T.keep)} →</button></div>
    <div class="dsub"><button type="button" class="link" data-dir="down">${esc(T.review)}</button>
      <button type="button" class="link" data-undo="1" ${hist.length ? "" : "disabled"}>${esc(T.undo)}</button></div>`;
}

function setView(v) {
  view = v;
  try { localStorage.setItem(LS + ":view", v); } catch (e) {}
  document.body.classList.toggle("v-deck", v === "deck");
  document.querySelectorAll(".vopt").forEach(b => b.setAttribute("aria-checked", b.dataset.v === v));
  $("keys").textContent = v === "deck" ? T.keysDeck : T.keys;
  if (v === "deck") { pos = firstUndecided(); hist = []; renderDeck(); }
  sync();
}

function commit(dir) {
  if (busy || pos >= ITEMS.length) return;
  const it = ITEMS[pos], a = actionFor(it, dir);
  const c = document.querySelector("#deck .dk:not(.back)");
  const go = () => { busy = false; choose(it.id, a); hist.push(pos); pos++; renderDeck(); };
  if (!c || reduce) { go(); return; }
  busy = true;
  const fx = dir === "left" ? -1 : dir === "right" ? 1 : 0, fy = dir === "up" ? -1 : dir === "down" ? 1 : 0;
  const m = /translate\(([-\d.]+)px,\s*([-\d.]+)px\)/.exec(c.style.transform || "");
  const x0 = m ? +m[1] : 0, y0 = m ? +m[2] : 0;
  c.style.animation = "none";
  c.style.transition = "transform .26s cubic-bezier(.3,.7,.4,1), opacity .26s ease-in";
  c.style.transform = `translate(${x0 + fx * innerWidth}px,${y0 + fy * innerHeight * .8}px) rotate(${fx * 22}deg)`;
  c.style.opacity = "0";
  const b = document.querySelector("#deck .dk.back");
  if (b) { b.style.transition = "transform .26s ease-out, opacity .26s ease-out"; b.style.transform = "none"; b.style.opacity = "1"; }
  setTimeout(go, 240);
}

function undo() {
  if (busy || !hist.length) return;
  pos = hist.pop(); st(ITEMS[pos].id).action = null; save(); sync(); renderDeck();
}

function dirOf(dx, dy) {
  if (Math.max(Math.abs(dx), Math.abs(dy)) < 12) return null;
  return Math.abs(dy) > Math.abs(dx) ? (dy < 0 ? "up" : "down") : (dx > 0 ? "right" : "left");
}
function startDrag(c, x, y, id) {
  const r = c.getBoundingClientRect(), back = $("deck").querySelector(".dk.back");
  drag = {c, back, x, y, dx: 0, dy: 0, id, sign: (y - r.top) < r.height / 2 ? 1 : -1, pts: []};
  c.style.animation = "none"; c.style.transition = "none";
  if (back) back.style.transition = "none";
}
function moveDrag(dx, dy) {
  const now = performance.now();
  drag.dx = dx; drag.dy = dy; drag.pts.push([now, dx, dy]);
  drag.pts = drag.pts.filter(p => now - p[0] < 120);
  const dir = dirOf(dx, dy), a = Math.min(1, Math.max(Math.abs(dx), Math.abs(dy)) / TH), c = drag.c;
  c.style.transform = `translate(${dx}px,${dy}px) rotate(${drag.sign * dx / 22}deg)`;
  c.querySelectorAll(".stamp").forEach(el => el.style.opacity = 0);
  const tint = c.querySelector(".tint");
  if (dir) {
    const el = c.querySelector(".s-" + dir); if (el) el.style.opacity = a;
    tint.style.background = `rgba(${TINT[dir]},.38)`; tint.style.opacity = a;
  } else tint.style.opacity = 0;
  if (drag.back) { drag.back.style.transform = `translateY(${14 * (1 - a)}px) scale(${.95 + .05 * a})`; drag.back.style.opacity = .55 + .45 * a; }
}
function endDrag(cancel) {
  if (!drag) return false;
  const d = drag; drag = null;
  const dir = dirOf(d.dx, d.dy), vert = dir === "up" || dir === "down";
  const dist = vert ? Math.abs(d.dy) : Math.abs(d.dx);
  const p = d.pts, v = p.length > 1 ? (vert ? (p[p.length - 1][2] - p[0][2]) : (p[p.length - 1][1] - p[0][1])) / ((p[p.length - 1][0] - p[0][0]) || 1) : 0;
  if (!cancel && dir && (dist >= TH || (dist >= 40 && Math.abs(v) > .6))) { commit(dir); return true; }
  d.c.style.transition = "transform .25s cubic-bezier(.3,1.4,.5,1)"; d.c.style.transform = "";
  d.c.querySelectorAll(".stamp").forEach(el => el.style.opacity = 0);
  const t = d.c.querySelector(".tint"); if (t) t.style.opacity = 0;
  if (d.back) { d.back.style.transition = "transform .25s ease-out, opacity .25s ease-out"; d.back.style.transform = ""; d.back.style.opacity = ""; }
  return false;
}
$("deck").addEventListener("pointerdown", e => {
  const c = e.target.closest(".dk:not(.back)");
  if (!c || busy || wh || e.button > 0 || e.target.closest("textarea,button,a,summary,input")) return;
  startDrag(c, e.clientX, e.clientY, e.pointerId);
  try { c.setPointerCapture(e.pointerId); } catch (err) {}
});
$("deck").addEventListener("pointermove", e => {
  if (!drag || e.pointerId !== drag.id) return;
  moveDrag(e.clientX - drag.x, e.clientY - drag.y);
});
$("deck").addEventListener("pointerup", e => { if (drag && e.pointerId === drag.id) endDrag(false); });
$("deck").addEventListener("pointercancel", () => endDrag(true));

/* trackpad / mouse wheel: two-finger swipe moves the card */
function endWheel() {
  if (!wh) return;
  clearTimeout(wh.t); wh = null;
  if (endDrag(false)) lockUntil = performance.now() + 700;   // swallow the trackpad's inertia events
}
document.addEventListener("wheel", e => {
  if (view !== "deck" || busy || pos >= ITEMS.length) return;
  const c = e.target.closest(".dk:not(.back)");
  if (!wh) {
    if (e.target.closest("textarea,details.clean,#out") || !e.target.closest("main")) return;
    if (!c && Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return;     // vertical scroll outside the card stays a scroll
  }
  e.preventDefault();
  if (performance.now() < lockUntil) return;
  const k = e.deltaMode === 1 ? 16 : 1;
  if (!wh) {
    const card = document.querySelector("#deck .dk:not(.back)"); if (!card) return;
    wh = {x: 0, y: 0, t: 0};
    startDrag(card, e.clientX, card.getBoundingClientRect().top + 1, -1);
  }
  wh.x -= e.deltaX * k; wh.y -= e.deltaY * k;     // the card follows the fingers
  moveDrag(wh.x, wh.y);
  clearTimeout(wh.t);
  const dist = Math.max(Math.abs(wh.x), Math.abs(wh.y));
  if (dist >= TH * 1.6) endWheel(); else wh.t = setTimeout(endWheel, 120);
}, {passive: false});

$("deck").addEventListener("click", e => {
  const b = e.target.closest("[data-dir]"); if (b) { commit(b.dataset.dir); return; }
  if (e.target.closest("[data-undo]")) { undo(); return; }
  if (e.target.closest("[data-dcopy]")) { copyOut(); return; }
  if (e.target.closest("[data-dlist]")) { setView("list"); return; }
  const ed = e.target.closest("[data-dedit]");
  if (ed) {
    const id = +ed.dataset.dedit, sp = $("deck").querySelector(`[data-ptx="${id}"]`);
    if (!sp) return;
    const ta = document.createElement("textarea");
    ta.rows = 1; ta.dataset.text = id; ta.placeholder = T.textPh; ta.value = sp.textContent;
    sp.replaceWith(ta); ed.remove(); grow(ta); ta.focus(); return;
  }
  if (e.target.closest("[data-dnote]")) { const n = $("deck").querySelector("textarea.note"); if (n) { n.hidden = false; n.focus(); } }
});
document.querySelectorAll(".vopt").forEach(b => b.onclick = () => setView(b.dataset.v));

let focused = null;
function focusCard(id, scroll = true) {
  document.querySelectorAll(".card.focus").forEach(c => c.classList.remove("focus"));
  const c = $("c" + id); if (!c) return;
  focused = id; c.classList.add("focus");
  if (scroll) c.scrollIntoView({behavior: "smooth", block: "center"});
}
document.addEventListener("keydown", e => {
  if (/^(TEXTAREA|INPUT)$/.test(e.target.tagName) || e.metaKey || e.ctrlKey || e.altKey) return;
  if (view === "deck") {
    const k = {ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down"}[e.key];
    if (k) { e.preventDefault(); commit(k); }
    else if (e.key === "z" || e.key === "Backspace") { e.preventDefault(); undo(); }
    else if ("1234".includes(e.key) && e.key.length === 1) commit(dirOfAction(ACTIONS[+e.key - 1]));
    return;
  }
  const ids = ITEMS.map(i => i.id), idx = ids.indexOf(focused);
  if (e.key === "j" || e.key === "ArrowDown") { e.preventDefault(); focusCard(ids[Math.min(idx + 1, ids.length - 1)]); }
  else if (e.key === "k" || e.key === "ArrowUp") { e.preventDefault(); focusCard(ids[Math.max(idx - 1, 0)]); }
  else if (focused != null && "1234".includes(e.key) && e.key.length === 1) {
    choose(focused, ACTIONS[+e.key - 1]);
    const next = ids.slice(idx + 1).find(i => !st(i).action);
    if (next != null) focusCard(next);
  }
});
build();
</script>
</body>
</html>
"""


def js(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def load_mark() -> str:
    try:
        svg = MARK_PATH.read_text(encoding="utf-8")
    except OSError:
        svg = FALLBACK_MARK
    return svg.strip()


def favicon(svg: str) -> str:
    flat = re.sub(r"var\(--\w+,\s*(#[0-9a-fA-F]+)\)", r"\1", svg)
    flat = re.sub(r"\s+", " ", flat)
    return (flat.replace("%", "%25").replace("#", "%23").replace("<", "%3C")
                .replace(">", "%3E").replace('"', "'"))


def pick_lang(cli, data) -> str:
    lang = cli or data.get("lang") or ""
    if not lang:
        env = os.environ.get("LC_ALL") or os.environ.get("LANG") or ""
        lang = "es" if env.lower().startswith("es") else "en"
    return lang if lang in STRINGS else "en"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("items", help="items.json produced during triage")
    ap.add_argument("-o", "--output", help="output HTML path (default: <items>.review.html)")
    ap.add_argument("--title", help="header subtitle (default: items.title or today's date)")
    ap.add_argument("--lang", choices=sorted(STRINGS), help="UI language (default: items.lang, then $LANG)")
    ap.add_argument("--open", action="store_true", help="open the page when done")
    args = ap.parse_args()

    src = Path(args.items).expanduser()
    data = json.loads(src.read_text(encoding="utf-8"))
    raw_items = data.get("items", [])
    clean = list(data.get("clean", []))

    items, seen = [], set()
    next_id = max([i.get("id", 0) for i in raw_items if isinstance(i.get("id"), int)] + [0]) + 1
    for it in raw_items:
        if it.get("verdict") == "healthy":
            # healthy never needs a decision: fold into the clean list
            clean.append({"file": it.get("file", ""), "line": it.get("line"), "rule": it.get("rule", ""),
                          "note": it.get("context", "")})
            print(f"note: healthy item at {it.get('file')} moved to 'clean'", file=sys.stderr)
            continue
        if "id" not in it or it["id"] in seen:
            if "id" in it:
                print(f"warning: duplicate id {it['id']}, renumbering", file=sys.stderr)
            it["id"] = next_id
            next_id += 1
        seen.add(it["id"])
        sug = ALIASES.get(it.get("suggested"), it.get("suggested"))
        it["suggested"] = sug if sug in ACTIONS else "review"
        it.setdefault("verdict", "")
        it.setdefault("proposal", "")
        it.setdefault("context", "")
        it.setdefault("line", None)
        it.setdefault("also", [])
        if it["verdict"] and it["verdict"] not in VERDICTS:
            print(f"warning: item {it['id']} verdict '{it['verdict']}' not in {VERDICTS}",
                  file=sys.stderr)
        items.append(it)

    if not items:
        print("nothing to review: no items need a decision", file=sys.stderr)
        return 1

    lang = pick_lang(args.lang, data)
    title = args.title or data.get("title") or date.today().isoformat()
    key_src = "|".join(f"{i['file']}:{i['line']}:{i['rule'][:40]}" for i in items)
    key = hashlib.sha1(key_src.encode()).hexdigest()[:10]

    mark = load_mark()
    subs = {
        "LANG": lang,
        "TITLE": html.escape(title),
        "FAVICON": favicon(mark),
        "MARK": mark,
        "DATA": js({"t": STRINGS[lang], "items": items, "clean": clean, "key": key}),
    }
    out_html = re.sub(r"\{\{(LANG|TITLE|FAVICON|MARK|DATA)\}\}",
                      lambda m: subs[m.group(1)], TEMPLATE)

    out = Path(args.output).expanduser() if args.output else src.with_suffix(".review.html")
    out.write_text(out_html, encoding="utf-8")
    print(f"{len(items)} to decide, {len(clean)} clean -> {out}")
    if args.open:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        try:
            subprocess.run([opener, str(out)], check=False)
        except OSError:
            print(f"open it manually: {out}")
    else:
        print(f'open it with: open "{out}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
