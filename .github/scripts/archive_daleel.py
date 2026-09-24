#!/usr/bin/env python3
"""يطوي بطاقات malatya/daleel.html الأقدم من CUTOFF_DAYS إلى malatya/archive-YYYY-MM.html.
يعمل فقط داخل <!--DAILY-CONTENT-START/END-->، ولا يمسّ فصول الدليل الثابتة.
"""
import re
import sys
import os
from collections import defaultdict
from datetime import date, timedelta

DAYS = int(os.environ.get("ARCHIVE_AFTER_DAYS", "21"))
SRC = os.environ.get("DAILY_FILE", "malatya/daleel.html")
TODAY = os.environ.get("TODAY") or date.today().isoformat()

START_MARK = "<!--DAILY-CONTENT-START-->"
END_MARK = "<!--DAILY-CONTENT-END-->"

ITEM_OPEN_RE = re.compile(r'<div class="item" data-date="(\d{4}-\d{2}-\d{2})">')
H2_RE = re.compile(r'<h2><span class="sec-ico">(?P<icon>[^<]*)</span>\s*(?P<label>[^<]+?)\s*<span class="count">(?P<count>\d+)</span></h2>')


def balanced_end(html, idx):
    """idx يقع بعد '<div class=\"item\" ...>' مطابق بالفعل (عمق=1). يعيد فهرس نهاية </div> المطابقة."""
    depth = 1
    div_re = re.compile(r'<div\b|</div>')
    while depth > 0:
        m = div_re.search(html, idx)
        if not m:
            raise RuntimeError("وسم <div> غير متوازن أثناء استخراج بطاقة")
        depth += -1 if m.group(0) == '</div>' else 1
        idx = m.end()
    return idx


def extract_items(segment):
    items = []
    pos = 0
    while True:
        m = ITEM_OPEN_RE.search(segment, pos)
        if not m:
            break
        end = balanced_end(segment, m.end())
        items.append({"date": m.group(1), "block": segment[m.start():end],
                      "start": m.start(), "end": end})
        pos = end
    return items


def process(html, cutoff):
    if START_MARK not in html or END_MARK not in html:
        raise RuntimeError("لا علامتا DAILY-CONTENT — الملف ليس بالشكل المتوقّع")
    s = html.index(START_MARK) + len(START_MARK)
    e = html.index(END_MARK)
    region = html[s:e]

    h2_matches = list(H2_RE.finditer(region))
    if not h2_matches:
        raise RuntimeError("لا فصول <h2> داخل منطقة DAILY-CONTENT")

    leading = region[:h2_matches[0].start()]
    archived_by_month = defaultdict(list)  # "YYYY-MM" -> [(category_label, block), ...]
    total_before = 0
    total_kept = 0
    out_parts = []
    category_new_counts = []  # [(icon, label, new_count)]

    for i, hm in enumerate(h2_matches):
        chunk_start = hm.start()
        chunk_end = h2_matches[i + 1].start() if i + 1 < len(h2_matches) else len(region)
        header = region[chunk_start:hm.end()]
        body = region[hm.end():chunk_end]

        items = extract_items(body)
        total_before += len(items)

        kept_parts = []
        cursor = 0
        kept_count = 0
        for it in items:
            kept_parts.append(body[cursor:it["start"]])
            if it["date"] >= cutoff:
                kept_parts.append(it["block"])
                kept_count += 1
            else:
                ym = it["date"][:7]
                archived_by_month[ym].append((hm.group("label").strip(), it["block"]))
            cursor = it["end"]
        kept_parts.append(body[cursor:])
        new_body = "".join(kept_parts)

        old_count_str = hm.group("count")
        new_header = header[:header.index(old_count_str)] + str(kept_count) + header[header.index(old_count_str) + len(old_count_str):]

        out_parts.append(new_header)
        out_parts.append(new_body)
        total_kept += kept_count
        category_new_counts.append((hm.group("icon"), hm.group("label").strip(), kept_count))

    new_region = leading + "".join(out_parts)
    new_html = html[:s] + new_region + html[e:]

    # حدّث total=N في <!--RESEARCH-REPORT--> لكل تصنيف له سطر مطابق (لا "أبرز اليوم").
    def fix_report(m):
        report = m.group(0)
        for icon, label, new_count in category_new_counts:
            report, n = re.subn(
                r'(^' + re.escape(icon) + r' found=\d+ covered=\d+ written=\d+ total=)\d+',
                r'\g<1>' + str(new_count),
                report, count=1, flags=re.M,
            )
        return report

    new_html = re.sub(r'<!--RESEARCH-REPORT.*?-->', fix_report, new_html, count=1, flags=re.S)

    return new_html, archived_by_month, total_before, total_kept


ARCHIVE_HEAD = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>أرشيف دليل ملاطيا — {label}</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{{
  --bg:#0b1020; --bg2:#0d1430; --card:#151e44; --border:#28345f;
  --text:#eef3ff; --text2:#c2cdec; --muted:#8b98bf;
  --accent:#f7a52b; --accent-soft:rgba(247,165,43,.14); --accent-line:rgba(247,165,43,.4);
  --green:#40d183; --green-soft:rgba(64,209,131,.13);
  --blue:#5b9dff; --blue-soft:rgba(91,157,255,.13);
  --font:'Cairo',system-ui,-apple-system,'Segoe UI',sans-serif;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:var(--font);background:var(--bg);color:var(--text);line-height:1.75;font-size:16px;padding:24px 16px 60px;max-width:900px;margin:0 auto}}
a{{color:var(--accent);text-decoration:none}}
a:hover{{text-decoration:underline}}
h1{{font-size:22px;margin-bottom:6px}}
.sub{{color:var(--muted);font-size:14px;margin-bottom:20px}}
.nav{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:24px;font-size:14px}}
.nav a{{background:var(--card);border:1px solid var(--border);padding:6px 12px;border-radius:100px}}
.item{{background:linear-gradient(180deg,var(--card),var(--bg2));border:1px solid var(--border);border-inline-start:4px solid var(--accent);
  border-radius:12px;padding:14px 16px;margin-bottom:12px}}
.item h3{{font-size:15px;font-weight:700;color:#fff;margin:0 0 5px;line-height:1.45}}
.item p{{color:var(--text2);font-size:14px;margin:4px 0}}
.meta{{display:flex;flex-wrap:wrap;gap:7px;margin-top:10px;align-items:center}}
.badge{{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:700;padding:3px 10px;border-radius:100px}}
.badge.b-price{{background:var(--green-soft);color:var(--green);border:1px solid rgba(64,209,131,.3)}}
.badge.b-date{{background:var(--blue-soft);color:var(--blue);border:1px solid rgba(91,157,255,.3)}}
.badge.b-area{{background:var(--accent-soft);color:var(--accent);border:1px solid var(--accent-line)}}
.badge.b-cat{{background:rgba(255,255,255,.06);color:var(--muted);border:1px solid var(--border)}}
.footnote{{color:var(--muted);font-size:13px;margin-top:30px;border-top:1px solid var(--border);padding-top:16px}}
</style>
</head>
<body>
<h1>📦 أرشيف دليل ملاطيا — {label}</h1>
<div class="sub">{count} بطاقة · أقدم من {days} يوماً وقت الطيّ · مرتّبة من الأحدث إلى الأقدم</div>
<div class="nav">{nav}</div>
"""

ARCHIVE_TAIL = """
<p class="footnote">هذه الصفحة أرشيف تلقائي يُحدَّث أسبوعياً بواسطة malatya-archive.yml. البطاقات لا تُحذف أبداً — تُنقل فقط من النشرة الحيّة بعد {days} يوماً.</p>
</body>
</html>
"""

AR_MONTHS = ["", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
             "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]


def month_label(ym):
    y, m = ym.split("-")
    return "%s %s" % (AR_MONTHS[int(m)], y)


def build_archive_page(ym, items, all_months, malatya_dir):
    label = month_label(ym)
    nav_links = []
    for other in sorted(all_months, reverse=True):
        if other == ym:
            nav_links.append('<span class="badge b-cat">%s</span>' % month_label(other))
        else:
            nav_links.append('<a href="archive-%s.html">%s</a>' % (other, month_label(other)))
    nav_links.append('<a href="daleel.html#chapter-daily">← النشرة الحيّة</a>')
    nav = " ".join(nav_links)

    body_items = "\n".join(block for _label, block in items)
    return (ARCHIVE_HEAD.format(label=label, count=len(items), days=DAYS, nav=nav)
            + body_items
            + ARCHIVE_TAIL.format(days=DAYS))


def merge_existing_archive(path, new_items):
    """يدمج بطاقات الشهر الجديدة مع أي بطاقات محفوظة أصلاً في archive-YYYY-MM.html، بلا تكرار."""
    if not os.path.exists(path):
        return new_items
    old_html = open(path, encoding="utf-8").read()
    old_items = extract_items(old_html)
    seen = set()
    merged = []
    for it in old_items:
        key = it["block"]
        if key in seen:
            print("⚠️ بطاقة مطابقة حرفياً موجودة مرّتين في %s (%s) — أُبقيت نسخة واحدة" % (path, it["date"]))
            continue
        seen.add(key)
        merged.append(("؟", it["block"]))
    for label, block in new_items:
        if block in seen:
            print("⚠️ بطاقة قادمة من daleel.html مطابقة حرفياً لبطاقة أُرشفت سابقاً — لم تُكرَّر")
            continue
        seen.add(block)
        merged.append((label, block))
    merged.sort(key=lambda t: re.search(r'data-date="([^"]+)"', t[1]).group(1), reverse=True)
    return merged


ARCHIVE_INDEX_START = "<!--ARCHIVE-INDEX-START-->"
ARCHIVE_INDEX_END = "<!--ARCHIVE-INDEX-END-->"


def build_index_block(all_months, days):
    if not all_months:
        return ""
    links = " · ".join(
        '<a href="archive-%s.html">%s</a>' % (ym, month_label(ym))
        for ym in sorted(all_months, reverse=True)
    )
    return (
        ARCHIVE_INDEX_START
        + '\n<div class="callout accent" style="margin-top:26px">\n'
        + '  <div class="c-h">📦 الأرشيف</div>\n'
        + ('  <p>بطاقات أقدم من %s يوماً تُطوى أسبوعياً إلى صفحات شهرية، بلا حذف: %s</p>\n' % (days, links))
        + "</div>\n"
        + ARCHIVE_INDEX_END
    )


def upsert_archive_index(html, all_months, days):
    block = build_index_block(all_months, days)
    if not block:
        return html
    if ARCHIVE_INDEX_START in html and ARCHIVE_INDEX_END in html:
        s = html.index(ARCHIVE_INDEX_START)
        e = html.index(ARCHIVE_INDEX_END) + len(ARCHIVE_INDEX_END)
        return html[:s] + block + html[e:]
    marker = "<!--DAILY-CONTENT-END-->"
    idx = html.index(marker) + len(marker)
    return html[:idx] + "\n\n" + block + html[idx:]


def main():
    cutoff = (date.fromisoformat(TODAY) - timedelta(days=DAYS)).isoformat()
    html = open(SRC, encoding="utf-8").read()
    new_html, archived_by_month, total_before, total_kept = process(html, cutoff)

    total_archived_now = sum(len(v) for v in archived_by_month.values())
    assert total_before == total_kept + total_archived_now, (
        "فقدان بيانات: قبل=%d، أُبقي=%d، أُرشف=%d" % (total_before, total_kept, total_archived_now))

    malatya_dir = os.path.dirname(SRC)
    touched_archive_files = []
    existing = [f[len("archive-"):-len(".html")] for f in os.listdir(malatya_dir)
                if re.match(r'archive-\d{4}-\d{2}\.html$', f)]
    all_months = set(existing) | set(archived_by_month.keys())
    if archived_by_month:
        for ym, new_items in archived_by_month.items():
            path = os.path.join(malatya_dir, "archive-%s.html" % ym)
            merged = merge_existing_archive(path, new_items)
            page = build_archive_page(ym, merged, all_months, malatya_dir)
            with open(path, "w", encoding="utf-8") as f:
                f.write(page)
            touched_archive_files.append((path, len(merged), len(new_items)))

    new_html = upsert_archive_index(new_html, all_months, DAYS)

    with open(SRC, "w", encoding="utf-8") as f:
        f.write(new_html)

    print("cutoff=%s" % cutoff)
    print("قبل=%d بطاقة، أُبقي=%d، طُوي=%d" % (total_before, total_kept, total_archived_now))
    for path, total, added in touched_archive_files:
        print("  %s ← +%d جديدة (المجموع %d)" % (path, added, total))

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write("archived=%d\n" % total_archived_now)
            f.write("kept=%d\n" % total_kept)
            f.write("months=%s\n" % ",".join(sorted(archived_by_month.keys())))


if __name__ == "__main__":
    main()
