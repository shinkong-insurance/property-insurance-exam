#!/usr/bin/env python3
"""
Extract questions from a "產險業務員測驗題庫" exam-bank PDF (the vendor's
three-column layout: 答案 / 題目 / 解析) into structured JSON.

Usage:
    python3 tools/extract_pdf.py "保險實務、產險業務員測驗題庫YYYYMMDD.pdf" tools/out/practical.json

Requires: pip install pymupdf

How the PDF is structured (as of the 20260512 edition):
  - Each page has three x-position columns: answer tag (~x<85), question
    number+stem+options (~85<=x<400), and explanation (~x>=400).
  - Each question's answer tag "(A)"/"(B)"/"(C)"/"(D)" in column 1 sits at
    the topmost y-position of that question's row, so consecutive answer
    tags are used as row boundaries to slice columns 2 and 3.
  - Words on the same visual line can have several points of y-jitter
    (mixed baselines), which breaks a naive sort-by-(y,x) — so words are
    clustered into lines by y-proximity first, then ordered by x within
    each line.
  - The vendor embeds a lightweight anti-copy artifact: option labels are
    sometimes duplicated verbatim next to each other, e.g. "(A)(A)條款
    (B)(B)條款(C)(C)條款(D)以上皆是" instead of "(A)條款(B)條款(C)條款
    (D)以上皆是". These are collapsed automatically. A handful of
    instances in the 運輸保險 (cargo/ICC-clause) section have the
    duplication scrambled rather than clean (e.g. "(A)(C)...(C)(A)..."),
    which this script cannot safely auto-correct — see MANUAL_FIXES in
    build_questions.py for the ones found in the 20260512 edition.
"""
import fitz, re, json, sys

def extract_pdf(path, colA_max=85, colB_max=400):
    doc = fitz.open(path)
    rows = []
    for pno in range(len(doc)):
        page = doc[pno]
        words = page.get_text("words")  # x0,y0,x1,y1,text,block,line,wordno
        col1, col2, col3 = [], [], []
        for w in words:
            x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
            if y0 < 52 or y0 > 790:
                continue  # strip repeated page header/footer text
            if x0 < colA_max and re.match(r'^\([A-D]\)$', text):
                col1.append((y0, x0, x1, text))
            elif x0 < colB_max:
                col2.append((y0, x0, x1, text))
            else:
                col3.append((y0, x0, x1, text))
        col1.sort(key=lambda t: (t[0], t[1]))
        anchors = [c[0] for c in col1]
        answers = [c[3][1] for c in col1]  # the letter inside "(X)"
        n = len(anchors)

        def gather(colwords, lo, hi):
            items = [w for w in colwords if lo <= w[0] < hi]
            items.sort(key=lambda t: t[0])
            lines = []
            for it in items:
                placed = False
                for ln in lines:
                    if abs(it[0] - ln["y"]) < 6.0:
                        ln["items"].append(it)
                        ln["y"] = min(ln["y"], it[0])
                        placed = True
                        break
                if not placed:
                    lines.append({"y": it[0], "items": [it]})
            lines.sort(key=lambda ln: ln["y"])
            out = []
            for ln in lines:
                ln_items = sorted(ln["items"], key=lambda t: t[1])
                prev_x1 = None
                for (y0, x0, x1, text) in ln_items:
                    if prev_x1 is not None and (x0 - prev_x1) > 2.0:
                        out.append(" ")
                    out.append(text)
                    prev_x1 = x1
            return "".join(out)

        for i in range(n):
            lo = anchors[i] - 1.0
            hi = (anchors[i + 1] - 1.5) if i + 1 < n else 1e9
            raw_q = gather(col2, lo, hi)
            raw_expl = gather(col3, lo, hi)
            for _ in range(2):  # collapse "(X)(X)" anti-copy duplication
                raw_q = re.sub(r'\(([A-D])\)\s?\(\1\)', r'(\1)', raw_q)
                raw_expl = re.sub(r'\(([A-D])\)\s?\(\1\)', r'(\1)', raw_expl)
            rows.append({
                "page": pno + 1,
                "answer": answers[i],
                "raw_q": raw_q,
                "raw_expl": raw_expl,
            })
    return rows

def split_number(raw_q):
    m = re.match(r'^(\d+)\.\s*(.*)$', raw_q)
    if not m:
        return None, raw_q
    return int(m.group(1)), m.group(2)

def split_stem_options(text):
    """Split "<stem>(A)optA(B)optB(C)optC(D)optD" using a backward search
    from the last "(D)", so that stray "(A)"-style clause references
    inside the stem itself (e.g. "投保(A)條款者，...") don't get mistaken
    for the start of the option list. Falls back to a 3-option (A)(B)(C)
    split for the rare question that only has three choices."""
    posD = text.rfind("(D)")
    if posD == -1:
        posC = text.rfind("(C)")
        if posC == -1: return None
        posB = text.rfind("(B)", 0, posC)
        if posB == -1: return None
        posA = text.rfind("(A)", 0, posB)
        if posA == -1: return None
        stem = text[:posA].strip()
        optA = text[posA+3:posB].strip()
        optB = text[posB+3:posC].strip()
        optC = re.sub(r'[。\s]+$', '', text[posC+3:].strip())
        return stem, [optA, optB, optC]
    posC = text.rfind("(C)", 0, posD)
    if posC == -1: return None
    posB = text.rfind("(B)", 0, posC)
    if posB == -1: return None
    posA = text.rfind("(A)", 0, posB)
    if posA == -1: return None
    stem = text[:posA].strip()
    optA = text[posA+3:posB].strip()
    optB = text[posB+3:posC].strip()
    optC = text[posC+3:posD].strip()
    optD = re.sub(r'[。\s]+$', '', text[posD+3:].strip())
    return stem, [optA, optB, optC, optD]

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <input.pdf> <output.json>")
        sys.exit(1)
    path, outpath = sys.argv[1], sys.argv[2]
    rows = extract_pdf(path)
    results, errors = [], []
    for r in rows:
        num, rest = split_number(r["raw_q"])
        if num is None:
            errors.append({"reason": "no_number", **r})
            continue
        parsed = split_stem_options(rest)
        if parsed is None:
            errors.append({"reason": "no_options", "num": num, "rest": rest, **r})
            continue
        stem, options = parsed
        results.append({
            "source_no": num,
            "answer": r["answer"],
            "stem": stem,
            "options": options,
            "explanation": r["raw_expl"].strip(),
            "page": r["page"],
        })
    json.dump({"results": results, "errors": errors}, open(outpath, "w", encoding="utf-8"),
               ensure_ascii=False, indent=1)
    print(f"{path}: rows={len(rows)} parsed={len(results)} errors={len(errors)}")
    if errors:
        print(f"  !! {len(errors)} row(s) failed to parse — inspect '{outpath}' errors[] and fix manually.")
