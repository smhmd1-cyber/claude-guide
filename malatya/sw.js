/* منظومة ملاطيا — عامل الخدمة (Service Worker)
 *
 * الغرض: أن تفتح المنظومة على الهاتف كتطبيق، وأن تعمل صفحاتها حين تنقطع الشبكة.
 *
 * القاعدة التي تحكم كل شيء هنا: البيانات الطازجة أوّلاً، والمخزَّن شبكةُ أمان لا بديلاً.
 * لذلك لا نستعمل «cache-first» لأي صفحة أو ملفّ بيانات — لو فعلنا لرأيت أسعار
 * الأمس وأنت تظنّها اليوم، وهذا أسوأ من ألّا ترى شيئاً.
 *
 * لتحديث نسخة المخزَّن: ارفع رقم CACHE_V. القديم يُحذف تلقائياً عند التفعيل.
 */

const CACHE_V = 'malatya-v2';
const CORE = 'core-' + CACHE_V;
const RUNTIME = 'run-' + CACHE_V;

/* هيكل التطبيق: ما يلزم لفتح المنظومة بلا شبكة. لا نضع هنا ملفّات البيانات.
 *
 * ⚠️ ولا نضع هنا **ملفّات الأصول** (css/js) — قرار 02/10/2026:
 * أسماء الأصول صارت مبنيّة على بصمة محتواها (`nav.<md5>.js`)، فذِكرُها هنا
 * يجعل هذا الملفّ يتغيّر مع كل تغيير فيها. وهذا الملفّ بالذات **لا يمكن
 * إعادة تسميته** (مسار عامل الخدمة ثابت بحكم تسجيله)، وأمام الموقع طبقةُ
 * تخزينٍ مؤقّت تُخزّن js حسب المسار — فيبقى القديم يُقدَّم للزوّار ويعود
 * يُخزّن أصولاً لم تعد موجودة. والأصول تُخزَّن أصلاً وقت الطلب عبر
 * staleWhileRevalidate أدناه، فلا خسارة في إخراجها من هنا.
 */
const CORE_ASSETS = [
  './',
  './index.html',
  './arsa.html',
  './land-board.html',
  './aqar.html',
  './aqar-board.html',
  './reports.html',
  './library.html',
  './admin.html',
  './install.html',
  './manual.html',
  './offline.html',
  './assets/icons/icon-192.png',
  './assets/icons/icon-512.png',
  './manifest.webmanifest'
];

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(CORE);
    // addAll تفشل كلّها لو فشل ملفّ واحد، فنضيف كلّاً على حدة ونتسامح مع الغائب
    await Promise.all(CORE_ASSETS.map((u) => c.add(u).catch(() => null)));
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CORE && k !== RUNTIME).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('message', (e) => {
  if (e.data === 'skip-waiting') self.skipWaiting();
  if (e.data === 'clear-cache') {
    caches.keys().then((ks) => Promise.all(ks.map((k) => caches.delete(k))));
  }
});

function isData(url) { return /\/data\/.*\.json(\?|$)/.test(url.pathname + url.search); }
function isAsset(url) { return /\.(css|js|png|jpg|jpeg|svg|webp|woff2?)(\?|$)/.test(url.pathname + url.search); }

/** الشبكة أوّلاً بمهلة: إن تأخّرت الشبكة نعرض المخزَّن بدل انتظار لا ينتهي. */
async function networkFirst(req, cacheName, timeoutMs) {
  const cache = await caches.open(cacheName);
  try {
    const net = await (timeoutMs
      ? Promise.race([
          fetch(req),
          new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), timeoutMs))
        ])
      : fetch(req));
    if (net && net.ok) cache.put(req, net.clone());
    return net;
  } catch (err) {
    const hit = await cache.match(req, { ignoreSearch: true });
    if (hit) return hit;
    throw err;
  }
}

/** المخزَّن فوراً مع تحديثه في الخلفية — للأصول الثابتة وحدها. */
async function staleWhileRevalidate(req, cacheName) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(req, { ignoreSearch: true });
  const net = fetch(req).then((r) => { if (r && r.ok) cache.put(req, r.clone()); return r; }).catch(() => null);
  return hit || net || fetch(req);
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // لا نلمس شيئاً خارج نطاقنا: GitHub API وصور الإعلانات وغيرها تمرّ كما هي.
  if (url.origin !== self.location.origin) return;
  // مجلّد المستندات محميّ بـ.htaccess — تخزينه يفسد سلوك الحماية
  if (url.pathname.includes('/docs/')) return;

  if (req.mode === 'navigate') {
    e.respondWith((async () => {
      try {
        return await networkFirst(req, RUNTIME, 6000);
      } catch (err) {
        const cache = await caches.open(CORE);
        return (await cache.match('./offline.html')) ||
               new Response('غير متّصل', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
      }
    })());
    return;
  }

  if (isData(url)) {
    e.respondWith(networkFirst(req, RUNTIME, 8000).catch(
      () => new Response(JSON.stringify({ offline: true }), {
        status: 503, headers: { 'Content-Type': 'application/json; charset=utf-8' }
      })
    ));
    return;
  }

  if (isAsset(url)) {
    e.respondWith(staleWhileRevalidate(req, CORE));
  }
});
