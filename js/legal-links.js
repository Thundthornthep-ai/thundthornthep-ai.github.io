/**
 * LAS Legal Links — Auto-link legal tags to relevant articles
 * Converts plain-text legal references into clickable links
 *
 * Scans: .legal-tags span, .card-tags span, .series-ref, .law-tag
 * Maps: มาตรา → LAS article that analyzes it | Contract type → LAS article
 */
(function () {
  'use strict';

  // --- Mapping: text pattern → { url, title } ---
  // Priority: LAS articles first (best context), OCS fallback for unmapped
  // PDF base path
  var PDF = '/laws/';

  var defined = [
    // ปพพ. มาตรา — link to LAS articles + PDF of Civil & Commercial Code
    { pattern: /มาตรา\s*354|ม\.?\s*354/,   url: '/articles/las-cc-01.html',   title: 'LAS C&C 01 — โครงสร้างสัญญาไทย (ม.354)', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /มาตรา\s*537|ม\.?\s*537/,   url: '/articles/lease-agreement-thailand-guide.html', title: 'สัญญาเช่าในกฎหมายไทย (ม.537)', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /มาตรา\s*538|ม\.?\s*538/,   url: '/articles/lease-agreement-thailand-guide.html', title: 'สัญญาเช่า — เกิน 3 ปีต้องจดทะเบียน (ม.538)', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /มาตรา\s*575|ม\.?\s*575/,   url: '/articles/las-share-01.html', title: 'LAS Share 01 — จ้างทำของ vs จ้างแรงงาน (ม.575)', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /มาตรา\s*587|ม\.?\s*587/,   url: '/articles/las-share-01.html', title: 'LAS Share 01 — จ้างทำของ vs จ้างแรงงาน (ม.587)', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /มาตรา\s*680|ม\.?\s*680/,   url: '/articles/las-share-05.html', title: 'LAS Share 05 — สัญญาค้ำประกัน (ม.680)', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /มาตรา\s*797|ม\.?\s*797/,   url: '/articles/las-share-08.html', title: 'LAS Share 08 — หนังสือมอบอำนาจ (ม.797)', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /มาตรา\s*1012|ม\.?\s*1012/, url: '/articles/las-upsize-01.html', title: 'LAS UP 01 — จดทะเบียนบริษัท (ม.1012)', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /มาตรา\s*1098|ม\.?\s*1098/, url: '/articles/las-share-02.html', title: 'LAS Share 02 — หนังสือบริคณห์สนธิ (ม.1098)', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /มาตรา\s*1129|ม\.?\s*1129/, url: '/articles/las-share-07.html', title: 'LAS Share 07 — การโอนหุ้น (ม.1129)', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /มาตรา\s*1194|ม\.?\s*1194/, url: '/articles/las-share-03.html', title: 'LAS Share 03 — มติที่ประชุม (ม.1194)', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /มาตรา\s*193/,              url: '/articles/las-share-04.html', title: 'LAS Share 04 — อายุความ (ม.193)', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /มาตรา\s*291|ม\.?\s*291/,   url: '/articles/las-share-09.html', title: 'LAS Share 09 — หนี้ร่วม vs หนี้ลำพัง (ม.291)', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /มาตรา\s*295|ม\.?\s*295/,   url: '/articles/las-share-09.html', title: 'LAS Share 09 — หนี้ร่วม vs หนี้ลำพัง (ม.295)', pdf: PDF+'civil-commercial-code-2568.pdf' },

    // พ.ร.บ.คุ้มครองแรงงาน
    { pattern: /มาตรา\s*118|ม\.?\s*118/,   url: '/articles/las-shield-05.html', title: 'LAS Shield 05 — กฎหมายแรงงาน ค่าชดเชย (ม.118)', pdf: PDF+'labour-protection-act-2541-amendment9.pdf' },
    { pattern: /มาตรา\s*41(?:\/1)?/,       url: '/articles/labour-protection-act-amendment-9-2568.html', title: 'LPA ฉบับที่ 9 — ลาคลอด 120 วัน (ม.41)', pdf: PDF+'labour-protection-act-2541-amendment9.pdf' },

    // พ.ร.บ.ความลับทางการค้า
    { pattern: /มาตรา\s*3|ม\.?\s*3(?!\d)/,  url: '/articles/las-shield-02.html', title: 'LAS Shield 02 — NDA ความลับทางการค้า (ม.3)', pdf: PDF+'trade-secrets-act-2545.pdf' },

    // พ.ร.บ.ข้อสัญญาที่ไม่เป็นธรรม
    { pattern: /มาตรา\s*4|ม\.?\s*4(?!\d)/,  url: '/articles/las-share-10.html', title: 'LAS Share 10 — ข้อสัญญาที่ไม่เป็นธรรม (ม.4)', pdf: PDF+'unfair-contract-terms-act-2540.pdf' },

    // Contract types → relevant LAS articles
    { pattern: /^NDA$/i,                    url: '/articles/nda-non-disclosure-agreement-thailand.html', title: 'NDA สัญญารักษาความลับ — คู่มือฉบับสมบูรณ์', pdf: PDF+'trade-secrets-act-2545.pdf' },
    { pattern: /^Non-Compete$/i,            url: '/articles/las-shield-03.html', title: 'LAS Shield 03 — Non-Compete ข้อห้ามแข่งขัน' },
    { pattern: /^SHA$/i,                    url: '/articles/las-upsize-02.html', title: 'LAS UP 02 — Shareholders Agreement' },
    { pattern: /^สัญญาจ้างแรงงาน$/,         url: '/articles/employment-contract-thailand-guide.html', title: 'สัญญาจ้างแรงงาน — คู่มือฉบับสมบูรณ์', pdf: PDF+'labour-protection-act-2541-amendment9.pdf' },
    { pattern: /^สัญญาเช่า$/,               url: '/articles/lease-agreement-thailand-guide.html', title: 'สัญญาเช่า — คู่มือครบจบ', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /^สัญญาบริการ$/,              url: '/articles/las-share-01.html', title: 'LAS Share 01 — จ้างทำของ vs จ้างแรงงาน', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /^สัญญาค้ำประกัน$/,           url: '/articles/las-share-05.html', title: 'LAS Share 05 — สัญญาค้ำประกัน', pdf: PDF+'civil-commercial-code-2568.pdf' },
    { pattern: /^สัญญาความลับ$/,             url: '/articles/nda-non-disclosure-agreement-thailand.html', title: 'NDA สัญญารักษาความลับ', pdf: PDF+'trade-secrets-act-2545.pdf' },
    { pattern: /^สัญญาแฟรนไชส์$/,            url: '/articles/franchise-agreement-thailand.html', title: 'สัญญาแฟรนไชส์ไทย' },
    { pattern: /^Joint Venture$/i,          url: '/articles/joint-venture-agreement-thailand.html', title: 'สัญญา Joint Venture ไทย' },
    { pattern: /^Due Diligence$/i,          url: '/articles/due-diligence-conditions-precedent-thailand.html', title: 'Due Diligence & CP Thailand' },
    { pattern: /^PDPA$/i,                   url: '/articles/pdpa-compliance-guide-thailand.html', title: 'PDPA Compliance Guide Thailand', pdf: PDF+'pdpa-2562.pdf' },
    { pattern: /^Force Majeure$/i,          url: '/articles/las-shield-06.html', title: 'LAS Shield 06 — Force Majeure เหตุสุดวิสัย' },
    { pattern: /^M&A$|^M&amp;A$/i,          url: '/articles/mergers-acquisitions-thailand.html', title: 'M&A กฎหมายไทย' },
    { pattern: /^BOI$/i,                    url: '/articles/boi-investment-thailand-guide.html', title: 'BOI สิทธิประโยชน์การลงทุนไทย', pdf: PDF+'investment-promotion-act-boi.pdf' },
    { pattern: /^Transfer Pricing$/i,       url: '/articles/transfer-pricing-thailand.html', title: 'Transfer Pricing ไทย', pdf: PDF+'revenue-code.pdf' },
    { pattern: /^Indemnification$/i,        url: '/articles/las-cc-07.html', title: 'LAS C&C 07 — Indemnification ชดใช้ค่าเสียหาย' },
    { pattern: /^Termination$/i,            url: '/articles/las-cc-06.html', title: 'LAS C&C 06 — เลิกสัญญา' },

    // Broader law names → PDF direct
    { pattern: /^ปพพ\.|^ประมวลกฎหมายแพ่ง/,  url: PDF+'civil-commercial-code-2568.pdf', title: 'ประมวลกฎหมายแพ่งและพาณิชย์ (ฉบับอัปเดต 2568) — PDF' },
    { pattern: /^พ\.ร\.บ\./,                url: 'https://www.ocs.go.th/searchlaw', title: 'ค้นหากฎหมาย — สำนักงานคณะกรรมการกฤษฎีกา', external: true }
  ];

  // --- Selectors to scan ---
  var SELECTORS = '.legal-tags span, .card-tags span, .series-ref, span.law-tag';

  function linkify() {
    var spans = document.querySelectorAll(SELECTORS);
    spans.forEach(function (span) {
      // Skip if already contains a link
      if (span.querySelector('a') || span.closest('a')) return;

      var text = span.textContent.trim();
      if (!text) return;

      for (var i = 0; i < defined.length; i++) {
        var rule = defined[i];
        if (rule.pattern.test(text)) {
          // Don't link to self (current page)
          if (window.location.pathname.endsWith(rule.url)) break;

          var a = document.createElement('a');
          a.href = rule.url;
          a.title = rule.title;
          a.textContent = text;
          a.style.cssText = 'color:inherit;text-decoration:underline dotted;text-underline-offset:2px;';
          if (rule.external) {
            a.target = '_blank';
            a.rel = 'noopener';
          }
          span.textContent = '';
          span.appendChild(a);

          // Add PDF icon link if available
          if (rule.pdf) {
            var pdfLink = document.createElement('a');
            pdfLink.href = rule.pdf;
            pdfLink.target = '_blank';
            pdfLink.rel = 'noopener';
            pdfLink.title = 'ดูตัวบทกฎหมาย PDF';
            pdfLink.textContent = '\u00A0\uD83D\uDCC4';
            pdfLink.style.cssText = 'text-decoration:none;font-size:0.85em;opacity:0.7;';
            span.appendChild(pdfLink);
          }
          break; // first match wins
        }
      }
    });
  }

  // Run after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', linkify);
  } else {
    linkify();
  }
})();
