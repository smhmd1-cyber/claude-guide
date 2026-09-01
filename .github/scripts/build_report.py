#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
يحوّل تقرير الوكيل اليومي (ماركداون في agents/src/) إلى شذرة HTML
داخل malatya/reports/، ويحدّث malatya/data/reports-index.json.

الاستخدام:  python3 .github/scripts/build_report.py <aqar|land>

يُبقي المنطق خارج يد النموذج: الوكيل يكتب ماركداون فقط،
وهذا السكربت يولّد HTML متّسق مع بقية الأرشيف.
"""
import io, os, re, sys, json, html, glob, subprocess, datetime

TRACK = (sys.argv[1] if len(sys.argv) > 1 else '').strip()
if TRACK not in ('aqar', 'land'):
    sys.exit('الاستخدام: build_report.py <aqar|land>')

SRC_DIR = 'agents/src'
OUT_DIR = 'malatya/reports'
IDX = 'malatya/data/reports-index.json'
NAME_RE = re.compile(r'^(aqar|land)-(\d{4}-\d{2}-\d{2})\.md$')


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
def today_iso():
    """تاريخ القدس — نفس التاريخ الذي تَسِم به السحّابات والوكلاء سجلّ اليوم."""
    r = subprocess.run(['date', '+%Y-%m-%d'], capture_output=True, text=True,
                       env={**os.environ, 'TZ': 'Asia/Jerusalem'})
    out = (r.stdout or '').strip()
    return out or datetime.date.today().isoformat()


def rescue_placeholder_names(iso):
    """شبكة أمان لخطأ كلّف ثلاثة أيام من الأرشيف.

    في التوجيه، `TODAY` **متغيّر** يُفترض أن يستبدله الوكيل بتاريخ اليوم. لكن
    مسار الملفّ كان مكتوباً حرفياً `agents/src/aqar-TODAY.md`، فأخذه النموذج
    كما هو وكتب ملفّاً بهذا الاسم. النتيجة في 30 و31/08 و01/09/2026:
      · هذا السكربت لا يطابق الاسم فيتخطّاه **بصمت** ⇒ لا صفحة ولا فهرس؛
      · وفي اليوم التالي يُكتب فوقه ⇒ نصّ الأمس يضيع بلا أثر.
    هنا نصحّح الاسم بدل أن نلوم النموذج: أيّ `<track>-TODAY.md` يصير
    `<track>-<تاريخ اليوم>.md`، والباقي يمرّ في المسار الطبيعي.
    """
    moved = []
    for stray in glob.glob(os.path.join(SRC_DIR, '%s-*.md' % TRACK)):
        base = os.path.basename(stray)
        if NAME_RE.match(base):
            continue
        # نُنقذ فقط ما يشبه اسم اليوم النائب؛ ما عداه يُبلَّغ عنه ولا يُمَسّ.
        if re.match(r'^%s-(TODAY|<TODAY>|\$TODAY|today)\.md$' % TRACK, base):
            dst = os.path.join(SRC_DIR, '%s-%s.md' % (TRACK, iso))
            if os.path.exists(dst) and os.path.getsize(dst) >= os.path.getsize(stray):
                print('::warning::%s موجود سلفاً وأطول — أُبقي عليه وحُذف النائب %s' % (dst, base))
                os.remove(stray)
            else:
                os.replace(stray, dst)
                print('::warning::اسم نائب: %s ← أُعيدت تسميته إلى %s-%s.md' % (base, TRACK, iso))
            moved.append(base)
        else:
            print('::error::ملفّ لا يطابق الصيغة <%s>-<YYYY-MM-DD>.md ولن يُبنى: %s'
                  % (TRACK, base))
    return moved


def ensure_today_source(iso):
    """يومٌ بلا تقرير يُسجَّل كيوم بلا تقرير — لا كفجوة صامتة في الأرشيف."""
    dst = os.path.join(SRC_DIR, '%s-%s.md' % (TRACK, iso))
    # لا نكتب فوق شيء كتبه الوكيل، ولو بدا قصيراً: الدهس هو العطب الذي
    # نُصلحه هنا، لا الأداة التي نُصلحه بها. الملفّ القصير يسقط لاحقاً في
    # فحص «أقصر من 120 حرفاً» فيظهر الإخفاق بدل أن يُدفن.
    if os.path.exists(dst):
        return False
    label = 'سوق الشقق' if TRACK == 'aqar' else 'أراضي ملاطيا'
    data = ('malatya/data/aqar-listings.json' if TRACK == 'aqar'
            else 'malatya/data/land-listings.json')
    with io.open(dst, 'w', encoding='utf-8', newline='\n') as f:
        f.write(
            '# %s — %s: لم يُكتب تقرير سرديّ اليوم\n\n'
            '> **هذه ليست «لا جديد في السوق».** هذه إفادةٌ بأنّ خطوة الكتابة لم تُنتج نصّاً\n'
            '> اليوم — تعطّلٌ في الوكيل أو في رمز الدخول أو مهلة انتهت. البيانات نفسها\n'
            '> ليست معنيّة: سجلّ اليوم في `%s` كُتب بسحّاب حتميّ مستقلّ عن هذه الخطوة،\n'
            '> واللوحة الحيّة تعرض أرقام اليوم كاملةً.\n\n'
            '## ما الذي يُفحص\n\n'
            '- سجلّ الريّة في تبويب Actions — الخطوة «تشغيل Claude».\n'
            '- صلاحية السرّ `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token`).\n'
            '- مهلة الوظيفة (60 دقيقة) إن كان السحب قد استغرقها.\n\n'
            '## لماذا تُكتب هذه الصفحة أصلاً\n\n'
            'لأنّ الفجوة الصامتة أسوأ من الإخفاق المُعلَن: في 30 و31 آب/أغسطس 2026 غاب\n'
            'التقرير ثلاثة أيام ولم يَبِن ذلك في الأرشيف، فبدا الأمر كأنّ شيئاً لم يحدث.\n'
            % (label, iso, data))
    print('::warning::لم يكتب الوكيل تقرير %s ليوم %s — أُنشئت صفحة تُصرّح بذلك'
          % (TRACK, iso))
    return True


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(SRC_DIR, exist_ok=True)

    iso = today_iso()
    rescue_placeholder_names(iso)
    ensure_today_source(iso)

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

    # الفحص الأخير: هل ليوم اليوم صفحةٌ فعلاً؟ سلسلة الأرشيف تُقاس هنا لا في النيّة.
    want = '%s-%s.html' % (TRACK, iso)
    if want in by_file and os.path.exists(os.path.join(OUT_DIR, want)):
        print('   سلسلة الأرشيف متّصلة حتى %s' % iso)
    else:
        print('::error::لا صفحة أرشيف ليوم %s في مسار %s — السلسلة منقطعة' % (iso, TRACK))
        sys.exit(1)


if __name__ == '__main__':
    main()
