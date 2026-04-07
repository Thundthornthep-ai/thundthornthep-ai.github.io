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
    { pattern: /มาตรา\s*3(?!\d)|ม\.?\s*3(?!\d)/,  url: '/articles/las-shield-02.html', title: 'LAS Shield 02 — NDA ความลับทางการค้า (ม.3)', pdf: PDF+'trade-secrets-act-2545.pdf' },

    // พ.ร.บ.ข้อสัญญาที่ไม่เป็นธรรม
    { pattern: /มาตรา\s*4(?!\d)|ม\.?\s*4(?!\d)/,  url: '/articles/las-share-10.html', title: 'LAS Share 10 — ข้อสัญญาที่ไม่เป็นธรรม (ม.4)', pdf: PDF+'unfair-contract-terms-act-2540.pdf' },

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
    { pattern: /^พ\.ร\.บ\./,                url: 'https://www.ocs.go.th/searchlaw-law', title: 'ค้นหากฎหมาย — สำนักงานคณะกรรมการกฤษฎีกา', external: true }
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

  // ==========================================================
  // LAW-REF-CARD: Centralized PDF/Link Map (Single Source of Truth)
  // เปลี่ยน URL ที่นี่ที่เดียว → update ทุก law-ref-card ทั้งเว็บ
  // ==========================================================

  var OCS = 'https://www.ocs.go.th/searchlaw-law';

  var LAW_CARD_MAP = {
    // ประมวลกฎหมาย
    'ปพพ.':           { pdf: PDF+'civil-commercial-code-2568.pdf', name: 'ประมวลกฎหมายแพ่งและพาณิชย์' },
    'รัษฎากร':         { pdf: PDF+'revenue-code.pdf', name: 'ประมวลรัษฎากร' },

    // พ.ร.บ. ที่มี PDF
    'FBA':            { pdf: PDF+'foreign-business-act-2542.pdf', name: 'พ.ร.บ.ประกอบธุรกิจของคนต่างด้าว พ.ศ. 2542' },
    'PDPA':           { pdf: PDF+'pdpa-2562.pdf', name: 'พ.ร.บ.คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562' },
    'LPA':            { pdf: PDF+'labour-protection-act-2541-amendment9.pdf', name: 'พ.ร.บ.คุ้มครองแรงงาน (แก้ไขครั้งที่ 9) พ.ศ. 2568' },
    'คอนโด':          { pdf: PDF+'condominium-act-2522.pdf', name: 'พ.ร.บ.อาคารชุด พ.ศ. 2522' },
    'โรงแรม':          { pdf: PDF+'hotel-act-2547.pdf', name: 'พ.ร.บ.โรงแรม พ.ศ. 2547' },
    'แข่งขัน':         { pdf: PDF+'trade-competition-act-2560.pdf', name: 'พ.ร.บ.การแข่งขันทางการค้า พ.ศ. 2560' },
    'คุ้มครองผู้บริโภค':  { pdf: PDF+'consumer-protection-act.pdf', name: 'พ.ร.บ.คุ้มครองผู้บริโภค พ.ศ. 2522' },
    'เครื่องหมายการค้า': { pdf: PDF+'trademark-act.pdf', name: 'พ.ร.บ.เครื่องหมายการค้า พ.ศ. 2534' },
    'ความลับทางการค้า':  { pdf: PDF+'trade-secrets-act-2545.pdf', name: 'พ.ร.บ.ความลับทางการค้า พ.ศ. 2545' },
    'ลิขสิทธิ์':        { pdf: PDF+'copyright-act.pdf', name: 'พ.ร.บ.ลิขสิทธิ์ พ.ศ. 2537' },
    'สิทธิบัตร':        { pdf: PDF+'patent-act.pdf', name: 'พ.ร.บ.สิทธิบัตร พ.ศ. 2522' },
    'หลักทรัพย์':       { pdf: PDF+'securities-act-2535.pdf', name: 'พ.ร.บ.หลักทรัพย์และตลาดหลักทรัพย์ พ.ศ. 2535' },
    'ข้อสัญญาไม่เป็นธรรม': { pdf: PDF+'unfair-contract-terms-act-2540.pdf', name: 'พ.ร.บ.ว่าด้วยข้อสัญญาที่ไม่เป็นธรรม พ.ศ. 2540' },
    'อนุญาโตตุลาการ':    { pdf: PDF+'arbitration-act-2545.pdf', name: 'พ.ร.บ.อนุญาโตตุลาการ พ.ศ. 2545' },
    'คอมพิวเตอร์':      { pdf: PDF+'computer-crime-act-2550.pdf', name: 'พ.ร.บ.ว่าด้วยการกระทำความผิดเกี่ยวกับคอมพิวเตอร์ พ.ศ. 2550' },
    'BOI':            { pdf: PDF+'investment-promotion-act-boi.pdf', name: 'พ.ร.บ.ส่งเสริมการลงทุน พ.ศ. 2520' },

    // พ.ร.บ. ที่ยังไม่มี PDF — OCS search fallback
    'เครื่องสำอาง':     { ocs: 'พระราชบัญญัติเครื่องสำอาง', name: 'พ.ร.บ.เครื่องสำอาง พ.ศ. 2558' },
    'อาหาร':          { ocs: 'พระราชบัญญัติอาหาร', name: 'พ.ร.บ.อาหาร พ.ศ. 2522' },
    'โรงงาน':          { ocs: 'พระราชบัญญัติโรงงาน', name: 'พ.ร.บ.โรงงาน พ.ศ. 2535' },
    'ที่ดิน':           { ocs: 'ประมวลกฎหมายที่ดิน', name: 'ประมวลกฎหมายที่ดิน' },
    'ภาษีที่ดิน':       { ocs: 'พระราชบัญญัติภาษีที่ดินและสิ่งปลูกสร้าง', name: 'พ.ร.บ.ภาษีที่ดินและสิ่งปลูกสร้าง พ.ศ. 2562' },
    'EEC':            { ocs: 'พระราชบัญญัติเขตพัฒนาพิเศษภาคตะวันออก', name: 'พ.ร.บ.เขตพัฒนาพิเศษภาคตะวันออก พ.ศ. 2561' },
    'ธุรกรรมอิเล็กทรอนิกส์': { ocs: 'พระราชบัญญัติว่าด้วยธุรกรรมทางอิเล็กทรอนิกส์', name: 'พ.ร.บ.ธุรกรรมทางอิเล็กทรอนิกส์ พ.ศ. 2544' },

    // Concept cards → internal articles
    'concept:ma':       { article: '/articles/mergers-acquisitions-thailand.html', name: 'Due Diligence & M&A' },
    'concept:corporate': { article: '/articles/company-registration-thailand-guide.html', name: 'Corporate Law' },
    'concept:franchise': { article: '/articles/franchise-agreement-thailand.html', name: 'Franchise & Distribution' },
    'concept:contract':  { article: '/articles/contract-reading-guide.html', name: 'Contract Fundamentals' },
    'concept:labour':    { article: '/articles/employment-contract-thailand-guide.html', name: 'Labour & Employment' },
    'concept:realestate': { article: '/articles/foreigner-buy-condo-thailand.html', name: 'Real Estate & Property' },
    'concept:ip':        { article: '/articles/ip-law-business-marketing.html', name: 'Intellectual Property' },

    // Missing keys found by Audit Agent (2026-04-08)
    'ป.ป.ช.':           { ocs: '\u0E1B\u0E49\u0E2D\u0E07\u0E01\u0E31\u0E19\u0E41\u0E25\u0E30\u0E1B\u0E23\u0E32\u0E1A\u0E1B\u0E23\u0E32\u0E21\u0E17\u0E38\u0E08\u0E23\u0E34\u0E15', name: '\u0E1E.\u0E23.\u0E1A.\u0E1B\u0E49\u0E2D\u0E07\u0E01\u0E31\u0E19\u0E41\u0E25\u0E30\u0E1B\u0E23\u0E32\u0E1A\u0E1B\u0E23\u0E32\u0E21\u0E17\u0E38\u0E08\u0E23\u0E34\u0E15 \u0E1E.\u0E28. 2561' },
    '\u0E08\u0E31\u0E14\u0E0B\u0E37\u0E49\u0E2D\u0E08\u0E31\u0E14\u0E08\u0E49\u0E32\u0E07': { ocs: '\u0E08\u0E31\u0E14\u0E0B\u0E37\u0E49\u0E2D\u0E08\u0E31\u0E14\u0E08\u0E49\u0E32\u0E07', name: '\u0E1E.\u0E23.\u0E1A.\u0E01\u0E32\u0E23\u0E08\u0E31\u0E14\u0E0B\u0E37\u0E49\u0E2D\u0E08\u0E31\u0E14\u0E08\u0E49\u0E32\u0E07\u0E20\u0E32\u0E04\u0E23\u0E31\u0E10 \u0E1E.\u0E28. 2560' },
    '\u0E21\u0E2B\u0E32\u0E0A\u0E19':  { ocs: '\u0E1A\u0E23\u0E34\u0E29\u0E31\u0E17\u0E21\u0E2B\u0E32\u0E0A\u0E19\u0E08\u0E33\u0E01\u0E31\u0E14', name: '\u0E1E.\u0E23.\u0E1A.\u0E1A\u0E23\u0E34\u0E29\u0E31\u0E17\u0E21\u0E2B\u0E32\u0E0A\u0E19\u0E08\u0E33\u0E01\u0E31\u0E14 \u0E1E.\u0E28. 2535' },
    '\u0E23\u0E31\u0E10\u0E18\u0E23\u0E23\u0E21\u0E19\u0E39\u0E0D': { ocs: '\u0E23\u0E31\u0E10\u0E18\u0E23\u0E23\u0E21\u0E19\u0E39\u0E0D', name: '\u0E23\u0E31\u0E10\u0E18\u0E23\u0E23\u0E21\u0E19\u0E39\u0E0D\u0E41\u0E2B\u0E48\u0E07\u0E23\u0E32\u0E0A\u0E2D\u0E32\u0E13\u0E32\u0E08\u0E31\u0E01\u0E23\u0E44\u0E17\u0E22 \u0E1E.\u0E28. 2560' },
    '\u0E25\u0E30\u0E40\u0E21\u0E34\u0E14\u0E40\u0E08\u0E49\u0E32\u0E2B\u0E19\u0E49\u0E32\u0E17\u0E35\u0E48': { ocs: '\u0E04\u0E27\u0E32\u0E21\u0E23\u0E31\u0E1A\u0E1C\u0E34\u0E14\u0E17\u0E32\u0E07\u0E25\u0E30\u0E40\u0E21\u0E34\u0E14', name: '\u0E1E.\u0E23.\u0E1A.\u0E04\u0E27\u0E32\u0E21\u0E23\u0E31\u0E1A\u0E1C\u0E34\u0E14\u0E17\u0E32\u0E07\u0E25\u0E30\u0E40\u0E21\u0E34\u0E14\u0E02\u0E2D\u0E07\u0E40\u0E08\u0E49\u0E32\u0E2B\u0E19\u0E49\u0E32\u0E17\u0E35\u0E48 \u0E1E.\u0E28. 2539' },
    '\u0E2E\u0E31\u0E49\u0E27\u0E1B\u0E23\u0E30\u0E21\u0E39\u0E25': { ocs: '\u0E27\u0E48\u0E32\u0E14\u0E49\u0E27\u0E22\u0E04\u0E27\u0E32\u0E21\u0E1C\u0E34\u0E14\u0E40\u0E01\u0E35\u0E48\u0E22\u0E27\u0E01\u0E31\u0E1A\u0E01\u0E32\u0E23\u0E40\u0E2A\u0E19\u0E2D\u0E23\u0E32\u0E04\u0E32', name: '\u0E1E.\u0E23.\u0E1A.\u0E27\u0E48\u0E32\u0E14\u0E49\u0E27\u0E22\u0E04\u0E27\u0E32\u0E21\u0E1C\u0E34\u0E14\u0E40\u0E01\u0E35\u0E48\u0E22\u0E27\u0E01\u0E31\u0E1A\u0E01\u0E32\u0E23\u0E40\u0E2A\u0E19\u0E2D\u0E23\u0E32\u0E04\u0E32 \u0E1E.\u0E28. 2542' },
    '\u0E40\u0E0A\u0E48\u0E32\u0E2D\u0E2A\u0E31\u0E07\u0E2B\u0E32\u0E2F': { ocs: '\u0E01\u0E32\u0E23\u0E40\u0E0A\u0E48\u0E32\u0E2D\u0E2A\u0E31\u0E07\u0E2B\u0E32\u0E23\u0E34\u0E21\u0E17\u0E23\u0E31\u0E1E\u0E22\u0E4C', name: '\u0E1E.\u0E23.\u0E1A.\u0E01\u0E32\u0E23\u0E40\u0E0A\u0E48\u0E32\u0E2D\u0E2A\u0E31\u0E07\u0E2B\u0E32\u0E23\u0E34\u0E21\u0E17\u0E23\u0E31\u0E1E\u0E22\u0E4C\u0E40\u0E1E\u0E37\u0E48\u0E2D\u0E1E\u0E32\u0E13\u0E34\u0E0A\u0E22\u0E01\u0E23\u0E23\u0E21\u0E41\u0E25\u0E30\u0E2D\u0E38\u0E15\u0E2A\u0E32\u0E2B\u0E01\u0E23\u0E23\u0E21 \u0E1E.\u0E28. 2542' },
    'concept:anticorruption': { article: '/articles/civil-recovery-corruption-thailand.html', name: 'Anti-Corruption & Civil Recovery' },
    'concept:digital':   { article: '/articles/social-media-marketing-law.html', name: 'Digital & Social Media Law' },
    'concept:drafting':  { article: '/articles/art-of-ancient-contract-drafting.html', name: 'Contract Drafting' },
    'concept:lease':     { article: '/articles/lease-agreement-thailand-guide.html', name: 'Lease Agreement' },
    'concept:nominee':   { article: '/articles/anti-nominee-thailand-legal-guide.html', name: 'Anti-Nominee' },
    'concept:review':    { article: '/articles/contract-reading-guide.html', name: 'Contract Review' }
  };

  /**
   * resolveLawRefCards — Auto-resolve law-ref-card links from LAW_CARD_MAP
   * Reads data-law attribute, updates href + law-source text
   */
  function resolveLawRefCards() {
    var cards = document.querySelectorAll('.law-ref-card[data-law]');
    cards.forEach(function (card) {
      var key = card.getAttribute('data-law');
      if (!key) return;

      var entry = LAW_CARD_MAP[key];
      if (!entry) return;

      var sourceEl = card.querySelector('.law-source');

      if (entry.pdf) {
        card.href = entry.pdf;
        if (sourceEl) sourceEl.textContent = '\uD83D\uDD17 \u0E14\u0E32\u0E27\u0E19\u0E4C\u0E42\u0E2B\u0E25\u0E14 PDF ' + entry.name;
      } else if (entry.article) {
        // Skip self-referencing links (current page)
        if (window.location.pathname.endsWith(entry.article)) return;
        card.href = entry.article;
        if (sourceEl) sourceEl.textContent = '\uD83D\uDD17 \u0E2D\u0E48\u0E32\u0E19\u0E1A\u0E17\u0E04\u0E27\u0E32\u0E21 ' + entry.name;
      } else if (entry.ocs) {
        card.href = OCS + '?q=' + encodeURIComponent(entry.ocs);
        if (sourceEl) sourceEl.textContent = '\uD83D\uDD17 \u0E04\u0E49\u0E19\u0E2B\u0E32\u0E15\u0E31\u0E27\u0E1A\u0E17\u0E01\u0E0E\u0E2B\u0E21\u0E32\u0E22 \u2014 \u0E2A\u0E33\u0E19\u0E31\u0E01\u0E07\u0E32\u0E19\u0E04\u0E13\u0E30\u0E01\u0E23\u0E23\u0E21\u0E01\u0E32\u0E23\u0E01\u0E24\u0E29\u0E0E\u0E35\u0E01\u0E32';
      }
    });
  }

  // Run after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { linkify(); resolveLawRefCards(); });
  } else {
    linkify();
    resolveLawRefCards();
  }
})();
