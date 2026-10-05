#!/usr/bin/env node
/**
 * Build the data blocks embedded in index.html:
 *
 *   const QUESTIONS = JSON.parse(deobfuscate("..."));   <- questions.json + enrich.json
 *   const LEARN = JSON.parse(deobfuscate("..."));       <- learn.json  (講義章節)
 *   const CARDS = JSON.parse(deobfuscate("..."));       <- cards.json  (數字速記卡)
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

const questions = readJSON("questions.json");
const enrich = readJSON("enrich.json", {});
let merged = 0;
for (const q of questions) {
  const e = enrich[String(q.id)];
  if (!e) continue;
  if (e.sec) q.sec = e.sec;
  if (e.exp) q.explanation = e.exp;
  if (e.ex) q.example = e.ex;
  merged++;
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
fs.writeFileSync(indexPath, html);

console.log(`injected ${questions.length} questions (${merged} enriched), ${learn.length} chapters, ${cards.length} cards into ${indexPath}`);
