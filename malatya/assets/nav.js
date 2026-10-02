/* build: 2026-10-02 — بند «ملابسي» في السايدبار
   ===========================================================
   منظومة ملاطيا — المُشغّل العائم (شريط تنقّل موحّد)
   يُحقن في كل صفحة عبر:  <script src="assets/nav.js" defer></script>
   لا يلمس تخطيط الصفحة إطلاقاً — زر عائم + لوحة منزلقة.
   =========================================================== */
(function () {
  'use strict';

  var BASE = (function () {
    // يحدّد الجذر تلقائياً سواء كانت الصفحة في /malatya/ أو /malatya/reports/
    var s = document.currentScript || (function () {
      var a = document.getElementsByTagName('script');
      for (var i = a.length - 1; i >= 0; i--) if (/nav\.js/.test(a[i].src)) return a[i];
      return null;
    })();
    if (!s) return '';
    return s.src.replace(/assets\/nav\.js.*$/, '');
  })();

  var SECTIONS = [
    { g: 'المنظومة' , items: [
      { h: 'index.html',       i: '🎛️', n: 'مركز التحكّم',           d: 'الصفحة الرئيسية — كل شيء من هنا' },
      { h: 'daleel.html',      i: '📖', n: 'الدليل + النشرة اليومية', d: 'المعيشة · السكن · النقل · السياحة — يتحدّث يومياً' },
      { h: 'aroud.html',       i: '🛒', n: 'العروض والحملات',        d: 'تخفيضات السوبرماركت والأسواق الأسبوعية — كل صباح' },
      { h: 'rijal.html',       i: '👔', n: 'ملابسي',                 d: 'ملابس رجالية كلاسيكية بمقاس 54–56 وXXL — ما يتوفّر بمقاسي فعلاً' },
      { h: 'mujaz.html',       i: '🧭', n: 'الموجز القراري',          d: 'ما يمسّ القرار اليوم — ومؤشّر السعر الحقيقي' }
    ]},
    { g: 'الأدوات الحيّة', items: [
      { h: 'aqar.html',        i: '🔎', n: 'محرّك البحث العقاري',     d: 'شقق ≤3 سنوات فقط — فلترة وفرز وخرائط' },
      { h: 'aqar-board.html',  i: '🏢', n: 'لوحة العقارات',            d: 'مؤشّرات السوق اليومية + أفضل الفرص' },
      { h: 'land-board.html',  i: '🌾', n: 'لوحة الأراضي',             d: 'رصد القطع وفجوة التحويل يومياً' },
      { h: 'arsa.html',        i: '🗺️', n: 'أراضي البناء للبيع',    d: 'كل إعلانات الأرسا في الولاية — بحث وفرز وتصفية' },
      { h: 'land-agent.html',  i: '🧮', n: 'وكيل تقييم الأراضي',       d: 'حاسبة احتمالية + محفظة قطع' }
    ]},
    { g: 'ملف الاستثمار المشترك', items: [
      { h: 'invest.html',         i: '🏛️', n: 'الملف — نظرة عامة',        d: 'الملخّص التنفيذي · خريطة القسم · الخلية الاستشارية' },
      { h: 'invest-legal.html',   i: '⚖️', n: 'الأساس القانوني',           d: '٢٥ سؤالاً · الوقائع المتحقَّقة · مقارنة ست صيغ' },
      { h: 'invest-risk.html',    i: '🛡️', n: 'المخاطر والبيانات المطلوبة', d: '٢٨ خطراً بإجراءات تخفيف · ما ينقص لاتخاذ القرار' },
      { h: 'invest-paths.html',   i: '🧭', n: 'المسارات المرشّحة',          d: '٢٢ مساراً بدرجة أولوية فحص — بلا اعتماد' },
      { h: 'invest-plan.html',    i: '🧱', n: 'المسار التنفيذي والمهل',     d: 'بوّابات الفحص · الخطوات · عدّاد ٣١/١٢/٢٠٢٦' },
      { h: 'invest-nace.html',    i: '🔬', n: 'مطابقة الأنشطة مع EK-3',     d: 'المسارات الأربعة الأعلى · كود NACE · ما يوقف كلاً منها' },
      { h: 'invest-sectors.html', i: '🧪', n: 'قطاعات أخرى فُحصت',          d: 'شمسية · مواشٍ · دواجن · أثاث · تدوير · ألبان' },
      { h: 'invest-model.html',   i: '🧮', n: 'إطار النموذج المالي',        d: 'ثلاثة سيناريوهات · المدخلات · البوّابة قبل أي رقم' },
      { h: 'invest-docs.html',    i: '📑', n: 'العقود واختيار المستشارين',  d: 'بنود للمحامي · معايير وأسئلة لكل مستشار' },
      { h: 'invest-dd.html',      i: '🔍', n: 'العناية الواجبة والأسئلة',   d: 'قائمة تحقّق عند وجود صفقة · ١١ سؤالاً شائعاً' },
      { h: 'invest-log.html',     i: '📚', n: 'السجلّات',                   d: 'الأسعار والتكاليف · القرارات · التحديثات القانونية' },
      { h: 'invest-ops.html',     i: '📡', n: 'المتابعة والأتمتة',          d: 'دورات الرصد والبنية التقنية وصيغة التقرير' },
      { h: 'invest-sources.html', i: '📚', n: 'أرشيف المصادر',              d: '٩٤ مصدراً بروابطها وتواريخها' }
    ]},
    { g: 'الأرشيف والمراجع', items: [
      { h: 'reports.html',     i: '🗂️', n: 'أرشيف التقارير اليومية',  d: 'كل تقارير الوكيلين منذ الانطلاق' },
      { h: 'library.html',     i: '📚', n: 'مكتبة المشاريع الثمانية',  d: 'دراسات الجدوى والنماذج المالية' }
    ]},
    { g: 'التشغيل والإدارة', items: [
      { h: 'admin.html',   i: '🛠️', n: 'لوحة الإدارة',    d: 'أضف · عدّل · احذف · انشر — من دون وسيط' },
      { h: 'manual.html',  i: '📘', n: 'دليل التشغيل',     d: 'كيف تدير المنظومة وتصلحها وتوسّعها بنفسك' },
      { h: 'install.html', i: '⬇️', n: 'التثبيت والإعداد', d: 'ثبّتها كتطبيق وافتح صلاحية التعديل' }
    ]}
  ];

  var CSS = [
    '#mly-fab{position:fixed;inset-inline-start:18px;bottom:18px;z-index:9998;width:56px;height:56px;border-radius:18px;',
      'border:1px solid rgba(247,165,43,.45);background:linear-gradient(135deg,#f7a52b,#ff8a3d);color:#241200;',
      'font-size:25px;cursor:pointer;box-shadow:0 10px 26px rgba(0,0,0,.45);display:grid;place-items:center;',
      "font-family:'Cairo',system-ui,sans-serif;transition:transform .16s ease}",
    '#mly-fab:hover{transform:translateY(-3px) scale(1.04)}',
    '#mly-fab span{pointer-events:none}',
    '#mly-scrim{position:fixed;inset:0;z-index:9998;background:rgba(4,7,18,.66);backdrop-filter:blur(3px);',
      'opacity:0;pointer-events:none;transition:opacity .2s ease}',
    '#mly-scrim.on{opacity:1;pointer-events:auto}',
    '#mly-drawer{position:fixed;z-index:9999;inset-block:0;inset-inline-start:0;width:min(340px,88vw);',
      'background:linear-gradient(180deg,#121a3a,#0b1020);border-inline-end:1px solid #28345f;',
      'box-shadow:0 0 44px rgba(0,0,0,.6);transform:translateX(105%);transition:transform .24s cubic-bezier(.3,.8,.3,1);',
      "overflow-y:auto;font-family:'Cairo',system-ui,sans-serif;direction:rtl;text-align:right;color:#eef3ff}",
    /* اللوحة تُثبَّت دائماً على يمين الشاشة (dir=rtl داخلها) — إخفاؤها بالإزاحة يميناً */
    '#mly-drawer.on{transform:translateX(0)}',
    '#mly-drawer .hd{display:flex;align-items:center;gap:11px;padding:18px 18px 14px;border-bottom:1px solid #222c56}',
    '#mly-drawer .hd .lg{width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,#f7a52b,#ff8a3d);',
      'display:grid;place-items:center;font-size:21px;flex:0 0 auto}',
    '#mly-drawer .hd b{font-size:16px;font-weight:800;display:block;line-height:1.3}',
    '#mly-drawer .hd small{font-size:11.5px;color:#8b98bf;font-weight:600}',
    '#mly-drawer .x{margin-inline-start:auto;background:#151e44;border:1px solid #28345f;color:#c2cdec;',
      'width:34px;height:34px;border-radius:10px;font-size:17px;cursor:pointer;flex:0 0 auto}',
    '#mly-drawer .grp{font-size:10.5px;letter-spacing:1.1px;color:#8b98bf;font-weight:800;padding:16px 18px 7px;text-transform:uppercase}',
    '#mly-drawer a.it{display:flex;gap:11px;align-items:flex-start;padding:10px 18px;color:#c2cdec;text-decoration:none;transition:.14s}',
    '#mly-drawer a.it:hover{background:#151e44;color:#fff}',
    '#mly-drawer a.it.cur{background:rgba(247,165,43,.14);color:#ffe6c2}',
    '#mly-drawer a.it .ic{width:32px;height:32px;flex:0 0 auto;border-radius:10px;background:#151e44;border:1px solid #222c56;',
      'display:grid;place-items:center;font-size:15px}',
    '#mly-drawer a.it.cur .ic{background:linear-gradient(135deg,#f7a52b,#ff8a3d);border-color:transparent;color:#241200}',
    '#mly-drawer a.it b{font-size:14px;font-weight:700;display:block;line-height:1.4}',
    '#mly-drawer a.it small{font-size:11.5px;color:#8b98bf;display:block;line-height:1.5;margin-top:1px}',
    '#mly-drawer .ft{padding:18px;margin-top:10px;border-top:1px solid #222c56;font-size:11.5px;color:#8b98bf;line-height:1.8}',
    '@media print{#mly-fab,#mly-scrim,#mly-drawer{display:none!important}}',

    /* ── أدوات عائمة إضافية: الصفحة الرئيسية · تمرير لأعلى/لأسفل · بحث ذكي (٢٦/٠٩) ── */
    '#mly-tools{position:fixed;inset-inline-end:18px;bottom:18px;z-index:9998;display:flex;flex-direction:column;gap:10px}',
    '#mly-tools button{width:46px;height:46px;border-radius:14px;border:1px solid #28345f;',
      'background:linear-gradient(180deg,#151e44,#0d1430);color:#c2cdec;font-size:19px;cursor:pointer;',
      'box-shadow:0 6px 18px rgba(0,0,0,.35);display:grid;place-items:center;',
      "font-family:'Cairo',system-ui,sans-serif;transition:transform .15s ease,color .15s ease,border-color .15s ease}",
    '#mly-tools button:hover{transform:translateY(-2px);color:#fff;border-color:#f7a52b}',
    '@media print{#mly-tools,#mly-search-scrim{display:none!important}}',

    '#mly-search-scrim{position:fixed;inset:0;z-index:10000;background:rgba(4,7,18,.72);backdrop-filter:blur(3px);',
      'opacity:0;pointer-events:none;transition:opacity .18s ease;display:flex;align-items:flex-start;',
      'justify-content:center;padding-top:12vh}',
    '#mly-search-scrim.on{opacity:1;pointer-events:auto}',
    '#mly-search-box{width:min(560px,92vw);background:linear-gradient(180deg,#121a3a,#0b1020);border:1px solid #28345f;',
      'border-radius:18px;box-shadow:0 20px 60px rgba(0,0,0,.55);overflow:hidden;transform:translateY(-10px);',
      "transition:transform .18s ease;font-family:'Cairo',system-ui,sans-serif;direction:rtl;text-align:right;color:#eef3ff}",
    '#mly-search-scrim.on #mly-search-box{transform:translateY(0)}',
    '#mly-search-box .row{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid #222c56}',
    '#mly-search-box .row span.ic{font-size:19px;flex:0 0 auto}',
    '#mly-search-box input{flex:1;background:transparent;border:none;outline:none;color:#eef3ff;font-size:16px;font-family:inherit}',
    '#mly-search-box input::placeholder{color:#8b98bf}',
    '#mly-search-box .x{background:#151e44;border:1px solid #28345f;color:#c2cdec;width:30px;height:30px;border-radius:9px;',
      'font-size:15px;cursor:pointer;flex:0 0 auto}',
    '#mly-search-results{max-height:52vh;overflow-y:auto}',
    '#mly-search-results a{display:flex;gap:11px;align-items:flex-start;padding:11px 16px;color:#c2cdec;',
      'text-decoration:none;transition:.12s}',
    '#mly-search-results a:hover,#mly-search-results a.sel{background:#151e44;color:#fff}',
    '#mly-search-results a .ic{width:32px;height:32px;flex:0 0 auto;border-radius:10px;background:#151e44;',
      'border:1px solid #222c56;display:grid;place-items:center;font-size:15px}',
    '#mly-search-results a b{font-size:14px;font-weight:700;display:block;line-height:1.4}',
    '#mly-search-results a small{font-size:11.5px;color:#8b98bf;display:block;line-height:1.5;margin-top:1px}',
    '#mly-search-results .grp{font-size:10px;letter-spacing:1px;color:#8b98bf;font-weight:800;padding:12px 16px 4px;',
      'text-transform:uppercase}',
    '#mly-search-empty{padding:22px 16px;text-align:center;color:#8b98bf;font-size:13.5px}'
  ].join('');

  function build() {
    var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);

    var here = (location.pathname.split('/').pop() || 'index.html').toLowerCase();

    var fab = document.createElement('button');
    fab.id = 'mly-fab'; fab.type = 'button';
    fab.setAttribute('aria-label', 'قائمة منظومة ملاطيا');
    fab.innerHTML = '<span>🧭</span>';

    var scrim = document.createElement('div'); scrim.id = 'mly-scrim';

    var dr = document.createElement('aside');
    dr.id = 'mly-drawer'; dr.setAttribute('dir', 'rtl');

    var html = '<div class="hd"><div class="lg">🌰</div><div><b>منظومة ملاطيا</b>' +
               '<small>كل الملفات والأنظمة في مكان واحد</small></div>' +
               '<button class="x" type="button" aria-label="إغلاق">✕</button></div>';

    SECTIONS.forEach(function (sec) {
      html += '<div class="grp">' + sec.g + '</div>';
      sec.items.forEach(function (it) {
        var cur = (it.h.toLowerCase() === here) ? ' cur' : '';
        html += '<a class="it' + cur + '" href="' + BASE + it.h + '">' +
                  '<span class="ic">' + it.i + '</span>' +
                  '<span><b>' + it.n + '</b><small>' + it.d + '</small></span>' +
                '</a>';
      });
    });

    html += '<div class="ft">📁 <b style="color:#c2cdec">مكتبة المستندات</b> — دراسات الجدوى' +
            ' والنماذج المالية، تُفتح وتُنزَّل مباشرةً.<br>' +
            '<span style="opacity:.75">jmahery.com/malatya/</span></div>';

    dr.innerHTML = html;

    document.body.appendChild(scrim);
    document.body.appendChild(dr);
    document.body.appendChild(fab);

    function open()  { scrim.classList.add('on');  dr.classList.add('on');  }
    function close() { scrim.classList.remove('on'); dr.classList.remove('on'); }

    fab.addEventListener('click', open);
    scrim.addEventListener('click', close);
    dr.querySelector('.x').addEventListener('click', close);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });

    buildToolsAndSearch(here);
  }

  /* ═══ الصفحة الرئيسية · تمرير لأعلى/لأسفل · بحث ذكي لكل المنظومة (٢٦/٠٩) ═══
   * زرّ الرئيسية والسهمان أدوات تنقّل بسيطة على كل صفحة. البحث يطابق اسم كل
   * صفحة ووصفها ومجموعتها من SECTIONS نفسها (٢٥ صفحة) — لا فهرسة لمحتوى كل
   * صفحة، فقط دليل المنظومة نفسه — بمطابقة عربية متسامحة (تسقط التشكيل
   * وتوحّد أ/إ/آ وة/ه وى/ي) بحيث "الدليل" أو "aldليل" أو "aroud" كلّها تصل. */
  function normAr(s) {
    return (s || '').toString().toLowerCase()
      .replace(/[ً-ٰٟ]/g, '')
      .replace(/[إأآا]/g, 'ا')
      .replace(/ى/g, 'ي')
      .replace(/ة/g, 'ه')
      .replace(/ؤ/g, 'و')
      .replace(/ئ/g, 'ي')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function buildToolsAndSearch(here) {
    var ALL = [];
    SECTIONS.forEach(function (sec) {
      sec.items.forEach(function (it) { ALL.push({ g: sec.g, h: it.h, i: it.i, n: it.n, d: it.d }); });
    });

    /* ── شريط الأدوات العائم ── */
    var tools = document.createElement('div');
    tools.id = 'mly-tools';

    var bSearch = document.createElement('button');
    bSearch.type = 'button'; bSearch.setAttribute('aria-label', 'بحث ذكي في كل المنظومة');
    bSearch.innerHTML = '<span>🔍</span>';

    var bHome = document.createElement('button');
    bHome.type = 'button'; bHome.setAttribute('aria-label', 'الصفحة الرئيسية');
    bHome.innerHTML = '<span>🏠</span>';
    bHome.addEventListener('click', function () { location.href = BASE + 'index.html'; });

    var bUp = document.createElement('button');
    bUp.type = 'button'; bUp.setAttribute('aria-label', 'التمرير لأعلى الصفحة');
    bUp.innerHTML = '<span>▲</span>';
    bUp.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });

    var bDown = document.createElement('button');
    bDown.type = 'button'; bDown.setAttribute('aria-label', 'التمرير لأسفل الصفحة');
    bDown.innerHTML = '<span>▼</span>';
    bDown.addEventListener('click', function () {
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' });
    });

    tools.appendChild(bSearch);
    tools.appendChild(bHome);
    tools.appendChild(bUp);
    tools.appendChild(bDown);
    document.body.appendChild(tools);

    /* ── مربّع البحث الذكي ── */
    var sScrim = document.createElement('div'); sScrim.id = 'mly-search-scrim';
    var sBox = document.createElement('div'); sBox.id = 'mly-search-box'; sBox.setAttribute('dir', 'rtl');
    sBox.innerHTML =
      '<div class="row"><span class="ic">🔍</span>' +
      '<input type="text" id="mly-search-input" placeholder="ابحث في كل صفحات المنظومة… (الدليل، العروض، الأراضي، العقارات…)" autocomplete="off">' +
      '<button class="x" type="button" aria-label="إغلاق">✕</button></div>' +
      '<div id="mly-search-results"></div>';
    sScrim.appendChild(sBox);
    document.body.appendChild(sScrim);

    var input = sBox.querySelector('#mly-search-input');
    var resultsEl = sBox.querySelector('#mly-search-results');

    function render(list) {
      if (!list.length) {
        resultsEl.innerHTML = '<div id="mly-search-empty">لا نتائج مطابقة — جرّب كلمة أخرى</div>';
        return;
      }
      var html = '';
      var lastGrp = null;
      list.forEach(function (it) {
        if (it.g !== lastGrp) { html += '<div class="grp">' + it.g + '</div>'; lastGrp = it.g; }
        var cur = (it.h.toLowerCase() === here) ? ' cur' : '';
        html += '<a class="' + cur + '" href="' + BASE + it.h + '">' +
                  '<span class="ic">' + it.i + '</span>' +
                  '<span><b>' + it.n + '</b><small>' + it.d + '</small></span>' +
                '</a>';
      });
      resultsEl.innerHTML = html;
    }

    function search(q) {
      var nq = normAr(q);
      if (!nq) { render(ALL); return; }
      var scored = [];
      ALL.forEach(function (it) {
        var nn = normAr(it.n), nd = normAr(it.d), ng = normAr(it.g), nh = it.h.toLowerCase();
        var score = 0;
        if (nn.indexOf(nq) === 0) score = 4;
        else if (nn.indexOf(nq) !== -1) score = 3;
        else if (nh.indexOf(nq.replace(/\s+/g, '')) !== -1) score = 2;
        else if (nd.indexOf(nq) !== -1 || ng.indexOf(nq) !== -1) score = 1;
        if (score > 0) scored.push({ it: it, score: score });
      });
      scored.sort(function (a, b) { return b.score - a.score; });
      render(scored.map(function (s) { return s.it; }).slice(0, 18));
    }

    function openSearch() {
      render(ALL);
      sScrim.classList.add('on');
      setTimeout(function () { input.focus(); }, 30);
    }
    function closeSearch() { sScrim.classList.remove('on'); input.value = ''; }

    bSearch.addEventListener('click', openSearch);
    sScrim.addEventListener('click', function (e) { if (e.target === sScrim) closeSearch(); });
    sBox.querySelector('.x').addEventListener('click', closeSearch);
    input.addEventListener('input', function () { search(input.value); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { closeSearch(); return; }
      if (e.key === 'Enter') {
        var first = resultsEl.querySelector('a');
        if (first) location.href = first.getAttribute('href');
      }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && sScrim.classList.contains('on')) closeSearch();
      /* اختصار: Ctrl/Cmd+K يفتح البحث من أي مكان في المنظومة */
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); openSearch(); }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build);
  else build();
})();


/* ═══════════ MLY-PWA-START — تشغيل المنظومة كتطبيق ═══════════
 * أُضيف في ٢٨/٠٨/٢٠٢٦. يعيش هنا لأن nav.js يُحمَّل في كل صفحة، فلا حاجة
 * لتعديل عشرين صفحة كلّما تغيّر شيء في سلوك التطبيق.
 *
 * ثلاث وظائف: تسجيل عامل الخدمة · زرّ التثبيت داخل قائمة التنقّل ·
 * إشعار «تحديث جاهز» حين ينزل إصدار جديد — لأن المستخدم الذي لا يعلم أنه
 * يرى نسخة قديمة أسوأ حالاً ممّن يعلم.
 */
(function () {
  'use strict';

  var BASE = (function () {
    var s = document.currentScript;
    if (!s) {
      var a = document.getElementsByTagName('script');
      for (var i = a.length - 1; i >= 0; i--) if (/nav\.js/.test(a[i].src)) { s = a[i]; break; }
    }
    return s ? s.src.replace(/assets\/nav\.js.*$/, '') : '';
  })();

  /* ── عامل الخدمة ── */
  if ('serviceWorker' in navigator && window.isSecureContext) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register(BASE + 'sw.js', { scope: BASE || './' })
        .then(function (reg) {
          reg.addEventListener('updatefound', function () {
            var nw = reg.installing;
            if (!nw) return;
            nw.addEventListener('statechange', function () {
              // controller موجود ⇒ هذه ترقية لا تثبيت أوّل
              if (nw.state === 'installed' && navigator.serviceWorker.controller) showUpdate(reg);
            });
          });
        })
        .catch(function () { /* التثبيت ليس شرطاً لعمل الموقع */ });

      var refreshing = false;
      navigator.serviceWorker.addEventListener('controllerchange', function () {
        if (refreshing) return;
        refreshing = true;
        location.reload();
      });
    });
  }

  function showUpdate(reg) {
    if (document.getElementById('mly-upd')) return;
    var bar = document.createElement('div');
    bar.id = 'mly-upd';
    bar.className = 'on';
    bar.innerHTML = '<span>وصل تحديث للمنظومة</span>';
    var b = document.createElement('button');
    b.className = 'btn sm primary';
    b.textContent = 'حدّث الآن';
    b.onclick = function () {
      b.disabled = true; b.textContent = 'جارٍ…';
      if (reg.waiting) reg.waiting.postMessage('skip-waiting'); else location.reload();
    };
    var x = document.createElement('button');
    x.className = 'btn sm';
    x.textContent = 'لاحقاً';
    x.onclick = function () { bar.remove(); };
    bar.appendChild(b); bar.appendChild(x);
    document.body.appendChild(bar);
  }

  /* ── زرّ التثبيت ── */
  var deferred = null;
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferred = e;
    addInstallEntry();
  });
  window.addEventListener('appinstalled', function () {
    deferred = null;
    var el = document.getElementById('mly-install-entry');
    if (el) el.remove();
  });

  /* قائمة nav.js عبارة عن #mly-drawer فيه .hd ثمّ مجموعات .grp/.it ثمّ .ft */
  function addInstallEntry() {
    var tries = 0;
    var t = setInterval(function () {
      if (document.getElementById('mly-install-entry')) { clearInterval(t); return; }
      var drawer = document.getElementById('mly-drawer');
      if (drawer) {
        clearInterval(t);
        var wrap = document.createElement('div');
        wrap.id = 'mly-install-entry';
        wrap.style.cssText = 'padding:12px 16px;border-top:1px solid var(--border)';
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'btn primary';
        b.style.width = '100%';
        b.textContent = '⬇️ ثبّت المنظومة كتطبيق';
        b.onclick = async function () {
          if (!deferred) { location.href = 'install.html'; return; }
          deferred.prompt();
          await deferred.userChoice;
          deferred = null;
          wrap.remove();
        };
        wrap.appendChild(b);
        var ft = drawer.querySelector('.ft');
        if (ft) drawer.insertBefore(wrap, ft); else drawer.appendChild(wrap);
      }
      if (++tries > 40) clearInterval(t);
    }, 300);
  }
})();
/* ═══════════ MLY-PWA-END ═══════════ */
