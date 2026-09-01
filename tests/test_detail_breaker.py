# -*- coding: utf-8 -*-
"""مبحث القاطع: يتوقّف عن التفاصيل عند سلسلة إخفاقات، ولا يفقد صفاً واحداً."""
import os, sys, time, importlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
os.environ['AQAR_DETAIL_FAIL_STREAK'] = '12'
os.environ['ARSA_DETAIL_FAIL_STREAK'] = '12'

ok = True
def chk(name, cond, extra=''):
    global ok
    print(('  ✓ ' if cond else '  ✗ ') + name + (('  ' + str(extra)) if extra else ''))
    ok = ok and cond

# ── aqar ──
aq = importlib.import_module('scrape_aqar')
calls = {'n': 0}
def boom(_id):
    calls['n'] += 1
    raise RuntimeError('HTTP 403')
aq.detail = boom
rows = [{'id': str(i), 'deal': 'sale'} for i in range(300)]
t0 = time.time()
meta = aq.enrich(rows, {})
dt = time.time() - t0
print('aqar:', meta, 'calls=%d  %.1fs' % (calls['n'], dt))
chk('توقّف بعد 12 محاولة لا 300', calls['n'] == 12, calls['n'])
chk('وسَم النتيجة degraded', meta.get('status') == 'degraded')
chk('سجّل سبب التوقّف', 'detail_aborted' in meta)
chk('لم يُفقد أي صفّ', len(rows) == 300)

# سلسلة تنقطع بنجاح ⇒ لا قاطع
calls['n'] = 0
seq = {'i': 0}
def flaky(_id):
    seq['i'] += 1
    if seq['i'] % 5 == 0:
        return {}
    raise RuntimeError('HTTP 500')
aq.detail = flaky
aq.time.sleep = lambda *_: None
rows2 = [{'id': 'x%d' % i, 'deal': 'sale'} for i in range(40)]
m2 = aq.enrich(rows2, {})
chk('نجاحٌ متقطّع لا يُفعّل القاطع', 'detail_aborted' not in m2, m2)

# الذاكرة تمنع الطلب أصلاً
prev = {'9': {'age_raw': '5', 'tapu': 'طابو مستقلّ'}}
calls['n'] = 0
aq.detail = boom
rows3 = [{'id': '9', 'deal': 'sale'}]
m3 = aq.enrich(rows3, prev)
chk('الصفّ المخزَّن لا يُطلب من الشبكة', calls['n'] == 0 and m3['detail_cached'] == 1)

# ── arsa ──
ar = importlib.import_module('scrape_arsa')
c2 = {'n': 0}
def boom2(_id):
    c2['n'] += 1
    raise RuntimeError('HTTP 403')
ar.ej_detail = boom2
rows4 = [{'id': str(i)} for i in range(300)]
m4 = ar.enrich_emlakjet(rows4, {})
print('arsa:', m4, 'calls=%d' % c2['n'])
chk('arsa: توقّف بعد 12', c2['n'] == 12, c2['n'])
chk('arsa: سجّل سبب التوقّف', 'detail_aborted' in m4)
chk('arsa: لم يُفقد أي صفّ', len(rows4) == 300)

print('\n' + ('✅ كل المباحث نجحت' if ok else '❌ سقط مبحث'))
sys.exit(0 if ok else 1)
