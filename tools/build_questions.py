#!/usr/bin/env python3
"""
Turn the two raw extract_pdf.py outputs (practical + regulation) into the
final categorized question set used by the site.

Usage:
    python3 tools/extract_pdf.py "保險實務、產險業務員測驗題庫YYYYMMDD.pdf" tools/out/practical.json
    python3 tools/extract_pdf.py "保險法規與理論 、產險業務員測驗題庫YYYYMMDD.pdf" tools/out/regulation.json
    python3 tools/build_questions.py tools/out/practical.json tools/out/regulation.json tools/data/questions.json

What this does:
  1. Applies MANUAL_FIXES for the handful of rows (usually in the 運輸保險
     cargo/ICC-clause section) where the vendor's anti-copy label
     duplication was scrambled rather than clean, so extract_pdf.py's
     automatic "(X)(X)" collapse couldn't recover the real text. These
     were found by reading the PDF's raw character stream by hand — see
     the git history of this file / the session that produced them for
     how each one was derived.
  2. Splits the practical-exam PDF into its 7 subject sections (each
     restarts its own question numbering at 1) and labels them by
     content order: 工程保險, 火災保險, 汽車保險, 健康保險, 責任保險,
     傷害保險, 運輸保險. IMPORTANT: this order is positional, not
     detected from any in-PDF heading — if a future edition reorders or
     adds/removes a subject section, `labels` below must be updated to
     match, or questions will be mislabeled.
  3. Puts every regulation-PDF row under a single "財產保險法規" category
     (the 20260512 edition merged what used to be a separate "財產保險
     理論" category into this file — the site's CATS entry for
     財產保險法規 has label:"財產保險法規與理論" to reflect that).
  4. Assigns final sequential `id`s in a fixed category order. NOTE: this
     means ids are NOT stable across a re-run/re-extraction if category
     sizes change — the site's localStorage keys (pins_wrong_v*,
     pins_fav_v*) must be version-bumped (see index.html's LS constant)
     whenever this script is re-run against a new edition, otherwise
     returning users' saved wrong-answer/favorite ids will point at the
     wrong question.
"""
import json, re, sys
from collections import Counter

MANUAL_FIXES = {
    # (source_file_tag, page, source_no): {stem, options}
    ('practical', 102, 4): {
        'stem': '在新式1982協會貨物保險條款中，下列何者對(B)條款之承保範圍敘述為正確：',
        'options': ['大於All Risks', '大於(C)條款', '小於(C)條款', '小於F.P.A條款'],
    },
    ('practical', 103, 11): {
        'stem': '就「短少」之損失，何種貨物運輸保險條款可予理賠',
        'options': ['協會條款', '協會條款', '協會條款', 'F.P.A條款'],
    },
    ('practical', 104, 23): {
        'stem': '新式1982協會貨物保險條款中，對承保之貨物因承保危險所致之「營業中斷損失」是否承保',
        'options': ['僅(A)條款承保', '(A)、(B)、(C)條款均不予承保', '僅兵險條款可承保', '以上皆非'],
    },
    ('practical', 104, 29): {
        'stem': '因民眾騷擾(Civil Commotions)所致之毀損是屬於下列何種協會貨物保險條款之承保項目：',
        'options': ['條款', '新式1982協會貨物兵險條款', '新式1982協會貨物罷工險條款', '條款'],
    },
    ('practical', 108, 82): {
        'stem': '魚粉(Fishmeal)進口，因該標的物如置於通風不良船艙內，容易引起自燃(Spontaneous Combustion)而致焦損，下列條款中何種協會貨物保險條款承保此種損失',
        'options': ['條款', '條款', '條款', '以上皆無'],
    },
}

PRACTICAL_SECTION_LABELS = ['工程保險', '火災保險', '汽車保險', '健康保險', '責任保險', '傷害保險', '運輸保險']
CAT_ORDER = ['財產保險法規', '火災保險', '汽車保險', '責任保險', '傷害保險', '健康保險', '工程保險', '運輸保險']

def apply_fixes(rows, tag):
    for r in rows:
        key = (tag, r['page'], r['source_no'])
        if key in MANUAL_FIXES:
            r['stem'] = MANUAL_FIXES[key]['stem']
            r['options'] = MANUAL_FIXES[key]['options']

def split_sections(rows):
    sections, cur = [], [rows[0]]
    for prev, r in zip(rows, rows[1:]):
        if r['source_no'] < prev['source_no']:
            sections.append(cur)
            cur = []
        cur.append(r)
    sections.append(cur)
    return sections

def main():
    if len(sys.argv) != 4:
        print(f"usage: {sys.argv[0]} <practical.json> <regulation.json> <output.json>")
        sys.exit(1)
    practical_path, regulation_path, out_path = sys.argv[1:4]

    practical = json.load(open(practical_path, encoding='utf-8'))['results']
    regulation = json.load(open(regulation_path, encoding='utf-8'))['results']

    apply_fixes(practical, 'practical')
    apply_fixes(regulation, 'regulation')

    practical_sections = split_sections(practical)
    if len(practical_sections) != len(PRACTICAL_SECTION_LABELS):
        print(f"!! expected {len(PRACTICAL_SECTION_LABELS)} practical sections, found "
              f"{len(practical_sections)} — update PRACTICAL_SECTION_LABELS to match "
              f"this edition's structure before trusting the output.")
        sys.exit(1)
    for sec, label in zip(practical_sections, PRACTICAL_SECTION_LABELS):
        for r in sec:
            r['category'] = label

    for r in regulation:
        r['category'] = '財產保險法規'
    for i, r in enumerate(regulation, start=1):
        r['source_no'] = i  # regulation PDF has 2 internal sections; renumber continuously

    all_rows = practical + regulation
    all_rows.sort(key=lambda r: (CAT_ORDER.index(r['category']), r['source_no']))

    questions = []
    for i, r in enumerate(all_rows, start=1):
        questions.append({
            'id': i,
            'category': r['category'],
            'source_no': r['source_no'],
            'answer': r['answer'],
            'stem': r['stem'],
            'options': r['options'],
            'explanation': r['explanation'],
        })

    cat_counts = Counter(q['category'] for q in questions)
    print("total:", len(questions))
    for c in CAT_ORDER:
        print(" ", c, cat_counts[c])

    bad = [q for q in questions if not q['stem'].strip() or len(q['options']) < 3 or not q['answer']]
    if bad:
        print(f"!! {len(bad)} suspect row(s) — inspect before publishing:")
        for q in bad[:20]:
            print("  ", q)

    flagged = [q for q in questions if any(re.search(r'\([A-D]\)', o) for o in q['options'])]
    if flagged:
        print(f"note: {len(flagged)} question(s) have an option containing a literal "
              f"'(A)'-style marker — usually legitimate (an option referencing another "
              f"clause by letter), but worth a manual skim after a re-extraction:")
        for q in flagged:
            print("  ", q['id'], q['category'], q['source_no'], q['stem'][:30])

    json.dump(questions, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"wrote {out_path}")

if __name__ == '__main__':
    main()
