#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
يحوّل تقرير الوكيل اليومي (ماركداون في agents/src/) إلى شذرة HTML
داخل malatya/reports/، ويحدّث malatya/data/reports-index.json.

الاستخدام:  python3 .github/scripts/build_report.py <aqar|land>

يُبقي المنطق خارج يد النموذج: الوكيل يكتب ماركداون فقط،
وهذا السكربت يولّد HTML متّسق مع بقية الأرشيف.
"""
import os, re, sys, json, html, glob, subprocess

TRACK = (sys.argv[1] if len(sys.argv) > 1 else '').strip()
if TRACK not in ('aqar', 'land'):
    sys.exit('الاستخدام: build_report.py <aqar|land>')

SRC_DIR = 'agents/src'
OUT_DIR = 'malatya/reports'
IDX = 'malatya/data/reports-index.json'


# ────────────────── تحويل ماركداون (نفس محوّل بناء الموقع) ──────────────────
def md_inline(s):
    s = html.escape(s)
    s = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)[^)]*\)',
               r'<img src="\2" alt="\1" style="max-width:100%;border-radius:10px">', s)
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)[^)]*\)',
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![\w*])\*([^*\n]+)\*(?![\w*])', r'<em>\1</em>', s)
    s = re.sub(r'(?<!href=")(?<!src=")(https?://[^\s<>"\)]+)',
               r'<a href="\1" target="_blank" rel="noopener">\1</a>', s)
    return s


def md_to_html(md):
    out, lines, i = [], md.replace('\r\n', '\n').split('\n'), 0
    list_open = None

    def close_list():
        nonlocal list_open
        if list_open:
            out.append('</%s>' % list_open); list_open = None

    while i < len(lines):
        ln = lines[i]

        if '|' in ln and i + 1 < len(lines) and re.match(r'^\s*\|?[\s:|-]+\|[\s:|-]*$', lines[i + 1]):
            close_list()
            cells = lambda r: [c.strip() for c in r.strip().strip('|').split('|')]
            out.append('<div class="tbl-wrap"><table><thead><tr>' +
                       ''.join('<th>' + md_inline(c) + '</th>' for c in cells(ln)) +
                       '</tr></thead><tbody>')
            i += 2
            while i < len(lines) and '|' in lines[i] and lines[i].strip():
                out.append('<tr>' + ''.join('<td>' + md_inline(c) + '</td>' for c in cells(lines[i])) + '</tr>')
                i += 1
            out.append('</tbody></table></div>')
            continue

        m = re.match(r'^(#{1,6})\s+(.*)$', ln)
        if m:
            close_list()
            lvl = min(len(m.group(1)) + 1, 6)
            out.append('<h%d>%s</h%d>' % (lvl, md_inline(m.group(2)), lvl)); i += 1; continue

        if re.match(r'^\s*([-*_])\1{2,}\s*$', ln):
            close_list(); out.append('<hr class="soft">'); i += 1; continue

        m = re.match(r'^\s*([-*+•])\s+(.*)$', ln)
        if m:
            if list_open != 'ul': close_list(); out.append('<ul>'); list_open = 'ul'
            out.append('<li>' + md_inline(m.group(2)) + '</li>'); i += 1; continue

        m = re.match(r'^\s*(\d+)[.)]\s+(.*)$', ln)
        if m:
            if list_open != 'ol': close_list(); out.append('<ol>'); list_open = 'ol'
            out.append('<li>' + md_inline(m.group(2)) + '</li>'); i += 1; continue

        m = re.match(r'^\s*>\s?(.*)$', ln)
        if m:
            close_list(); out.append('<div class="note">' + md_inline(m.group(1)) + '</div>'); i += 1; continue

        if not ln.strip():
            close_list(); i += 1; continue

        close_list()
        out.append('<p>' + md_inline(ln.strip()) + '</p>')
        i += 1

    close_list()
    return '\n'.join(out)


# ────────────────────────────── التنفيذ ──────────────────────────────
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(SRC_DIR, exist_ok=True)

    srcs = sorted(glob.glob(os.path.join(SRC_DIR, '%s-*.md' % TRACK)))
    if not srcs:
        print('⏭️  لا تقارير ماركداون جديدة للمسار %s — لا شيء لبنائه.' % TRACK)
        return

    idx = json.load(open(IDX, encoding='utf-8')) if os.path.exists(IDX) else []
    by_file = {r['file']: r for r in idx}
    built = 0

    for s in srcs:
        m = re.search(r'(%s)-(\d{4}-\d{2}-\d{2})\.md$' % TRACK, os.path.basename(s))
        if not m:
            continue
        track, date = m.group(1), m.group(2)
        name = '%s-%s.html' % (track, date)
        body = md_to_html(open(s, encoding='utf-8', errors='replace').read())
        if len(body) < 120:
            print('⚠️  %s قصير جداً (%d حرفاً) — تخطّيته' % (name, len(body)))
            continue
        open(os.path.join(OUT_DIR, name), 'w', encoding='utf-8').write(body)
        by_file[name] = {'track': track, 'date': date, 'file': name}
        built += 1
        print('  ✓ %s (%d حرفاً)' % (name, len(body)))

    # فهرس نظيف بلا تكرار، الأحدث أولاً
    idx = sorted(by_file.values(), key=lambda r: (r['track'], r['date']), reverse=True)
    json.dump(idx, open(IDX, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    n_a = sum(1 for r in idx if r['track'] == 'aqar')
    n_l = sum(1 for r in idx if r['track'] == 'land')
    print('✅ بُني %d تقريراً · الفهرس الآن %d (عقارات %d · أراضٍ %d)' % (built, len(idx), n_a, n_l))


if __name__ == '__main__':
    main()
