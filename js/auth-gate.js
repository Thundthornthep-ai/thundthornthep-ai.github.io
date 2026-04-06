/**
 * LAS Knowledge Hub — Auth Gate
 * Client-side password protection for knowledge articles
 * Username: LAS / Password: laslegal
 *
 * Usage: Add <script src="/js/auth-gate.js"></script> before </body>
 */
(function () {
  'use strict';

  // --- Config ---
  var VALID_USER = 'LAS';
  var VALID_PASS = 'laslegal';
  var SESSION_KEY = 'las_auth_ok';
  var REMEMBER_KEY = 'las_auth_remember';

  // Already authenticated (localStorage = remember me, sessionStorage = this session)
  if (localStorage.getItem(SESSION_KEY) === '1' || sessionStorage.getItem(SESSION_KEY) === '1') return;

  // --- Hide page content ---
  document.documentElement.style.overflow = 'hidden';
  var mainEl = document.querySelector('main');
  if (mainEl) mainEl.style.display = 'none';

  // --- Build overlay ---
  var overlay = document.createElement('div');
  overlay.id = 'las-auth-overlay';
  overlay.innerHTML = [
    '<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;',
    'background:linear-gradient(135deg,#0a1628 0%,#162a3e 50%,#0d1b2a 100%);',
    'position:fixed;top:0;left:0;width:100%;height:100%;z-index:99999;font-family:sans-serif;">',
    '<div style="background:#0f1f30;border:1px solid #1e3a5f;border-radius:16px;padding:40px 36px;',
    'max-width:380px;width:90%;box-shadow:0 20px 60px rgba(0,0,0,0.5);text-align:center;">',

    // Logo area
    '<div style="margin-bottom:24px;">',
    '<img src="/las-logo.webp" alt="LAS" style="width:64px;height:64px;border-radius:12px;margin-bottom:12px;" onerror="this.style.display=\'none\'">',
    '<div style="color:#C9A96E;font-size:20px;font-weight:700;letter-spacing:1px;">LAS Knowledge Hub</div>',
    '<div style="color:#6a8da8;font-size:12px;margin-top:4px;">Protected Content — Please Log In</div>',
    '</div>',

    // Username
    '<div style="margin-bottom:12px;text-align:left;">',
    '<label style="color:#8ab4d8;font-size:11px;font-weight:600;letter-spacing:0.5px;display:block;margin-bottom:4px;">USERNAME</label>',
    '<input id="las-auth-user" type="text" autocomplete="username" placeholder="Enter username" ',
    'style="width:100%;padding:10px 14px;background:#162a3e;border:1px solid #1e3a5f;border-radius:8px;',
    'color:#e8eef3;font-size:14px;outline:none;box-sizing:border-box;" onfocus="this.style.borderColor=\'#C9A96E\'" onblur="this.style.borderColor=\'#1e3a5f\'">',
    '</div>',

    // Password
    '<div style="margin-bottom:20px;text-align:left;">',
    '<label style="color:#8ab4d8;font-size:11px;font-weight:600;letter-spacing:0.5px;display:block;margin-bottom:4px;">PASSWORD</label>',
    '<input id="las-auth-pass" type="password" autocomplete="current-password" placeholder="Enter password" ',
    'style="width:100%;padding:10px 14px;background:#162a3e;border:1px solid #1e3a5f;border-radius:8px;',
    'color:#e8eef3;font-size:14px;outline:none;box-sizing:border-box;" onfocus="this.style.borderColor=\'#C9A96E\'" onblur="this.style.borderColor=\'#1e3a5f\'">',
    '</div>',

    // Remember me checkbox
    '<div style="margin-bottom:16px;text-align:left;display:flex;align-items:center;gap:8px;">',
    '<input id="las-auth-remember" type="checkbox" style="width:16px;height:16px;accent-color:#C9A96E;cursor:pointer;">',
    '<label for="las-auth-remember" style="color:#8ab4d8;font-size:12px;cursor:pointer;user-select:none;">จดจำการเข้าสู่ระบบ / Remember me</label>',
    '</div>',

    // Error message (hidden)
    '<div id="las-auth-error" style="display:none;color:#e74c3c;font-size:12px;margin-bottom:12px;">',
    'Invalid username or password</div>',

    // Button
    '<button id="las-auth-btn" style="width:100%;padding:12px;background:linear-gradient(135deg,#C9A96E,#b8954f);',
    'border:none;border-radius:8px;color:#0d1b2a;font-size:14px;font-weight:700;cursor:pointer;',
    'letter-spacing:0.5px;transition:all 0.2s;" ',
    'onmouseover="this.style.transform=\'translateY(-1px)\';this.style.boxShadow=\'0 4px 12px rgba(201,169,110,0.3)\'" ',
    'onmouseout="this.style.transform=\'none\';this.style.boxShadow=\'none\'">',
    'Log In</button>',

    // Footer
    '<div style="margin-top:20px;color:#3a5a72;font-size:10px;">',
    '&copy; 2026 Legal Advance Solution Co., Ltd.</div>',

    '</div></div>'
  ].join('');

  document.body.appendChild(overlay);

  // --- Auth logic ---
  function attempt() {
    var u = document.getElementById('las-auth-user').value.trim();
    var p = document.getElementById('las-auth-pass').value;
    var remember = document.getElementById('las-auth-remember').checked;
    if (u === VALID_USER && p === VALID_PASS) {
      if (remember) {
        localStorage.setItem(SESSION_KEY, '1');
      } else {
        sessionStorage.setItem(SESSION_KEY, '1');
      }
      overlay.remove();
      if (mainEl) mainEl.style.display = '';
      document.documentElement.style.overflow = '';
    } else {
      document.getElementById('las-auth-error').style.display = 'block';
      document.getElementById('las-auth-pass').value = '';
      document.getElementById('las-auth-pass').focus();
    }
  }

  document.getElementById('las-auth-btn').addEventListener('click', attempt);

  // Enter key support
  document.getElementById('las-auth-user').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') document.getElementById('las-auth-pass').focus();
  });
  document.getElementById('las-auth-pass').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') attempt();
  });

  // Auto-focus username field
  setTimeout(function () {
    var el = document.getElementById('las-auth-user');
    if (el) el.focus();
  }, 100);

  // --- Anti-copy protection (read-only for viewers) ---
  function enableCopyProtection() {
    // Disable text selection via CSS
    var style = document.createElement('style');
    style.textContent = [
      'main, article, .content, .article-body, section {',
      '  -webkit-user-select: none;',
      '  -moz-user-select: none;',
      '  -ms-user-select: none;',
      '  user-select: none;',
      '}',
      // Allow selection in code blocks for usability
      'pre, code, input, textarea { user-select: text !important; }'
    ].join('\n');
    document.head.appendChild(style);

    // Disable right-click on content
    document.addEventListener('contextmenu', function (e) {
      if (e.target.closest('input, textarea, pre, code')) return;
      e.preventDefault();
    });

    // Disable common copy shortcuts (Ctrl+C, Ctrl+U, Ctrl+S, Ctrl+P)
    document.addEventListener('keydown', function (e) {
      if (e.target.closest('input, textarea')) return;
      if ((e.ctrlKey || e.metaKey) && ['c','u','s','p','a'].indexOf(e.key.toLowerCase()) !== -1) {
        e.preventDefault();
      }
    });

    // Disable drag
    document.addEventListener('dragstart', function (e) {
      e.preventDefault();
    });
  }

  // Apply copy protection after auth succeeds (or if already authed)
  if (localStorage.getItem(SESSION_KEY) === '1' || sessionStorage.getItem(SESSION_KEY) === '1') {
    enableCopyProtection();
  } else {
    // Patch the attempt function to also enable protection after login
    var origAttempt = attempt;
    attempt = function () {
      origAttempt();
      if (localStorage.getItem(SESSION_KEY) === '1' || sessionStorage.getItem(SESSION_KEY) === '1') {
        enableCopyProtection();
      }
    };
    document.getElementById('las-auth-btn').removeEventListener('click', origAttempt);
    document.getElementById('las-auth-btn').addEventListener('click', attempt);
    document.getElementById('las-auth-pass').removeEventListener('keydown', origAttempt);
    document.getElementById('las-auth-pass').addEventListener('keydown', function (e) {
      if (e.key === 'Enter') attempt();
    });
  }
})();
