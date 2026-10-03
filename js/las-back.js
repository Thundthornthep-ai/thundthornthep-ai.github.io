/* LAS article back bar — owner instruction, 2 ตุลาคม 2569: every article opened from the Learning Hub needs a
   Back button that returns to the previous page, and to https://laslegal.tech/learning-hub/index.html.
   Injected at runtime so the article's own text is unchanged; added to a page with one <script> line
   (las-billing scripts/legal/add-back-button.py). */
(function () {
  'use strict';
  var HUB = 'https://laslegal.tech/learning-hub/index.html';
  var en = /^en\b/i.test(document.documentElement.lang || '') || location.pathname.indexOf('/en/') === 0;
  var labels = en
    ? { back: '← Back', hub: 'LAS Learning Hub', nav: 'Back to the previous page or the learning hub' }
    : { back: '← กลับหน้าก่อนหน้า', // ← กลับหน้าก่อนหน้า
        hub: 'คลังการเรียนรู้ LAS', // คลังการเรียนรู้ LAS
        nav: 'กลับหน้าก่อนหน้าหรือคลังการเรียนรู้' }; // กลับหน้าก่อนหน้าหรือคลังการเรียนรู้
  function goBack() {
    // Came here from another page in this tab (a referrer and a history entry): go back to it. A tab the library
    // opened (rel=noopener, so the referrer is set, but no history) or a typed address goes to the hub.
    if (document.referrer && window.history.length > 1) { window.history.back(); return; }
    window.location.href = HUB;
  }
  function mount() {
    if (document.querySelector('.las-back-bar')) return;
    var style = document.createElement('style');
    style.textContent =
      '.las-back-bar{position:sticky;top:0;z-index:100000;display:flex;align-items:center;justify-content:space-between;gap:12px;' +
      'padding:8px 16px;background:rgba(255,253,250,.96);border-bottom:1px solid #ded5c7;backdrop-filter:blur(6px);' +
      'font-family:inherit;font-size:14px;line-height:1.4}' +
      '.las-back-bar button,.las-back-bar a{display:inline-flex;align-items:center;gap:6px;min-height:40px;padding:6px 14px;border-radius:999px;' +
      'border:1px solid #c89d52;background:#fff;color:#344967;font:inherit;font-weight:700;text-decoration:none;cursor:pointer}' +
      '.las-back-bar button:hover,.las-back-bar a:hover,.las-back-bar button:focus-visible,.las-back-bar a:focus-visible{background:#344967;color:#fff;outline:none}' +
      '.las-back-bar a{font-weight:600;color:#667085}' +
      '@media print{.las-back-bar{display:none}}';
    var bar = document.createElement('nav');
    bar.className = 'las-back-bar';
    bar.setAttribute('aria-label', labels.nav);
    var button = document.createElement('button');
    button.type = 'button';
    button.textContent = labels.back;
    button.addEventListener('click', goBack);
    var hub = document.createElement('a');
    hub.href = HUB;
    hub.textContent = labels.hub;
    bar.appendChild(button);
    bar.appendChild(hub);
    document.head.appendChild(style);
    document.body.insertBefore(bar, document.body.firstChild);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
