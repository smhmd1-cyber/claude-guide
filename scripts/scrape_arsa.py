#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سحب إعلانات بيع الأراضي في ولاية ملاطيا من مصدرين — سوقيّ ورسميّ.

المصدر ١ — Emlakjet (سوق):
    صفحات نتائج «satilik-arsa/malatya». كل صفحة تحمل
    <script id="listing-realestate-schema" type="application/ld+json"> فيه @graph
    من كائنات schema.org/RealEstateListing. نقرأ الحقول البنيوية مباشرةً بدل تحليل
    شجرة الـHTML: أدقّ، والحقول كاملة حتى للبطاقات التي لم تُعرض بعد.
    السعر هنا = ما يطلبه البائع.

المصدر ٢ — ilan.gov.tr (رسميّ · هيئة الإعلانات الصحفية BİK):
    منصّة النشر الرسمية لإعلانات البيع القضائي (İCRA) والمزايدات العامة (İHALE).
    واجهة عامة: POST /api/api/services/app/Ad/AdsByFilter
    الجسم: {"keys":{"ats":["2"]},"sorting":null,"skipCount":N,"maxResultCount":20}
    ats=2 قضائي · ats=3 مزايدة. القيم يجب أن تكون مصفوفات.
    لا يوجد مفتاح تصفية بالولاية في هذه الواجهة — جُرِّب واسمه غير معلن — فالتصفية
    على ملاطيا تجري عندنا بعد الجلب اعتماداً على addressCityName.
    السعر هنا = «muhammen bedel»: تقدير رسمي مُعتمَد لا طلب بائع، وهو حدّ المزايدة.

لماذا مصدران فقط: sahibinden و hepsiemlak و hurriyetemlak تردّ 403 على أي عميل
HTTP عادي (حماية آلية)، و zingat صار يحوّل إلى hepsiemlak بعد الدمج. لا يمكن
سحبها من عدّاء GitHub، ولا نتظاهر بغير ذلك.

عند فشل مصدر: يُسجَّل فشله في الملف ويستمرّ الباقي. عند فشل الجميع: خروج بخطأ
دون كتابة الملف، فيبقى ملف الأمس كما هو.
"""

import json
import os
import re
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta

import requests

OUT = os.environ.get("ARSA_OUT", "malatya/data/arsa-listings.json")
FULL_SCAN = os.environ.get("ILAN_FULL_SCAN", "") == "1"

SUSPECT_M2 = 1_000_000     # أكبر من ذلك = خطأ فاصل في المصدر لا قطعة حقيقية
AUCTION_GRACE_DAYS = 7     # يُسقَط إعلان المزاد بعد أسبوع من آخر موعد بيع

DISTRICTS = [
    "Battalgazi", "Yeşilyurt", "Akçadağ", "Arapgir", "Arguvan", "Darende",
    "Doğanşehir", "Doğanyol", "Hekimhan", "Kale", "Kuluncak", "Pütürge", "Yazıhan",
]
DISTRICTS_UP = {d.upper(): d for d in DISTRICTS}

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.6",
}


# ───────────────────────── أدوات مشتركة ─────────────────────────

def get(url, tries=4, **kw):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=45, **kw)
            if r.status_code == 200:
                return r.text
            last = "HTTP %d" % r.status_code
        except Exception as e:
            last = "%s: %s" % (type(e).__name__, e)
        time.sleep(3 * (i + 1))
    raise RuntimeError("تعذّر جلب %s — %s" % (url, last))


def post_json(url, body, tries=4):
    last = None
    for i in range(tries):
        try:
            r = requests.post(url, json=body, timeout=45,
                              headers=dict(HEADERS, **{"Content-Type": "application/json"}))
            if r.status_code == 200:
                return r.json()
            last = "HTTP %d" % r.status_code
        except Exception as e:
            last = "%s: %s" % (type(e).__name__, e)
        time.sleep(3 * (i + 1))
    raise RuntimeError("تعذّر استدعاء %s — %s" % (url, last))


NUM_RE = re.compile(r'(\d[\d\.,]*)\s*(m²|m2|metrekare|dönüm|donum|hektar)', re.I)


def m2_from_text(txt):
    """استخراج المساحة من نصّ تركي. يعيد None إن لم يجد رقماً معقولاً.

    التركية تستعمل النقطة للآلاف والفاصلة للعشور، لكن كتّاب الإعلانات يخلطون.
    القاعدة: «1728.49» بجزء صحيح ≤٤ خانات وكسر من خانتين تُقرأ عشرية؛ وما عداها
    تُعامَل النقاط كفواصل آلاف.
    """
    if not txt:
        return None
    best = None
    for m in NUM_RE.finditer(txt):
        raw, unit = m.group(1), m.group(2).lower()
        val = None
        dec = re.fullmatch(r'(\d{1,4})\.(\d{2})', raw)
        if dec:
            val = float(raw)
        else:
            cleaned = raw.replace(".", "").replace(",", ".")
            try:
                val = float(cleaned)
            except ValueError:
                continue
        if unit.startswith("dön") or unit.startswith("don"):
            val *= 1000
        elif unit.startswith("hektar"):
            val *= 10000
        val = int(round(val))
        if 10 <= val <= SUSPECT_M2 and (best is None or val > best):
            best = val
    return best


PRICE_RE = re.compile(r'([\d\.]+)(?:,\d+)?\s*₺')


def price_from_text(txt):
    if not txt:
        return None
    m = PRICE_RE.search(txt)
    if not m:
        return None
    try:
        return int(m.group(1).replace(".", ""))
    except ValueError:
        return None


def norm_district(name):
    """يعيد اسم الإلچة بصيغتها المعيارية، أو None إن كانت خارج ولاية ملاطيا."""
    if not name:
        return None
    n = name.strip()
    up = n.upper().replace("I", "İ") if False else n.upper()
    for key, std in DISTRICTS_UP.items():
        if up == key or n.casefold() == std.casefold():
            return std
    # «Merkez» في ملاطيا تعني باتالغازي تاريخياً — لا نخمّن، نتركها كما هي
    return None


# ───────────────────────── المصدر ١: Emlakjet ─────────────────────────

EJ_BASE = "https://www.emlakjet.com/satilik-arsa/malatya/"
EJ_IMG = "https://imaj.emlakjet.com/resize/640/0/listing/"
EJ_SCHEMA = re.compile(
    r'<script[^>]+id="listing-realestate-schema"[^>]*>(.*?)</script>', re.S)
EJ_ID = re.compile(r'-(\d+)$')
# العدّاد المرئي مقسوم بوسم وتعليق HTML، لذلك لا ينفع بحث نصّي ساذج؛
# وحمولة Next.js تحمل totalItems/totalPages صراحةً.
EJ_TOTALS = [
    re.compile(r'\\*"totalItems\\*"\s*:\s*(\d+)'),
    re.compile(r'>(\d[\d\.]*)</span>[^<]*<!--[^>]*-->\s*ilan bulundu'),
    re.compile(r'([\d\.]+)\s*ilan bulundu'),
]
EJ_PAGES = re.compile(r'\\*"totalPages\\*"\s*:\s*(\d+)')


def ej_parse(html):
    m = EJ_SCHEMA.search(html)
    rows = []
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
            loc = [z.strip() for z in str(ap.get("Konum", "")).split(",")]
            raw_m2 = re.sub(r"[^0-9]", "", str(ap.get("Metrekare", "")))
            rows.append({
                "src": "emlakjet",
                "id": mid.group(1),
                "t": (x.get("name") or "").strip(),
                "ilce": loc[1] if len(loc) > 1 else "",
                "mah": loc[0] if loc else "",
                "m2": int(raw_m2) if raw_m2 else None,
                "p": (x.get("offers") or {}).get("price"),
                "d": x.get("datePosted") or "",
                "u": "https://www.emlakjet.com/ilan/" + mid.group(1),
                "img": (x.get("image") or "").replace(EJ_IMG, ""),
            })
    total = None
    for rx in EJ_TOTALS:
        t = rx.search(html)
        if t:
            total = int(t.group(1).replace(".", ""))
            break
    pages = None
    t = EJ_PAGES.search(html)
    if t:
        pages = int(t.group(1))
    return rows, total, pages


def source_emlakjet():
    items, reported, pages = {}, None, None
    page = 1
    while page <= 40:
        url = EJ_BASE if page == 1 else (EJ_BASE + "?sayfa=%d" % page)
        rows, tot, pg = ej_parse(get(url))
        if reported is None:
            reported = tot
        if pages is None:
            pages = pg
        if not rows:
            break
        for r in rows:
            items[r["id"]] = r
        print("  emlakjet ص%d: %d إعلاناً — الإجمالي %d" % (page, len(rows), len(items)))
        if pages and page >= pages:
            break
        if len(rows) < 30:
            break
        page += 1
        time.sleep(1.5)
    if not items:
        raise RuntimeError("لم يُسحب أي إعلان — يُرجَّح تغيّر بنية الصفحة أو حجب الطلب.")
    return list(items.values()), {"site_reported_total": reported, "pages": pages}


# ───────────────────────── المصدر ٢: ilan.gov.tr ─────────────────────────

BIK_API = "https://www.ilan.gov.tr/api/api/services/app/Ad/AdsByFilter"
BIK_PAGE = 20
BIK_ATS = {"2": "بيع قضائي (İCRA)", "3": "مزايدة عامة (İHALE)"}
# فئات الأرض داخل قسم «Emlak»: أرسا · تَرلا وأراضٍ زراعية وبساتين وكروم
BIK_LAND = re.compile(r'/emlak-(arsa|tarla|tarim|bag|bahce|zeytinlik)', re.I)
BIK_SCAN_PAGES = 40 if not FULL_SCAN else 2000


def bik_pick(filters, key):
    for f in (filters or []):
        if f.get("key") == key:
            return f.get("value")
    return None


def source_ilangovtr():
    """يمسح أحدث الإعلانات ويحتفظ بما يقع في ولاية ملاطيا ويخصّ الأرض.

    الواجهة لا تتيح تصفية بالولاية، والترتيب الافتراضي من الأحدث تقريباً، لذلك
    المسح تراكمي: كل يوم يُقرأ رأس القائمة ويُدمَج مع ما سبق. ILAN_FULL_SCAN=1
    يمسح الأرشيف كاملاً مرّة واحدة (بطيء — يُشغَّل يدوياً عند الحاجة).
    """
    found, seen, scanned = [], set(), 0
    for ats, label in BIK_ATS.items():
        for page in range(BIK_SCAN_PAGES):
            j = post_json(BIK_API, {"keys": {"ats": [ats]}, "sorting": None,
                                    "skipCount": page * BIK_PAGE,
                                    "maxResultCount": BIK_PAGE})
            ads = ((j or {}).get("result") or {}).get("ads") or []
            if not ads:
                break
            scanned += len(ads)
            for a in ads:
                if (a.get("addressCityName") or "").upper() != "MALATYA":
                    continue
                url = a.get("urlStr") or ""
                if not BIK_LAND.search(url):
                    continue
                aid = str(a.get("id"))
                if aid in seen:
                    continue
                seen.add(aid)
                f = a.get("adTypeFilters") or []
                title = (a.get("title") or "").strip()
                found.append({
                    "src": "ilangovtr",
                    "id": aid,
                    "t": title,
                    "ilce": norm_district(a.get("addressCountyName")) or (a.get("addressCountyName") or ""),
                    "mah": "",
                    "m2": m2_from_text(title),
                    "p": price_from_text(bik_pick(f, "Muhammen Bedeli") or ""),
                    "d": (a.get("publishStartDate") or "")[:10],
                    "u": "https://www.ilan.gov.tr" + url,
                    "img": "",
                    "kind": label,
                    "org": (a.get("advertiserName") or "").strip(),
                    "sale1": bik_pick(f, "Birinci Satış Günü") or bik_pick(f, "İhale ve Teklif Açma Tarihi"),
                    "sale2": bik_pick(f, "İkinci Satış Günü"),
                    "dosya": bik_pick(f, "Dosya No") or bik_pick(f, "İhale Kayıt No"),
                })
            time.sleep(0.35)
    print("  ilan.gov.tr: فُحص %d إعلاناً، منها %d في ملاطيا وتخصّ الأرض" % (scanned, len(found)))
    return found, {"scanned": scanned, "full_scan": FULL_SCAN}


# ───────────────────────── الدمج والإخراج ─────────────────────────

def parse_tr_date(s):
    if not s:
        return None
    m = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', s)
    if not m:
        return None
    try:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), tzinfo=timezone.utc)
    except ValueError:
        return None


def load_previous():
    try:
        with open(OUT, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def main():
    today = datetime.now(timezone.utc)
    prev = load_previous()
    prev_items = prev.get("items") or []

    adapters = [
        ("emlakjet", "Emlakjet", "https://www.emlakjet.com/satilik-arsa/malatya/",
         "سوق", "سعر يطلبه البائع أو المكتب", source_emlakjet),
        ("ilangovtr", "ilan.gov.tr — هيئة الإعلانات الصحفية (BİK)",
         "https://www.ilan.gov.tr/ilan/kategori/1/emlak",
         "رسميّ", "بدل محمّن: تقدير رسمي معتمَد وحدٌّ أدنى للمزايدة", source_ilangovtr),
    ]

    collected, metas = {}, []
    for key, name, url, kind, price_note, fn in adapters:
        print("→ %s" % name)
        try:
            rows, meta = fn()
            collected[key] = rows
            metas.append(dict(key=key, name=name, url=url, kind=kind,
                              price_note=price_note, status="ok",
                              count=len(rows), **meta))
        except Exception as e:
            print("  ✗ فشل %s: %s" % (name, e), file=sys.stderr)
            kept = [r for r in prev_items if r.get("src") == key]
            collected[key] = kept
            metas.append(dict(key=key, name=name, url=url, kind=kind,
                              price_note=price_note, status="failed",
                              error=str(e)[:200], count=len(kept),
                              note="عُرضت بيانات آخر سحب ناجح لهذا المصدر"))

    # المصدر الرسمي تراكمي: نضمّ ما سبق ثم نُسقط المزادات المنتهية
    if any(m["key"] == "ilangovtr" and m["status"] == "ok" for m in metas):
        merged = {r["id"]: r for r in prev_items if r.get("src") == "ilangovtr"}
        for r in collected["ilangovtr"]:
            merged[r["id"]] = r
        alive, expired = [], 0
        for r in merged.values():
            last = parse_tr_date(r.get("sale2")) or parse_tr_date(r.get("sale1"))
            if last and last < today - timedelta(days=AUCTION_GRACE_DAYS):
                expired += 1
                continue
            alive.append(r)
        collected["ilangovtr"] = alive
        for m in metas:
            if m["key"] == "ilangovtr":
                m["count"] = len(alive)
                m["expired_dropped"] = expired
        print("  ilan.gov.tr: %d محفوظاً بعد الدمج، %d مزاداً منتهياً أُسقط" % (len(alive), expired))

    rows, outside = [], 0
    for key in collected:
        for r in collected[key]:
            std = norm_district(r.get("ilce"))
            if not std:
                outside += 1
                print("خارج ولاية ملاطيا — استُبعد: %s/%s (%s)" % (r.get("src"), r.get("id"), r.get("ilce")))
                continue
            r["ilce"] = std
            rows.append(r)

    if not rows:
        raise RuntimeError("لم يبقَ أي إعلان بعد التصفية — لا يُكتب الملف.")

    # المساحة: إن كانت المعلنة غير معقولة نحاول انتشالها من نصّ العنوان
    recovered = 0
    for r in rows:
        m2 = r.get("m2")
        if m2 and m2 > SUSPECT_M2:
            alt = m2_from_text(r.get("t"))
            if alt:
                r["m2"], r["m2src"] = alt, "العنوان"
                recovered += 1
            else:
                r["sus"] = True
        r["ppm"] = (round(r["p"] / r["m2"])
                    if (r.get("p") and r.get("m2") and not r.get("sus")) else None)
    rows.sort(key=lambda r: (r.get("d") or "", r.get("id") or ""), reverse=True)

    # وسيط سعر المتر يُحتسب من إعلانات السوق وحدها: البدل المحمّن تقدير قضائي
    # لا سعر سوق، وخلطهما يفسد الوسيط.
    by = defaultdict(list)
    for r in rows:
        if r.get("ppm") and r.get("src") == "emlakjet":
            by[r["ilce"]].append(r)
    stats = []
    for d in DISTRICTS:
        n = len([r for r in rows if r["ilce"] == d])
        rs = by.get(d, [])
        if rs:
            pp = sorted(x["ppm"] for x in rs)
            pr = sorted(x["p"] for x in rs)
            stats.append({"ilce": d, "n": n, "ppm_med": int(statistics.median(pp)),
                          "ppm_min": pp[0], "ppm_max": pp[-1],
                          "p_med": int(statistics.median(pr))})
        else:
            stats.append({"ilce": d, "n": n, "ppm_med": None, "ppm_min": None,
                          "ppm_max": None, "p_med": None})
    stats.sort(key=lambda s: -s["n"])

    market = [r["ppm"] for r in rows if r.get("ppm") and r.get("src") == "emlakjet"]
    market.sort()
    prices = [r["p"] for r in rows if r.get("p")]
    doc = {
        "updated": today.date().isoformat(),
        "province": "Malatya",
        "scope": "إعلانات بيع الأراضي (arsa/tarla/bahçe) في ولاية ملاطيا فقط",
        "total": len(rows),
        "sources": metas,
        "note": ("أسعار المصدر السوقيّ كما يعلنها البائع أو المكتب — ليست تقييماً. "
                 "وأسعار المصدر الرسميّ بدلٌ محمّن: تقدير معتمَد وحدٌّ أدنى للمزايدة، لا سعر بيع. "
                 "تحقّق من الطابو والإفراز والحالة العمرانية قبل أي التزام."),
        "summary": {
            "districts_with_listings": len([s for s in stats if s["n"]]),
            "districts_total": len(DISTRICTS),
            "ppm_median": int(statistics.median(market)) if market else None,
            "ppm_p10": market[int(len(market) * 0.10)] if market else None,
            "ppm_p90": market[int(len(market) * 0.90)] if market else None,
            "price_min": min(prices) if prices else None,
            "price_max": max(prices) if prices else None,
            "flagged": len([r for r in rows if r.get("sus")]),
            "m2_recovered": recovered,
            "dropped_outside_province": outside,
            "by_source": {k: len([r for r in rows if r.get("src") == k]) for k in collected},
        },
        "stats": stats,
        "items": rows,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("كُتب %s — %d إعلاناً %s" % (OUT, len(rows), doc["summary"]["by_source"]))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("فشل السحب: %s" % e, file=sys.stderr)
        sys.exit(1)
