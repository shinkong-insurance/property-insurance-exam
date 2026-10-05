#!/usr/bin/env python3
"""
把 tools/handout/*.md（講義原稿）轉成網站用的 tools/data/learn.json 與 tools/data/cards.json。

- 01~09 章：每章以 `## ` 標題切成小節，轉成 HTML（需要 pandoc）。
  章節代號 c1~c9、小節代號 c{章}s{節}，題目的 `sec` 欄位對應這些代號。
- 10_appendix.md：「常考數字速記」表格轉成翻卡資料。

用法：python3 tools/build_handout.py
完成後執行 node tools/inject_questions.js 把資料注入 index.html。
"""
import json, re, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "handout"
OUT = HERE / "data"

# 章節 → 題庫分類（第一、二章同屬「財產保險法規」）
CHAPTER_CAT = {
    "01": "財產保險法規", "02": "財產保險法規", "03": "火災保險", "04": "運輸保險",
    "05": "責任保險", "06": "工程保險", "07": "汽車保險", "08": "傷害保險", "09": "健康保險",
}

def md2html(md: str) -> str:
    return subprocess.run(
        ["pandoc", "-f", "markdown+fenced_divs+pipe_tables", "-t", "html5", "--wrap=none"],
        input=md, capture_output=True, text=True, check=True).stdout

def build_learn():
    chapters = []
    for f in sorted(SRC.glob("0[1-9]_*.md")):
        num = f.name[:2]
        text = f.read_text(encoding="utf-8")
        title = re.search(r"^# (.+)$", text, re.M).group(1).strip()
        body = re.sub(r"^# .+\n", "", text, count=1, flags=re.M)
        parts = re.split(r"^## ", body, flags=re.M)
        cid = f"c{int(num)}"
        sections = []
        for i, part in enumerate(p for p in parts[1:] if p.strip()):
            head, _, rest = part.partition("\n")
            sections.append({
                "id": f"{cid}s{i+1}",
                "title": head.strip(),
                "html": md2html(rest),
            })
        chapters.append({"id": cid, "cat": CHAPTER_CAT[num], "title": title, "sections": sections})
    return chapters

def build_cards():
    text = (SRC / "10_appendix.md").read_text(encoding="utf-8")
    cards, group = [], ""
    for line in text.splitlines():
        if line.startswith("## "):
            group = line[3:].strip()
        m = re.match(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|$", line)
        if not m or set(m.group(1)) <= set("-: ") or m.group(1) in ("數字",):
            continue
        num = re.sub(r"\*\*|<[^>]+>", "", m.group(1)).strip()
        for item in re.split(r"[；;]", re.sub(r"\*\*|<[^>]+>", "", m.group(2))):
            item = item.strip()
            if item:
                cards.append({"group": group, "q": item, "a": num})
    return cards

if __name__ == "__main__":
    learn = build_learn()
    cards = build_cards()
    (OUT / "learn.json").write_text(json.dumps(learn, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "cards.json").write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"learn: {len(learn)} 章 / {sum(len(c['sections']) for c in learn)} 節；cards: {len(cards)} 張")
