#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════
#  فحص شامل لبيانات «ملف الاستثمار المشترك» وصفحاته.
#  يُشغَّل قبل كل نشر:  python3 audit_invest.py
#  يخرج بـ1 عند وجود خطأ، فيصلح للاستعمال داخل سير عمل.
# ═══════════════════════════════════════════════════════════════
import json,re,os,glob,sys
from collections import Counter
os.chdir(os.path.dirname(os.path.abspath(__file__)))
D='malatya/data/'; H='malatya/'
err=[];warn=[];ok=[]
E=err.append; W=warn.append; O=ok.append

# ① صحة التركيب
data={}
for f in sorted(glob.glob(D+'invest-*.json')):
    try: data[os.path.basename(f)]=json.load(open(f,encoding='utf-8'))
    except Exception as e: E(f'JSON معطوب: {f} — {e}')
O(f'{len(data)} ملف بيانات صالح تركيبياً')

src=data.get('invest-sources.json',{})
SRC={x['code'] for x in src.get('items',[])}

# ② المصادر
if src.get('count')!=len(src.get('items',[])): E(f"عدّاد المصادر {src.get('count')} ≠ العناصر {len(src.get('items',[]))}")
else: O(f"عدّاد المصادر مطابق ({src.get('count')})")
codes=[x['code'] for x in src.get('items',[])]
dup=sorted(c for c in set(codes) if codes.count(c)>1)
if dup: E(f'رموز مصادر مكرَّرة: {dup}')
else: O('لا رموز مصادر مكرَّرة')
bad=[x['code'] for x in src.get('items',[]) if not str(x.get('url','')).startswith('https://')]
if bad: E(f'روابط غير https: {bad}')
else: O('كل روابط المصادر تبدأ بـhttps')
missf=[x['code'] for x in src.get('items',[]) if not all(x.get(k) for k in ('org','title','url','why','cat'))]
if missf: E(f'مصادر بحقول ناقصة: {missf}')
else: O('كل المصادر مكتملة الحقول')

# ③ إحالات الرموز في البيانات والصفحات
def refs(o):
    out=[]
    if isinstance(o,dict):
        for k,v in o.items():
            if k in ('src','sources'): out += ([v] if isinstance(v,str) else [x for x in v if isinstance(x,str)])
            else: out+=refs(v)
    elif isinstance(o,list):
        for v in o: out+=refs(v)
    return out
for fn,d in data.items():
    if fn=='invest-sources.json': continue
    b=sorted(x for x in set(refs(d)) if x and x not in SRC)
    if b: E(f'{fn}: رموز مصادر غير معروفة {b}')
for f in sorted(glob.glob(H+'invest*.html')):
    cited=set(re.findall(r'class="cite">([A-Z]+\d+)<',open(f,encoding='utf-8').read()))
    b=sorted(c for c in cited if c not in SRC)
    if b: E(f'{os.path.basename(f)}: إحالات غير موجودة {b}')
O('فُحصت إحالات الرموز في البيانات وفي الصفحات')

# ④ المعرّفات
for fn,key in (('invest-paths.json','items'),('invest-risks.json','items'),
               ('invest-structures.json','structures'),('invest-nace.json','items')):
    ids=[x.get('id') for x in data.get(fn,{}).get(key,[])]
    d2=sorted(i for i in set(ids) if ids.count(i)>1)
    if d2: E(f'{fn}: معرّفات مكرَّرة {d2}')
O('لا معرّفات مكرَّرة')

# ⑤ إعادة حساب الدرجات من تقديراتها
W8={"prot":18,"inc":14,"macro":12,"dem":11,"mgmt":11,"evid":11,"cap":9,"legal":6,"team":5,"exit":3}
pw={w['k']:w['w'] for w in data.get('invest-profile.json',{}).get('weights',[])}
if pw!=W8: E(f'أوزان الملف لا تطابق المرجع: {pw}')
elif sum(W8.values())!=100: E('مجموع الأوزان ليس ١٠٠')
else: O('أوزان الشبكة المعيارية مطابقة ومجموعها ١٠٠')
for p in data.get('invest-paths.json',{}).get('items',[]):
    if 'r' not in p: E(f"{p['id']}: بلا تقديرات"); continue
    m=[k for k in W8 if k not in p['r']]
    if m: E(f"{p['id']}: معايير ناقصة {m}"); continue
    oob=[k for k,v in p['r'].items() if not (0<=v<=1)]
    if oob: E(f"{p['id']}: تقديرات خارج المدى [0,1] {oob}")
    calc=round(sum(W8[k]*p['r'][k] for k in W8))
    if calc!=p['score']: E(f"{p['id']}: الدرجة المخزَّنة {p['score']} ≠ المحسوبة {calc}")
O(f"أُعيد حساب درجات {len(data.get('invest-paths.json',{}).get('items',[]))} مساراً")

# ⑥ حقول المسارات والمخاطر والهياكل
for p in data.get('invest-paths.json',{}).get('items',[]):
    for k in ('id','name','cat','desc','evidence','unknown','inc'):
        if not p.get(k): E(f"{p.get('id')}: حقل ناقص {k}")
    if p.get('inc',{}).get('st') not in ('yes','no','part'): E(f"{p.get('id')}: حالة أهلية غير معيارية")
    if not p.get('unknown'): W(f"{p.get('id')}: بلا مجاهيل — كل مسار يجب أن يحمل ما يمنع اعتماده")
O('فُحصت حقول كل المسارات')
for r in data.get('invest-risks.json',{}).get('items',[]):
    for k in ('id','name','cat','prob','impact','desc','mitig'):
        if not r.get(k): E(f"خطر {r.get('id')}: حقل ناقص {k}")
    if r.get('prob') not in ('عالٍ','متوسط','منخفض'): E(f"خطر {r.get('id')}: احتمال غير معياري")
    if r.get('impact') not in ('عالٍ','متوسط','منخفض'): E(f"خطر {r.get('id')}: أثر غير معياري")
    if not r.get('src') and not r.get('basis'): W(f"خطر {r.get('id')}: بلا مصدر ولا وسم تحليلي")
O('فُحصت حقول كل المخاطر')
CRIT=['own','ctrl','prot','tax','perm','diff','cost','disp','exit','fit']
for s in data.get('invest-structures.json',{}).get('structures',[]):
    m=[k for k in CRIT if k not in s]
    if m: E(f"هيكل {s.get('id')}: معايير ناقصة {m}")
    if s.get('st') not in ('in','out','rej'): E(f"هيكل {s.get('id')}: حالة غير معيارية")
O('فُحصت معايير الهياكل الستة')

# ⑦ اللغة الممنوعة — مع استثناء نصّ القاعدة المانعة نفسها
BAN=['الربح مضمون','العائد مؤكَّد','العائد مؤكد','عائد مضمون','فرصة لا تُعوَّض','ربح مضمون','أرباح مضمونة']
for f in sorted(glob.glob(H+'invest*.html'))+sorted(glob.glob(D+'invest-*.json')):
    s=open(f,encoding='utf-8').read(); hit=[]
    for b in BAN:
        for mm in re.finditer(re.escape(b),s):
            ctx=s[max(0,mm.start()-60):mm.start()]
            if 'لا «' in ctx or 'لا تستخدم' in ctx or 'ممنوع' in ctx: continue
            hit.append(b)
    if hit: E(f'{os.path.basename(f)}: عبارة ممنوعة {sorted(set(hit))}')
O('لا عبارات ضمان ربح خارج سياق القاعدة المانعة')

# ⑧ الروابط الداخلية ومصادر الجلب
for f in sorted(glob.glob(H+'*.html')):
    s=open(f,encoding='utf-8').read()
    for href in set(re.findall(r'href="([a-z0-9\-]+\.html)"',s)):
        if not os.path.exists(H+href): E(f'{os.path.basename(f)}: رابط داخلي مكسور → {href}')
    for u in set(re.findall(r"fetch\('data/([a-z0-9\-]+\.json)",s)):
        if not os.path.exists(D+u): E(f'{os.path.basename(f)}: يجلب ملفاً غير موجود → {u}')
O('فُحصت الروابط الداخلية ومصادر الجلب')

# ⑨ تطابق الأعداد المكتوبة مع البيانات
AR='٠١٢٣٤٥٦٧٨٩'
def ar(n): return ''.join(AR[int(c)] for c in str(n))
np_=len(data.get('invest-paths.json',{}).get('items',[]))
nr=len(data.get('invest-risks.json',{}).get('items',[]))
ns=src.get('count',0)
for f in sorted(glob.glob(H+'invest*.html'))+[H+'index.html',H+'assets/nav.js']:
    s=open(f,encoding='utf-8').read(); b=os.path.basename(f)
    for pat,cur,lbl in ((r'([٠-٩]+) مصدر',ar(ns),'مصدراً'),(r'([٠-٩]+) خطر',ar(nr),'خطراً'),
                        (r'([٠-٩]+) مساراً',ar(np_),'مساراً')):
        for m in set(re.findall(pat,s)):
            if m!=cur: W(f'{b}: مكتوب «{m} {lbl}» والفعلي «{cur}»')
O('قوبلت الأعداد المكتوبة بالبيانات الفعلية')

# ⑩ شريط التنقّل وترقيم النسخة
nav=open(H+'assets/nav.js',encoding='utf-8').read()
for h in re.findall(r"h: '([a-z0-9\-]+\.html)'",nav):
    if not os.path.exists(H+h): E(f'nav.js: يشير إلى ملف غير موجود {h}')
pages=set(os.path.basename(x) for x in glob.glob(H+'invest*.html'))
innav=set(re.findall(r"h: '(invest[a-z0-9\-]*\.html)'",nav))
if pages-innav: W(f'صفحات خارج شريط التنقّل: {sorted(pages-innav)}')
else: O('كل صفحات القسم مدرجة في شريط التنقّل')
navv=set(re.findall(r'nav\.js\?v=(\d+)',' '.join(open(f,encoding='utf-8').read() for f in glob.glob(H+'*.html'))))
if len(navv)>1: W(f'إصدارات nav.js غير موحَّدة: {sorted(navv)}')
else: O(f'ترقيم nav.js موحَّد ({sorted(navv)[0] if navv else "—"})')

# ⑪ اكتمال حزمة النشر
wf=open('.github/workflows/malatya-publish.yml',encoding='utf-8').read()
need=set(re.findall(r'(invest[a-z0-9\-]*\.html|data/invest-[a-z0-9\-]+\.json)',wf))
for n in sorted(need):
    if not os.path.exists(H+n): E(f'فحص حزمة النشر يطلب ملفاً غير موجود: {n}')
present={('data/'+os.path.basename(x)) for x in glob.glob(D+'invest-*.json')} | pages
notchecked=sorted(present-need)
if notchecked: W(f'ملفات القسم خارج فحص حزمة النشر: {notchecked}')
else: O('كل ملفات القسم مشمولة بفحص اكتمال النشر')

# ⑫ خريطة المحتوى
s=open(H+'invest.html',encoding='utf-8').read()
m=re.findall(r"\[(\d+),'([^']+)','[^']*','(done|next|later)'\]",s)
if len(m)!=28: E(f'خريطة المحتوى فيها {len(m)} صفحة لا ٢٨')
c=Counter(x[2] for x in m)
O(f"خريطة المحتوى: {c.get('done',0)} منشورة · {c.get('next',0)} تالية · {c.get('later',0)} لاحقاً")

# ⑬ مصيدة ASI: «return» في آخر السطر تُفرغ الدالة بصمت — صفحة تُحمَّل ولا تعرض شيئاً
for f in sorted(glob.glob(H+'*.html')):
    body=open(f,encoding='utf-8').read()
    for sc in re.findall(r'<script>(.*?)</script>',body,re.S):
        if re.search(r'\breturn\s*\n',sc): E(f'{os.path.basename(f)}: «return» في آخر السطر داخل <script> — ستعود الدالة بلا قيمة')
O('لا مصيدة «return» في آخر السطر داخل أي صفحة')

print('══════ أخطاء ══════');  print('\n'.join(' ❌ '+e for e in err) or '  لا شيء')
print('══════ تنبيهات ══════'); print('\n'.join(' ⚠️  '+w for w in warn) or '  لا شيء')
print('══════ اجتاز ══════');  print('\n'.join(' ✅ '+o for o in ok))
print(f'\nالمحصّلة: {len(err)} خطأ · {len(warn)} تنبيه · {len(ok)} فحصاً')
sys.exit(1 if err else 0)
