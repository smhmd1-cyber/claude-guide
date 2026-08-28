#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سحب إعلانات بيع الأراضي (arsa / tarla / bahçe) في ولاية ملاطيا فقط.

المصدر: صفحات نتائج Emlakjet لتصنيف «satilik-arsa» المقيّد بولاية ملاطيا.
الطريقة: كل صفحة نتائج تحمل وسم <script id="listing-realestate-schema" type="application/ld+json">
يتضمّن @graph من كائنات schema.org/RealEstateListing — نقرأ منه الحقول البنيوية مباشرةً
بدل تحليل شجرة الـHTML (أثبت أنه أدقّ: الحقول كاملة حتى للبطاقات غير المعروضة بعد).

عند أي فشل: يخرج بحالة غير صفرية دون كتابة الملف، فيبقى ملف الأمس كما هو.
"""

import json
import os
import re
import statistics
import sys
import time
from collections import defaultdict
from datetime import date, timezone, datetime

import requests

BASE = "https://www.emlakjet.com/satilik-arsa/malatya/"
OUT = os.environ.get("ARSA_OUT", "malatya/data/arsa-listings.json")
PER_PAGE = 30
MAX_PAGES = 40           # سقف أمان — الحلقة تتوقّف من تلقائها عند أول صفحة فارغة
IMG_PREFIX = "https://imaj.emlakjet.com/resize/640/0/listing/"
SUSPECT_M2 = 1_000_000   # مساحة أكبر من ذلك = خطأ فاصل عشري في المصدر، لا قطعة حقيقية

# الإلچات الثلاث عشرة لولاية ملاطيا — ثابتة، تُستعمل للتحقّق أن كل نتيجة داخل الولاية
DISTRICTS = [
    "Battalgazi", "Yeşilyurt", "Akçadağ", "Arapgir", "Arguvan", "Darende",
    "Doğanşehir", "Doğanyol", "Hekimhan", "Kale", "Kuluncak", "Pütürge", "Yazıhan",
]

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.6",
    "Accept": "text/html,application/xhtml+xml",
}

SCHEMA_RE = re.compile(
    r'<script[^>]+id="listing-realestate-schema"[^>]*>(.*?)</script>', re.S)
TOTAL_RE = re.compile(r'([\d\.]+)\s*ilan bulundu')
ID_RE = re.compile(r'-(\d+)$')


def fetch(url, tries=4):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=45)
            if r.status_code == 200:
                return r.text
            last = "HTTP %d" % r.status_code
        except Exception as e:                       # شبكة / مهلة
            last = "%s: %s" % (type(e).__name__, e)
        time.sleep(3 * (i + 1))
    raise RuntimeError("تعذّر جلب %s — %s" % (url, last))


def parse_page(html):
    m = SCHEMA_RE.search(html)
    if not m:
        return [], None
    graph = json.loads(m.group(1)).get("@graph") or []
    total = None
    t = TOTAL_RE.search(html)
    if t:
        total = int(t.group(1).replace(".", ""))
    out = []
    for x in graph:
        if x.get("@type") != "RealEstateListing":
            continue
        ap = {p.get("name"): p.get("value")
              for p in (x.get("additionalProperty") or [])}
        url = x.get("url") or ""
        mid = ID_RE.search(url)
        if not mid:
            continue
        loc = [z.strip() for z in str(ap.get("Konum", "")).split(",")]
        m2 = re.sub(r"[^0-9]", "", str(ap.get("Metrekare", "")))
        offers = x.get("offers") or {}
        out.append({
            "id": mid.group(1),
            "t": (x.get("name") or "").strip(),
            "ilce": loc[1] if len(loc) > 1 else "",
            "mah": loc[0] if loc else "",
            "m2": int(m2) if m2 else None,
            "p": offers.get("price"),
            "d": x.get("datePosted") or "",
            "u": "https://www.emlakjet.com/ilan/" + mid.group(1),
            "img": (x.get("image") or "").replace(IMG_PREFIX, ""),
        })
    return out, total


def main():
    items, reported = {}, None
    for page in range(1, MAX_PAGES + 1):
        url = BASE if page == 1 else (BASE + "?sayfa=%d" % page)
        rows, tot = parse_page(fetch(url))
        if tot and not reported:
            reported = tot
        if not rows:
            break
        new = 0
        for r in rows:
            if r["id"] not in items:
                new += 1
            items[r["id"]] = r
        print("صفحة %d: %d إعلاناً (%d جديد) — الإجمالي %d"
              % (page, len(rows), new, len(items)))
        if len(rows) < PER_PAGE:
            break
        time.sleep(1.5)

    if not items:
        raise RuntimeError("لم يُسحب أي إعلان — يُرجَّح أن بنية المصدر تغيّرت أو أن الطلب حُجب.")

    # ولاية ملاطيا فقط — أي إلچة خارج القائمة تُستبعد وتُسجَّل
    dropped = [r for r in items.values() if r["ilce"] not in DISTRICTS]
    for r in dropped:
        print("خارج ولاية ملاطيا — استُبعد: %s (%s)" % (r["id"], r["ilce"]))
        del items[r["id"]]

    rows = list(items.values())
    for r in rows:
        sus = bool(r["m2"] and r["m2"] > SUSPECT_M2)
        r["ppm"] = (round(r["p"] / r["m2"])
                    if (r["p"] and r["m2"] and not sus) else None)
        if sus:
            r["sus"] = True
    rows.sort(key=lambda r: (r["d"] or "", r["id"]), reverse=True)

    by = defaultdict(list)
    for r in rows:
        if r.get("ppm"):
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

    allppm = sorted(r["ppm"] for r in rows if r.get("ppm"))
    prices = [r["p"] for r in rows if r["p"]]
    doc = {
        "updated": datetime.now(timezone.utc).date().isoformat(),
        "province": "Malatya",
        "scope": "إعلانات بيع الأراضي (arsa/tarla/bahçe) في ولاية ملاطيا فقط",
        "total": len(rows),
        "source": {
            "name": "Emlakjet",
            "url": BASE,
            "method": "JSON-LD (schema.org RealEstateListing) من كل صفحات النتائج",
            "site_reported_total": reported,
            "fetched": datetime.now(timezone.utc).date().isoformat(),
        },
        "note": ("الأسعار والمساحات كما يعلنها البائع/المكتب على المنصة — ليست تقييماً "
                 "ولا سعراً رسمياً. تحقّق من الطابو والإفراز والحالة العمرانية قبل أي التزام."),
        "summary": {
            "districts_with_listings": len([s for s in stats if s["n"]]),
            "districts_total": len(DISTRICTS),
            "ppm_median": int(statistics.median(allppm)) if allppm else None,
            "ppm_p10": allppm[int(len(allppm) * 0.10)] if allppm else None,
            "ppm_p90": allppm[int(len(allppm) * 0.90)] if allppm else None,
            "price_min": min(prices) if prices else None,
            "price_max": max(prices) if prices else None,
            "flagged": len([r for r in rows if r.get("sus")]),
            "dropped_outside_province": len(dropped),
        },
        "stats": stats,
        "items": rows,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("كُتب %s — %d إعلاناً (المصدر أعلن %s)" % (OUT, len(rows), reported))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("فشل السحب: %s" % e, file=sys.stderr)
        sys.exit(1)
