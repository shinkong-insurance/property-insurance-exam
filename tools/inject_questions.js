#!/usr/bin/env node
/**
 * Build the data blocks embedded in index.html:
 *
 *   const QUESTIONS = JSON.parse(deobfuscate("..."));   <- questions.json + enrich.json
 *   const LEARN = JSON.parse(deobfuscate("..."));       <- learn.json  (講義章節)
 *   const CARDS = JSON.parse(deobfuscate("..."));       <- cards.json  (數字速記卡)
 *   const FEATURED = JSON.parse(deobfuscate("..."));    <- featured.json (產險公司章節精選題)
 *
 * enrich.json ({ "<id>": { sec, exp, ex } }) holds our own explanations and
 * worked examples; it is merged onto the official question bank here so that
 * questions.json can stay a faithful copy of the 公會 PDF and be regenerated
 * by build_questions.py without losing the enrichment.
 *
 * Obfuscation = XOR against "PinsSecure2026!" then base64 (a light copy
 * deterrent only — see index.html). Keep the key in sync with index.html.
 *
 * Usage: node tools/inject_questions.js [index.html]
 */
const fs = require("fs");
const path = require("path");

const DATA = path.join(__dirname, "data");
const indexPath = process.argv[2] || path.join(__dirname, "..", "index.html");
const KEY = "PinsSecure2026!";

function readJSON(name, fallback) {
  const p = path.join(DATA, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf8")) : fallback;
}
function obfuscate(obj) {
  const bytes = Buffer.from(JSON.stringify(obj), "utf8");
  const out = Buffer.alloc(bytes.length);
  for (let i = 0; i < bytes.length; i++) out[i] = bytes[i] ^ KEY.charCodeAt(i % KEY.length);
  return out.toString("base64");
}

let questions = readJSON("questions.json");
const enrich = readJSON("enrich.json", {});
// corrections.json ({ "<id>": { stem?, options?, answer?, delete? } }): fixes from
// the 公會 勘誤表 (115.6 v3). Law changes the bank has NOT adopted go in current_law.json.
const corrections = readJSON("corrections.json", {});
let corrected = 0;
for (const q of questions) {
  const c = corrections[String(q.id)];
  if (!c) continue;
  if (c.stem) q.stem = c.stem;
  if (c.options) q.options = c.options;
  if (c.answer) q.answer = c.answer;
  corrected++;
}
// { "delete": true } = question removed by the 公會 勘誤表 (ids of the others stay unchanged)
const deleted = questions.filter(q => (corrections[String(q.id)] || {}).delete).length;
questions = questions.filter(q => !(corrections[String(q.id)] || {}).delete);
// current_law.json ({ "<id>": { note } }): questions whose 題庫 answer differs
// from current law. The question and answer stay as in the 公會 bank (that is
// what the exam grades); the current rule is shown as a separate note.
const currentLaw = readJSON("current_law.json", {});
let noted = 0;
for (const q of questions) {
  const n = currentLaw[String(q.id)];
  if (n && n.note) { q.note = n.note; noted++; }
}
let merged = 0;
for (const q of questions) {
  const e = enrich[String(q.id)];
  if (!e) continue;
  if (e.sec) q.sec = e.sec;
  if (e.exp) q.explanation = e.exp;
  if (e.ex) q.example = e.ex;
  merged++;
}
// featured.json: 產險公司提供的章節精選題（皆為題庫既有題目，只標記 id，不新增題目）
const featured = readJSON("featured.json", { sets: [] });
const byId = new Map(questions.map(q => [q.id, q]));
let featCount = 0;
for (const set of featured.sets) {
  set.ids = set.ids.filter(id => byId.has(id));
  for (const id of set.ids) { byId.get(id).feat = set.key; featCount++; }
  delete set.excluded; delete set.total_in_file;
}
const learn = readJSON("learn.json", []);
const cards = readJSON("cards.json", []);

let html = fs.readFileSync(indexPath, "utf8");
function splice(name, obj) {
  const re = new RegExp(`const ${name} = JSON\\.parse\\(deobfuscate\\("([^"]*)"\\)\\);`);
  if (!re.test(html)) {
    console.error(`could not find "const ${name} = JSON.parse(deobfuscate(...))" in ${indexPath}`);
    process.exit(1);
  }
  html = html.replace(re, () => `const ${name} = JSON.parse(deobfuscate("${obfuscate(obj)}"));`);
}
splice("QUESTIONS", questions);
splice("LEARN", learn);
splice("CARDS", cards);
splice("FEATURED", featured);
fs.writeFileSync(indexPath, html);

console.log(`injected ${questions.length} questions (${merged} enriched, ${corrected} corrected, ${deleted} deleted, ${noted} with current-law notes), ${featCount} featured in ${featured.sets.length} sets, ${learn.length} chapters, ${cards.length} cards into ${indexPath}`);
