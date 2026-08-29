#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سحب إعلانات الشقق في ولاية ملاطيا — بيعاً وإيجاراً — من Emlakjet.

لماذا كُتب هذا الملف: كان «وكيل الشقق» يعتمد على نموذج لغوي يتصفّح البوّابات
ويكتب النتائج بنفسه. توقّف عن الإنتاج في ٢٥/٠٨/٢٠٢٦ لأنّ hepsiemlak و
Coldwell Banker و sahibinden ترفض العملاء الآليّين (403)، فصار يعود بسجلّ فارغ
كل يوم. هذا السحّاب حتميّ: يقرأ الحقول البنيوية المعلنة في الصفحة نفسها، ولا
يستنبط ولا يخمّن. ما لا يعلنه المصدر يبقى فارغاً ويُعلَن أنه فارغ.

المصدر:
    https://www.emlakjet.com/satilik-daire/malatya/   (بيع)
    https://www.emlakjet.com/kiralik-daire/malatya/   (إيجار)
كل صفحة نتائج تحمل
<script id="listing-realestate-schema" type="application/ld+json"> فيه @graph من
كائنات schema.org/RealEstateListing. وصفحة الإعلان تحمل «Bina Yaşı» و«Tapu
Durumu» و«Isıtma Tipi» وبقيّة الحقول، بعضها في JSON-LD وبعضها في الوسم.

الإيجار يُسحَب كي يُحتسب العائد الإيجاري الإجمالي لكل إلچة من بيانات فعلية
منشورة، لا من تقدير. العائد هنا إجماليّ قبل الضريبة والإدارة والشواغر.

الأسعار كما يعلنها البائع أو المكتب — ليست تقييماً ولا عرضاً ملزماً.
"""

import io
import json
import os
import re
import statistics
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone

import requests

OUT = os.environ.get("AQAR_OUT", "malatya/data/aqar-listings.json")
REPORTS = os.environ.get("AQAR_REPORTS", "malatya/data/aqar-reports.json")
# ملفّ التعديلات اليدوية: تكتبه لوحة الإدارة ولا يمسّه السحّاب. الفصل نفسه
# المعتمد في لوحة الأراضي — لولاه لدهس التحديثُ اليوميّ كلَّ تعديل يدوي.
OVERRIDES = os.environ.get("AQAR_OVERRIDES",
                           os.path.join(os.path.dirname(OUT), "aqar-overrides.json"))
DETAIL_BUDGET = int(os.environ.get("AQAR_DETAIL_BUDGET", "600"))
MAX_PAGES = int(os.environ.get("AQAR_MAX_PAGES", "40"))

SUSPECT_M2 = 5000          # شقة أكبر من ذلك = خطأ فاصل في المصدر لا شقة حقيقية

DISTRICTS = [
    "Battalgazi", "Yeşilyurt", "Akçadağ", "Arapgir", "Arguvan", "Darende",
    "Doğanşehir", "Doğanyol", "Hekimhan", "Kale", "Kuluncak", "Pütürge", "Yazıhan",
]
DISTRICTS_UP = {d.upper(): d for d in DISTRICTS}
# «Arapkir» تهجئة قديمة لـ«Arapgir» — الإلچة نفسها.
# «Merkez» اسم ما قبل ٢٠١٣: قُسِّم مركز ملاطيا يومها إلى باتالغازي ويشيليورت.
# لا نخمّن أيّهما — يبقى باسمه ويُعرَض كما هو.
ALIASES = {"ARAPKIR": "Arapgir", "MERKEZ": "Merkez"}
LEGACY = {"Merkez": "مركز ملاطيا — تسمية ما قبل ٢٠١٣، لم تُفصَّل الإلچة"}
ALLOWED = DISTRICTS + list(LEGACY)
# نواة ملاطيا الحضرية: الإلچتان اللتان انقسم إليهما المركز، وفيهما جلّ السوق.
CORE = ("Yeşilyurt", "Battalgazi", "Merkez")

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.6",
}

CHAIN_PEM = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "ilan-gov-tr-chain.pem")
_BUNDLE = None


def ca_bundle():
    """حزمة شهادات احتياطية: certifi + الوسيطة المصدَّرة في المستودع.

    تُستعمل فقط عند فشل TLS بالتحقّق المعتاد. التحقّق يبقى مفعَّلاً دائماً.
    """
    global _BUNDLE
    if _BUNDLE is not None:
        return _BUNDLE or None
    if not os.path.exists(CHAIN_PEM):
        _BUNDLE = ""
        return None
    try:
        import certifi
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".pem")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(io.open(certifi.where(), encoding="utf-8").read())
            f.write("\n")
            f.write(io.open(CHAIN_PEM, encoding="utf-8").read())
        _BUNDLE = path
    except Exception as e:
        print("  تعذّر تجهيز حزمة الشهادات: %s" % e, file=sys.stderr)
        _BUNDLE = ""
    return _BUNDLE or None


def _verify_modes():
    modes = [True]
    b = ca_bundle()
    if b:
        modes.append(b)
    return modes


def get(url, tries=4, **kw):
    last = None
    for verify in _verify_modes():
        for i in range(tries):
            try:
                r = requests.get(url, headers=HEADERS, timeout=45, verify=verify, **kw)
                if r.status_code == 200:
                    return r.text
                last = "HTTP %d" % r.status_code
            except requests.exceptions.SSLError as e:
                last = "SSLError: %s" % e
                break
            except Exception as e:
                last = "%s: %s" % (type(e).__name__, e)
            time.sleep(3 * (i + 1))
    raise RuntimeError("تعذّر جلب %s — %s" % (url, last))


# ───────────────────────── تطبيع تركي ─────────────────────────
# التركية لا تُخفَّض حرفياً: «İ».lower() تُنتج i مع نقطة مركّبة، و«I».lower()
# تُنتج i لا ı. لذلك يُطبَّع الطرفان بمفتاح لاتيني مجرَّد قبل أي مقارنة.

def tr_key(x):
    t = unicodedata.normalize("NFKD", str(x or "")).lower()
    t = "".join(c for c in t if not unicodedata.combining(c))
    for a, b in (("ı", "i"), ("ş", "s"), ("ğ", "g"), ("ç", "c"), ("ö", "o"), ("ü", "u")):
        t = t.replace(a, b)
    t = re.sub(r"[^a-z0-9+ ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def norm_district(name):
    """يعيد اسم الإلچة بصيغتها المعيارية، أو None إن كانت خارج ولاية ملاطيا."""
    if not name:
        return None
    n = str(name).strip()
    up = n.upper()
    for key, std in DISTRICTS_UP.items():
        if up == key or n.casefold() == std.casefold():
            return std
    if up in ALIASES:
        return ALIASES[up]
    return None


def to_int(x):
    if x is None:
        return None
    s = re.sub(r"[^0-9]", "", str(x))
    return int(s) if s else None


# ───────────────────────── عمر البناء ─────────────────────────
# المحور الأهمّ في هذه اللوحة. القيمة معلنة في صفحة الإعلان («Bina Yaşı») ولا
# تُستنبط. الإعلان الذي لا يذكرها يُصنَّف «غير مذكور» ولا يُعامَل معاملة الجديد.

AGE_0 = "صفر · جاهز للسكن"
AGE_BUILD = "قيد الإنشاء"
AGE_1_3 = "١–٣ سنوات"
AGE_4_5 = "٤–٥ سنوات"
AGE_6_10 = "٦–١٠ سنوات"
AGE_11P = "أكثر من ١٠ سنوات"
AGE_UNK = "غير مذكور"
AGE_ORDER = [AGE_0, AGE_BUILD, AGE_1_3, AGE_4_5, AGE_6_10, AGE_11P, AGE_UNK]
# «القانون الحديدي» للمستثمر: جديد أو قيد الإنشاء أو ≤٣ سنوات.
AGE_FRESH = (AGE_0, AGE_BUILD, AGE_1_3)


def age_bucket(raw):
    """يحوّل قيمة «Bina Yaşı» المعلنة إلى فئة. يعيد (فئة، أدنى عمر معروف).

    القيم التي يكتبها المصدر فعلاً: «0 (Oturuma Hazır)» · «0 (Yapım Aşamasında)»
    · «6-10» · «11-15» · «21 Ve Üzeri» · «3». المدى يُصنَّف بحدّه الأدنى، ثمّ
    يُرفَع إن كان حدّه الأعلى يتجاوز الفئة — فـ«1-5» ليست «١–٣».
    """
    if raw is None or str(raw).strip() == "":
        return AGE_UNK, None
    t = tr_key(raw)
    if "yapim asama" in t or "insaat" in t:
        return AGE_BUILD, 0
    nums = [int(n) for n in re.findall(r"\d+", t)]
    if not nums:
        return AGE_UNK, None
    lo = min(nums)
    hi = max(nums)
    if "uzeri" in t or "+" in str(raw):
        hi = max(hi, 99)
    if hi == 0:
        return AGE_0, 0
    if hi <= 3:
        return AGE_1_3, lo
    if hi <= 5:
        return AGE_4_5, lo
    if hi <= 10:
        return AGE_6_10, lo
    return AGE_11P, lo


TAPU_MAP = {
    "kat mulkiyeti": "ملكية طوابق (Kat Mülkiyeti)",
    "kat irtifaki": "حقّ ارتفاق طوابق (Kat İrtifakı)",
    "mustakil tapulu": "طابو مستقلّ",
    "hisseli tapu": "طابو مشاع (حصّة)",
    "hisseli tapulu": "طابو مشاع (حصّة)",
    "arsa tapulu": "طابو أرض (لا إفراز طوابق)",
    "tapu kaydi yok": "بلا قيد طابو",
    "kooperatiften tapu": "طابو من تعاونية",
    "bilinmiyor": "نوع الطابو غير معروف",
}
_TAPU_KEYS = None


def tapu_label(raw):
    """يُعرِّب نوع الطابو. آمن للتكرار — القيمة العربية تمرّ كما هي."""
    global _TAPU_KEYS
    if _TAPU_KEYS is None:
        _TAPU_KEYS = {tr_key(k): v for k, v in TAPU_MAP.items()}
    if not raw:
        return None
    return _TAPU_KEYS.get(tr_key(raw), str(raw).strip())


YESNO = {"var": True, "evet": True, "yok": False, "hayir": False}


def yesno(raw):
    if raw is None:
        return None
    return YESNO.get(tr_key(raw))


def kredi_label(raw):
    if not raw:
        return None
    t = tr_key(raw)
    if "uygun" not in t:
        return str(raw).strip()
    return "غير صالح للتمويل" if "degil" in t else "صالح للتمويل"


# ───────────────────────── قراءة صفحات النتائج ─────────────────────────

EJ_SCHEMA = re.compile(
    r'<script[^>]+id="listing-realestate-schema"[^>]*>(.*?)</script>', re.S)
EJ_ID = re.compile(r'-(\d+)$')
# العدّاد المرئي مقسوم بوسم وتعليق HTML فلا ينفع بحث نصّي ساذج؛ وحمولة Next.js
# تحمل totalItems/totalPages صراحةً.
EJ_TOTAL = re.compile(r'\\*"totalItems\\*"\s*:\s*(\d+)')
EJ_PAGES = re.compile(r'\\*"totalPages\\*"\s*:\s*(\d+)')

FEEDS = [
    ("sale", "شقق للبيع", "https://www.emlakjet.com/satilik-daire/malatya/"),
    ("rent", "شقق للإيجار", "https://www.emlakjet.com/kiralik-daire/malatya/"),
]


def parse_list(html, deal):
    rows = []
    m = EJ_SCHEMA.search(html)
    if m:
        for x in (json.loads(m.group(1)).get("@graph") or []):
            if x.get("@type") != "RealEstateListing":
                continue
            ap = {p.get("name"): p.get("value")
                  for p in (x.get("additionalProperty") or [])}
            url = x.get("url") or ""
            mid = EJ_ID.search(url)
            if not mid:
                continue
            # «Koyunoğlu Mahallesi, Yeşilyurt» → حيّ، إلچة
            loc = [z.strip() for z in str(ap.get("Konum", "")).split(",")]
            mah = re.sub(r"\s*Mahallesi\s*$", "", loc[0] if loc else "").strip()
            rows.append({
                "src": "emlakjet",
                "id": mid.group(1),
                "deal": deal,
                "t": (x.get("name") or "").strip(),
                "ilce": loc[1] if len(loc) > 1 else "",
                "mah": mah,
                "rooms": (ap.get("Oda Sayısı") or "").strip() or None,
                "m2": to_int(ap.get("Metrekare")),
                "kat": (ap.get("Kat") or "").strip() or None,
                "p": (x.get("offers") or {}).get("price"),
                "d": x.get("datePosted") or "",
                "u": url,
                "img": (x.get("image") or ""),
            })
    total = EJ_TOTAL.search(html)
    pages = EJ_PAGES.search(html)
    return (rows,
            int(total.group(1)) if total else None,
            int(pages.group(1)) if pages else None)


def collect_feed(deal, base):
    items, reported, pages = {}, None, None
    page = 1
    while page <= MAX_PAGES:
        url = base if page == 1 else (base + "?sayfa=%d" % page)
        rows, tot, pg = parse_list(get(url), deal)
        if reported is None:
            reported = tot
        if pages is None:
            pages = pg
        if not rows:
            break
        for r in rows:
            items[r["id"]] = r
        print("  %s ص%d: %d إعلاناً — الإجمالي %d" % (deal, page, len(rows), len(items)))
        if pages and page >= pages:
            break
        if len(rows) < 20:
            break
        page += 1
        time.sleep(1.2)
    return list(items.values()), {"site_reported_total": reported, "pages": pages}


# ───────────────────────── قراءة صفحة الإعلان ─────────────────────────

EJ_LD = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
# الوسم يضع الوسم والقيمة في فقرتين متجاورتين، وترتيبهما يختلف بين الكتل،
# لذلك نلتقط الزوج ونقبله في الاتجاهين.
EJ_PAIR = re.compile(r'>([^<>]{1,60})</p><p[^>]*>([^<>]{1,60})</p>')
MARKUP_LABELS = ("Bina Yaşı", "Bulunduğu Kat", "Kat Sayısı", "Banyo Sayısı",
                 "Oda Sayısı", "Brüt", "Net", "En Az Değer", "En Fazla Değer",
                 "Tahmini Kira", "Geri Dönüş Süresi")


def _walk_props(o, out):
    if isinstance(o, list):
        for x in o:
            _walk_props(x, out)
        return
    if not isinstance(o, dict):
        return
    ap = o.get("additionalProperty")
    if isinstance(ap, list):
        for p in ap:
            if isinstance(p, dict) and p.get("name"):
                out[p["name"]] = p.get("value")
    for v in o.values():
        _walk_props(v, out)


def detail(listing_id):
    html = get("https://www.emlakjet.com/ilan/" + listing_id, tries=2)
    props = {}
    for m in EJ_LD.finditer(html):
        try:
            _walk_props(json.loads(m.group(1)), props)
        except Exception:
            pass
    for a, b in EJ_PAIR.findall(html):
        a, b = a.strip(), b.strip()
        if b in MARKUP_LABELS and a not in ("", b):
            props.setdefault(b, a)
        elif a in MARKUP_LABELS and b not in ("", a):
            props.setdefault(a, b)
    return props


DETAIL_KEYS = ("age_raw", "tapu", "isitma", "otopark", "kullanim", "krediye",
               "site", "asansor", "balkon", "esya", "mutfak", "ada", "parsel",
               "m2net", "floor", "floors", "banyo", "kira", "val_min",
               "val_max", "val_rent", "val_pb")


def apply_detail(r, p):
    r["age_raw"] = (p.get("Bina Yaşı") or "").strip() or None
    r["tapu"] = tapu_label(p.get("Tapu Durumu"))
    r["isitma"] = (p.get("Isıtma Tipi") or "").strip() or None
    r["otopark"] = (p.get("Otopark") or "").strip() or None
    r["kullanim"] = (p.get("Kullanım Durumu") or "").strip() or None
    r["krediye"] = kredi_label(p.get("Krediye Uygunluk"))
    r["site"] = yesno(p.get("Site İçerisinde"))
    r["asansor"] = yesno(p.get("Asansör"))
    r["balkon"] = yesno(p.get("Balkon"))
    r["esya"] = (p.get("Eşya Durumu") or "").strip() or None
    r["mutfak"] = (p.get("Mutfak") or "").strip() or None
    for src_key, dst in (("Ada", "ada"), ("Parsel", "parsel")):
        if p.get(src_key):
            r[dst] = str(p[src_key]).strip()
    r["m2net"] = to_int(p.get("Net"))
    r["floor"] = (p.get("Bulunduğu Kat") or "").strip() or None
    r["floors"] = to_int(p.get("Kat Sayısı"))
    r["banyo"] = to_int(p.get("Banyo Sayısı"))
    if not r.get("rooms") and p.get("Oda Sayısı"):
        r["rooms"] = str(p["Oda Sayısı"]).strip()
    # «Kira Getirisi» إيجار متوقَّع يعلنه المعلن — ليس عقداً قائماً.
    r["kira"] = to_int(p.get("Kira Getirisi"))
    # نطاق التقدير الآلي المعروض في الصفحة (Endeksa). تقدير طرف ثالث لا سعر بيع.
    r["val_min"] = to_int(p.get("En Az Değer"))
    r["val_max"] = to_int(p.get("En Fazla Değer"))
    r["val_rent"] = to_int(p.get("Tahmini Kira"))
    r["val_pb"] = to_int(p.get("Geri Dönüş Süresi"))
    return r


def enrich(rows, prev_by_id):
    """يملأ حقول صفحة الإعلان، ويعيد استعمال ما سبق جلبه بدل الطلب كل يوم."""
    cached = fetched = failed = 0
    for r in rows:
        old = prev_by_id.get(r["id"])
        if old and old.get("age_raw"):
            for k in DETAIL_KEYS:
                if old.get(k) is not None:
                    r[k] = old[k]
            if r.get("tapu"):
                r["tapu"] = tapu_label(r["tapu"])
            cached += 1
            continue
        if fetched >= DETAIL_BUDGET:
            continue
        try:
            p = detail(r["id"])
            fetched += 1
        except Exception as e:
            failed += 1
            if failed <= 3:
                print("  تعذّر جلب تفاصيل %s: %s" % (r["id"], str(e)[:80]),
                      file=sys.stderr)
            continue
        apply_detail(r, p)
        time.sleep(0.35)
    print("  تفاصيل الإعلانات: %d من الذاكرة · %d جُلبت · %d فشلت"
          % (cached, fetched, failed))
    return {"detail_cached": cached, "detail_fetched": fetched,
            "detail_failed": failed}


# ───────────────────────── الذاكرة والتعديلات ─────────────────────────

PREV_BY_ID = {}
PREV_FIRST = {}
# صحيح في التشغيلة الأولى وحدها: ملفّ الأمس بالشكل القديم، فلا سابقةَ يُقاس
# عليها «الجديد اليوم». نُعلن ذلك بدل أن نزعم أنّ كل السوق ظهر اليوم.
BOOTSTRAP = False


def load_previous():
    """يقرأ ملفّ الأمس. يقبل الشكلين: الوثيقة الحالية، وقاموس الروابط القديم.

    الملفّ القديم كان {رابط: سجلّ} كتبه وكيل لغويّ. نحتفظ منه بتاريخ أول ظهور
    وحده — وهو المعلومة الوحيدة التي لا يمكن استرجاعها من المصدر — ونستخرج
    المعرّف من ذيل الرابط.
    """
    try:
        with open(OUT, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return []
    if isinstance(d, dict) and isinstance(d.get("items"), list):
        for r in d["items"]:
            PREV_BY_ID[r.get("id")] = r
            if r.get("first_seen"):
                PREV_FIRST[r["id"]] = r["first_seen"]
        return d["items"]
    if isinstance(d, dict):
        global BOOTSTRAP
        BOOTSTRAP = True
        n = 0
        for url, r in d.items():
            if not isinstance(r, dict):
                continue
            m = EJ_ID.search(str(url))
            if not m:
                continue
            if r.get("first_seen"):
                PREV_FIRST[m.group(1)] = r["first_seen"]
                n += 1
        print("  رُحِّل تاريخ أول ظهور لـ%d إعلاناً من الملفّ القديم" % n)
    return []


def apply_overrides(rows):
    """يطبّق ما كتبه الإنسان فوق ما سحبته الآلة.

    hidden: مفاتيح تُخفى · patch: حقول تُبدَّل في إعلان قائم · items: إعلانات
    يدوية ليست في المصدر. المفتاح «src:id».
    """
    stats = {"hidden": 0, "patched": 0, "manual": 0}
    try:
        with open(OVERRIDES, encoding="utf-8") as f:
            ov = json.load(f)
    except FileNotFoundError:
        return rows, stats
    except Exception as e:
        print("  تعذّرت قراءة ملفّ التعديلات (%s) — تُجوهِل: %s" % (OVERRIDES, e),
              file=sys.stderr)
        return rows, stats

    hidden = set(ov.get("hidden") or [])
    patch = ov.get("patch") or {}
    out = []
    for r in rows:
        k = "%s:%s" % (r.get("src") or "emlakjet", r.get("id"))
        if k in hidden:
            stats["hidden"] += 1
            continue
        if k in patch:
            r = dict(r)
            r.update({kk: vv for kk, vv in patch[k].items() if vv is not None})
            r["edited"] = True
            stats["patched"] += 1
        out.append(r)

    for it in (ov.get("items") or []):
        if not it.get("id") or not it.get("t"):
            continue
        it = dict(it)
        it["src"] = "manual"
        it.setdefault("deal", "sale")
        it.setdefault("agesrc", "أدخلتَه بنفسك")
        it.setdefault("age", AGE_UNK)
        it["manual"] = True
        out.append(it)
        stats["manual"] += 1

    if any(stats.values()):
        print("  تعديلات يدوية: %d مخفيّ · %d معدَّل · %d مُضاف"
              % (stats["hidden"], stats["patched"], stats["manual"]))
    return out, stats


# ───────────────────────── الترتيب اليومي ─────────────────────────
# ترتيب شفّاف بالكامل: كل نقطة مشتقّة من حقل معلَن في الإعلان، ولا شيء منه رأي.
# الغرض ترتيب القراءة لا التوصية بالشراء.

def score(r, ppm_med):
    pts, why = 0, []
    if r.get("age") in AGE_FRESH:
        pts += 35
        why.append("عمر البناء %s" % r["age"])
    elif r.get("age") == AGE_UNK:
        why.append("عمر البناء غير مذكور")
    if r.get("ppm") and ppm_med:
        ratio = r["ppm"] / ppm_med
        if ratio <= 0.75:
            pts += 25
            why.append("سعر المتر أدنى من وسيط الإلچة بـ%d٪" % round((1 - ratio) * 100))
        elif ratio <= 0.95:
            pts += 15
            why.append("سعر المتر دون وسيط الإلچة")
        elif ratio >= 1.25:
            pts -= 10
            why.append("سعر المتر أعلى من الوسيط بـ%d٪" % round((ratio - 1) * 100))
    if r.get("tapu") and "ملكية طوابق" in r["tapu"]:
        pts += 12
        why.append("طابو ملكية طوابق")
    elif r.get("tapu") and "مشاع" in r["tapu"]:
        pts -= 12
        why.append("طابو مشاع — يحتاج فرزاً")
    if r.get("krediye") == "صالح للتمويل":
        pts += 8
        why.append("قابل للتمويل المصرفي")
    if r.get("asansor"):
        pts += 4
    if r.get("site"):
        pts += 4
    if r.get("yield_"):
        if r["yield_"] >= 7:
            pts += 10
            why.append("عائد إيجاري إجمالي معلَن %.1f٪" % r["yield_"])
        elif r["yield_"] >= 5:
            pts += 5
    return max(0, min(100, pts)), why


def recommend(r, why):
    """نصّ وصفيّ مبنيّ على الحقول وحدها. لا وعد ولا ضمان ولا دعوة للشراء."""
    head = "ظهر اليوم" if r.get("new_today") else "مرصود"
    body = "، ".join(why) if why else "لا حقول مميِّزة معلنة"
    tail = "" if r.get("age") != AGE_UNK else " — تحقّق من عمر البناء ورخصة الإسكان قبل أي التزام"
    return "%s: %s%s" % (head, body, tail)


# ───────────────────────── الإخراج ─────────────────────────

def median_or_none(xs):
    xs = [x for x in xs if x]
    return int(statistics.median(sorted(xs))) if xs else None


def build_report(today, rows, stats):
    """سجلّ اليوم في السلسلة التي تقرأها aqar-board.html."""
    core = [r for r in rows if r.get("ilce") in CORE]
    sale = [r for r in core if r.get("deal") == "sale"]
    rent = [r for r in core if r.get("deal") == "rent"]
    med_ppm = median_or_none([r.get("ppm") for r in sale])
    med_rpm = median_or_none([r.get("ppm") for r in rent])
    top = []
    for r in sorted(sale, key=lambda x: (-(x.get("score") or 0), x.get("ppm") or 10**9))[:8]:
        top.append({
            "mah": r.get("mah"), "deal": "satilik", "rooms": r.get("rooms"),
            "m2": r.get("m2"), "price": r.get("p"), "ppm": r.get("ppm"),
            "rpm": 0, "sc": r.get("score"), "rec": r.get("rec"), "url": r.get("u"),
        })
    return {
        "date": today.date().isoformat(),
        "il": "Malatya",
        "ilce": "النواة الحضرية (Yeşilyurt+Battalgazi)",
        "n_sale": len(sale),
        "n_rent": len(rent),
        "hi": len([r for r in sale if r.get("age") in AGE_FRESH]),
        "med_ppm": med_ppm,
        "med_rpm": med_rpm,
        "yield_": (round(med_rpm * 12 / med_ppm * 100, 1)
                   if med_ppm and med_rpm else None),
        "top": top,
        "source": "Emlakjet — سحب آليّ حتميّ",
    }


def write_report(rec):
    try:
        with open(REPORTS, encoding="utf-8") as f:
            series = json.load(f)
        if not isinstance(series, list):
            series = []
    except Exception:
        series = []
    series = [x for x in series if x.get("date") != rec["date"]]
    series.append(rec)
    series.sort(key=lambda x: x.get("date") or "")
    with open(REPORTS, "w", encoding="utf-8") as f:
        json.dump(series, f, ensure_ascii=False, indent=1)
    print("كُتب %s — %d سجلّاً" % (REPORTS, len(series)))


def main():
    today = datetime.now(timezone.utc)
    iso = today.date().isoformat()
    prev_items = load_previous()

    collected, metas = [], []
    for deal, label, base in FEEDS:
        print("→ Emlakjet — شقق %s" % label)
        try:
            rows, meta = collect_feed(deal, base)
            if not rows:
                raise RuntimeError("لم يُسحب أي إعلان — يُرجَّح تغيّر بنية الصفحة.")
            collected += rows
            metas.append(dict(key="emlakjet-" + deal,
                              name="Emlakjet — شقق للـ%s" % label,
                              url=base, kind="سوق", deal=deal, status="ok",
                              count=len(rows), **meta))
        except Exception as e:
            print("  ✗ فشل %s: %s" % (label, e), file=sys.stderr)
            kept = [r for r in prev_items if r.get("deal") == deal]
            collected += kept
            metas.append(dict(key="emlakjet-" + deal,
                              name="Emlakjet — شقق للـ%s" % label,
                              url=base, kind="سوق", deal=deal, status="failed",
                              error=str(e)[:200], count=len(kept),
                              note="عُرضت بيانات آخر سحب ناجح لهذا المصدر"))

    if not collected:
        raise RuntimeError("لم يبقَ أي إعلان — لا يُكتب الملف، ويبقى ملفّ الأمس.")

    # التصفية على ولاية ملاطيا: الرابط الإقليمي لا يضمن ذلك وحده
    rows, outside = [], 0
    for r in collected:
        std = norm_district(r.get("ilce"))
        if not std:
            outside += 1
            continue
        r["ilce"] = std
        rows.append(r)
    if outside:
        print("  خارج ولاية ملاطيا — استُبعد %d إعلاناً" % outside)

    metas_enrich = enrich(rows, PREV_BY_ID)

    for r in rows:
        r["age"], r["age_min"] = age_bucket(r.get("age_raw"))
        r["agesrc"] = "معلَن في الإعلان" if r.get("age_raw") else "غير مذكور في الإعلان"
        r["fresh"] = r["age"] in AGE_FRESH
        m2 = r.get("m2")
        if m2 and (m2 > SUSPECT_M2 or m2 < 15):
            r["sus"] = True
        r["ppm"] = (round(r["p"] / r["m2"])
                    if (r.get("p") and r.get("m2") and not r.get("sus")) else None)
        # العائد الإجمالي من الإيجار المتوقَّع الذي يعلنه المعلن نفسه
        r["yield_"] = (round(r["kira"] * 12 / r["p"] * 100, 1)
                       if (r.get("deal") == "sale" and r.get("kira") and r.get("p"))
                       else None)
        r["first_seen"] = PREV_FIRST.get(r["id"]) or (
            PREV_BY_ID.get(r["id"], {}).get("first_seen")) or iso
        r["last_seen"] = iso
        r["new_today"] = (not BOOTSTRAP) and r["first_seen"] == iso

    rows, ov_stats = apply_overrides(rows)
    for meta in metas:
        meta["count"] = len([r for r in rows if
                             ("emlakjet-" + (r.get("deal") or "")) == meta["key"]])

    # وسيط سعر المتر لكل إلچة يُحتسب من إعلانات البيع وحدها
    by_sale = defaultdict(list)
    by_rent = defaultdict(list)
    for r in rows:
        if r.get("ppm"):
            (by_sale if r.get("deal") == "sale" else by_rent)[r["ilce"]].append(r["ppm"])

    # الوسيط يُحتسب مرّة واحدة لكل إلچة، ثمّ يُقاس عليه كل إعلان بيع فيها.
    med_by_ilce = {d: median_or_none(v) for d, v in by_sale.items()}
    med_rent_by_ilce = {d: median_or_none(v) for d, v in by_rent.items()}
    for r in rows:
        if r.get("deal") == "rent":
            # الترتيب معيارُه استثماريّ ولا ينطبق على الإيجار، فلا يُرتَّب.
            r["score"] = None
            med = med_rent_by_ilce.get(r["ilce"])
            if r.get("ppm") and med:
                d = round((r["ppm"] / med - 1) * 100)
                r["rec"] = ("إيجار: %d ₺ للمتر شهرياً — %s وسيط الإلچة بـ%d٪"
                            % (r["ppm"], "فوق" if d >= 0 else "دون", abs(d)))
            else:
                r["rec"] = "إيجار: المساحة أو البدل غير معلن بما يكفي للمقارنة"
            continue
        sc, why = score(r, med_by_ilce.get(r["ilce"]))
        r["score"] = sc
        r["rec"] = recommend(r, why)

    rows.sort(key=lambda r: (r.get("d") or "", r.get("id") or ""), reverse=True)

    stats = []
    for d in ALLOWED:
        rs = [r for r in rows if r["ilce"] == d]
        s_ppm = sorted(by_sale.get(d, []))
        r_ppm = sorted(by_rent.get(d, []))
        med_s = median_or_none(s_ppm)
        med_r = median_or_none(r_ppm)
        stats.append({
            "ilce": d,
            "n": len(rs),
            "n_sale": len([r for r in rs if r.get("deal") == "sale"]),
            "n_rent": len([r for r in rs if r.get("deal") == "rent"]),
            "n_fresh": len([r for r in rs if r.get("fresh")]),
            "ppm_med": med_s,
            "ppm_min": s_ppm[0] if s_ppm else None,
            "ppm_max": s_ppm[-1] if s_ppm else None,
            "rpm_med": med_r,
            "p_med": median_or_none([r.get("p") for r in rs if r.get("deal") == "sale"]),
            "yield_": round(med_r * 12 / med_s * 100, 1) if (med_s and med_r) else None,
            "note": LEGACY.get(d),
        })
    stats.sort(key=lambda s: -s["n"])

    age_stats = []
    for a in AGE_ORDER:
        rs = [r for r in rows if r.get("age") == a and r.get("deal") == "sale"]
        pp = sorted(r["ppm"] for r in rs if r.get("ppm"))
        age_stats.append({
            "age": a,
            "n": len([r for r in rows if r.get("age") == a]),
            "n_sale": len(rs),
            "ppm_med": median_or_none(pp),
            "ppm_p10": pp[int(len(pp) * 0.10)] if pp else None,
            "ppm_p90": pp[int(len(pp) * 0.90)] if pp else None,
            "n_priced": len(pp),
        })

    sale_ppm = sorted(r["ppm"] for r in rows if r.get("ppm") and r.get("deal") == "sale")
    rent_ppm = sorted(r["ppm"] for r in rows if r.get("ppm") and r.get("deal") == "rent")
    sale_p = [r["p"] for r in rows if r.get("p") and r.get("deal") == "sale"]

    n_manual = len([r for r in rows if r.get("src") == "manual"])
    if n_manual:
        metas.append({"key": "manual", "name": "إدخال يدوي من لوحة الإدارة",
                      "url": "admin.html", "kind": "يدوي", "status": "ok",
                      "count": n_manual,
                      "price_note": "ما أدخلتَه بنفسك — لا سحب آليّ"})
    metas.append(dict(key="_detail", name="تفاصيل صفحات الإعلانات",
                      kind="داخليّ", status="ok", **metas_enrich))

    doc = {
        "updated": iso,
        "province": "Malatya",
        "scope": "ولاية ملاطيا فقط — شقق معروضة للبيع وللإيجار على Emlakjet",
        "total": len(rows),
        "sources": metas,
        "note": ("الأسعار كما يعلنها البائع أو المكتب — ليست تقييماً ولا عرضاً ملزماً. "
                 "«عمر البناء» و«نوع الطابو» منقولان حرفياً عمّا صرّح به الإعلان، "
                 "والوثيقة المُلزِمة هي قيد الطابو ورخصة الإسكان (İskân) من البلدية. "
                 "العائد الإيجاري إجماليّ قبل الضريبة والإدارة والشواغر."),
        "summary": {
            "districts_with_listings": len([s for s in stats if s["n"] and s["ilce"] in DISTRICTS]),
            "districts_total": len(DISTRICTS),
            "n_sale": len([r for r in rows if r.get("deal") == "sale"]),
            "n_rent": len([r for r in rows if r.get("deal") == "rent"]),
            "n_fresh": len([r for r in rows if r.get("fresh")]),
            "new_today": len([r for r in rows if r.get("new_today")]),
            "bootstrap": BOOTSTRAP,
            "ppm_median": median_or_none(sale_ppm),
            "ppm_p10": sale_ppm[int(len(sale_ppm) * 0.10)] if sale_ppm else None,
            "ppm_p90": sale_ppm[int(len(sale_ppm) * 0.90)] if sale_ppm else None,
            "rpm_median": median_or_none(rent_ppm),
            "yield_median": (round(median_or_none(rent_ppm) * 12
                                   / median_or_none(sale_ppm) * 100, 1)
                             if sale_ppm and rent_ppm else None),
            "price_min": min(sale_p) if sale_p else None,
            "price_max": max(sale_p) if sale_p else None,
            "flagged": len([r for r in rows if r.get("sus")]),
            "dropped_outside_province": outside,
            "overrides": ov_stats,
            "by_age": {a: len([r for r in rows if r.get("age") == a]) for a in AGE_ORDER},
            "by_rooms": {k: len([r for r in rows if r.get("rooms") == k])
                         for k in sorted({r.get("rooms") for r in rows if r.get("rooms")})},
            "by_tapu": {t: len([r for r in rows if r.get("tapu") == t])
                        for t in sorted({r.get("tapu") for r in rows if r.get("tapu")})},
            "age_declared": len([r for r in rows if r.get("age_raw")]),
        },
        "stats": stats,
        "age_stats": age_stats,
        "items": rows,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("كُتب %s — %d إعلاناً (%d بيع · %d إيجار)"
          % (OUT, len(rows), doc["summary"]["n_sale"], doc["summary"]["n_rent"]))
    print("  الأعمار: %s" % doc["summary"]["by_age"])

    write_report(build_report(today, rows, stats))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("فشل السحب: %s" % e, file=sys.stderr)
        sys.exit(1)
