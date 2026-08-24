/* ===========================================================
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
      { h: 'daleel.html',      i: '📖', n: 'الدليل + النشرة اليومية', d: 'المعيشة · السكن · النقل · السياحة — يتحدّث يومياً' }
    ]},
    { g: 'الأدوات الحيّة', items: [
      { h: 'aqar.html',        i: '🔎', n: 'محرّك البحث العقاري',     d: 'شقق ≤3 سنوات فقط — فلترة وفرز وخرائط' },
      { h: 'aqar-board.html',  i: '🏢', n: 'لوحة العقارات',            d: 'مؤشّرات السوق اليومية + أفضل الفرص' },
      { h: 'land-board.html',  i: '🌾', n: 'لوحة الأراضي',             d: 'رصد القطع وفجوة التحويل يومياً' },
      { h: 'land-agent.html',  i: '🧮', n: 'وكيل تقييم الأراضي',       d: 'حاسبة احتمالية + محفظة قطع' }
    ]},
    { g: 'الأرشيف والمراجع', items: [
      { h: 'reports.html',     i: '🗂️', n: 'أرشيف التقارير اليومية',  d: 'كل تقارير الوكيلين منذ الانطلاق' },
      { h: 'library.html',     i: '📚', n: 'مكتبة المشاريع الثمانية',  d: 'دراسات الجدوى والنماذج المالية' }
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
    '@media print{#mly-fab,#mly-scrim,#mly-drawer{display:none!important}}'
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

    html += '<div class="ft">📁 <b style="color:#c2cdec">مكتبة المستندات</b> محميّة بكلمة مرور —' +
            ' دراسات الجدوى والنماذج المالية للفريق فقط.<br>' +
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
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build);
  else build();
})();
