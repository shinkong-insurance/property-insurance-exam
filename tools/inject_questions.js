#!/usr/bin/env node
/**
 * Obfuscate tools/data/questions.json the same way index.html's
 * deobfuscate() expects (XOR against the "PinsSecure2026!" key, then
 * base64) and splice it into index.html's `const QUESTIONS = ...` line.
 *
 * This is a lightweight copy deterrent only (see index.html's own
 * comment above the anti-copy code) — not real access control. The key
 * is intentionally kept in sync between here and index.html; if you
 * change one, change both.
 *
 * Usage:
 *   node tools/inject_questions.js [questions.json] [index.html]
 * Defaults: tools/data/questions.json, index.html
 */
const fs = require("fs");
const path = require("path");

const questionsPath = process.argv[2] || path.join(__dirname, "data", "questions.json");
const indexPath = process.argv[3] || path.join(__dirname, "..", "index.html");
const KEY = "PinsSecure2026!";

const questions = JSON.parse(fs.readFileSync(questionsPath, "utf8"));
const jsonStr = JSON.stringify(questions);
const bytes = Buffer.from(jsonStr, "utf8");
const out = Buffer.alloc(bytes.length);
for (let i = 0; i < bytes.length; i++) out[i] = bytes[i] ^ KEY.charCodeAt(i % KEY.length);
const b64 = out.toString("base64");

let html = fs.readFileSync(indexPath, "utf8");
const re = /const QUESTIONS = JSON\.parse\(deobfuscate\("([^"]+)"\)\);/;
if (!re.test(html)) {
  console.error(`could not find "const QUESTIONS = JSON.parse(deobfuscate(...))" in ${indexPath}`);
  process.exit(1);
}
html = html.replace(re, `const QUESTIONS = JSON.parse(deobfuscate("${b64}"));`);
fs.writeFileSync(indexPath, html);

console.log(`injected ${questions.length} questions into ${indexPath} (${b64.length} b64 chars)`);
