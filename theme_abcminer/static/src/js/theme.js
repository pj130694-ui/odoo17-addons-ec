/* ABCMiner Theme JS — ROI Calculator + Brand Filter + Animations */
(function() {
  'use strict';

  /* ─── POLYFILL: zoomOdoo — evita error "not a function" en lazy bundle ── */
  // El widget ImageViewer de website_sale asume que $.fn.zoomOdoo ya está
  // registrado cuando llama start(), pero el módulo AMD zoomodoo.js no siempre
  // se inicializa antes. Este no-op se sobreescribe cuando zoomodoo.js carga.
  function patchZoomOdoo() {
    if (window.$ && typeof $.fn !== 'undefined' && typeof $.fn.zoomOdoo === 'undefined') {
      $.fn.zoomOdoo = function() { return this; };
    }
  }
  // Intentar inmediatamente y también cuando jQuery esté disponible
  patchZoomOdoo();
  document.addEventListener('DOMContentLoaded', patchZoomOdoo);
  /* ─────────────────────────────────────────────────────────────────────── */

  /* ─── ROI CALCULATOR — Equipment database ────────────────────── */
  // Prices are approximate and change frequently — consult /shop for current pricing
  const EQUIPMENT = {
    a1246:     { name: 'Avalon A1246',         th: 90,   watts: 3420, price: 700   },
    s19jpro:   { name: 'Antminer S19J Pro',    th: 104,  watts: 3068, price: 800   },
    s19jprop:  { name: 'Antminer S19J Pro+',   th: 122,  watts: 3355, price: 1100  },
    m30spp:    { name: 'Whatsminer M30S++',    th: 112,  watts: 3472, price: 1100  },
    s19kpro:   { name: 'Antminer S19K Pro',    th: 120,  watts: 2760, price: 1200  },
    a1366:     { name: 'Avalon A1366',         th: 130,  watts: 3250, price: 1300  },
    s19xp:     { name: 'Antminer S19 XP',      th: 141,  watts: 3010, price: 1500  },
    m50splus:  { name: 'Whatsminer M50S+',     th: 140,  watts: 3360, price: 1600  },
    s21:       { name: 'Antminer S21',         th: 200,  watts: 3500, price: 2800  },
    m60s:      { name: 'Whatsminer M60S',      th: 186,  watts: 3441, price: 2600  },
    s21plus:   { name: 'Antminer S21+',        th: 216,  watts: 3456, price: 3500  },
    s21pro:    { name: 'Antminer S21 Pro',     th: 234,  watts: 3510, price: 4200  },
    s21xp:     { name: 'Antminer S21 XP',     th: 270,  watts: 3531, price: 6018  },
    s21xp_hyd: { name: 'Antminer S21 XP Hyd', th: 473,  watts: 5676, price: 9500  }
  };

  const BTC_PRICE_USD     = 85000;
  const NETWORK_HASHRATE  = 800e6;   // TH/s (~800 EH/s)
  const BLOCK_REWARD      = 3.125;
  const BLOCKS_PER_DAY    = 144;

  function calcDailyBtc(th) {
    return (th / NETWORK_HASHRATE) * BLOCKS_PER_DAY * BLOCK_REWARD;
  }

  function updateCalc() {
    const selectEl   = document.getElementById('abc-equip-select');
    const rangeEl    = document.getElementById('abc-kwh-range');
    const kwhValEl   = document.getElementById('abc-kwh-val');
    const dailyEl    = document.getElementById('abc-result-daily');
    const monthEl    = document.getElementById('abc-result-month');
    const roiEl      = document.getElementById('abc-result-roi');
    const btcEl      = document.getElementById('abc-result-btc');

    if (!selectEl || !rangeEl) return;

    const equip    = EQUIPMENT[selectEl.value];
    const kwh      = parseFloat(rangeEl.value);

    // Display kWh value — show "GRATIS" at $0
    if (kwhValEl) {
      kwhValEl.textContent = kwh === 0 ? '¡GRATIS! ⚡' : '$' + kwh.toFixed(3);
      kwhValEl.style.color = kwh === 0 ? '#00C853' : 'var(--abc-yellow)';
    }

    const dailyBtc     = calcDailyBtc(equip.th);
    const dailyElec    = (equip.watts / 1000) * 24 * kwh;
    const dailyRevenue = dailyBtc * BTC_PRICE_USD;
    const dailyProfit  = dailyRevenue - dailyElec;
    const monthProfit  = dailyProfit * 30;
    const roiMonths    = equip.price / Math.max(monthProfit, 0.01);

    if (dailyEl) {
      dailyEl.textContent = '$' + Math.max(dailyProfit, 0).toFixed(2);
      dailyEl.style.color = dailyProfit >= 0 ? 'var(--abc-green)' : 'var(--abc-red)';
    }
    if (monthEl)  monthEl.textContent  = '$' + Math.max(monthProfit, 0).toFixed(0);
    if (roiEl)    roiEl.textContent    = monthProfit > 0 ? roiMonths.toFixed(1) + ' meses' : '∞';
    if (btcEl)    btcEl.textContent    = (dailyBtc * 1e6).toFixed(3) + ' μBTC';
  }

  function initCalc() {
    const select = document.getElementById('abc-equip-select');
    const range  = document.getElementById('abc-kwh-range');
    if (!select || !range) return;
    select.addEventListener('change', updateCalc);
    range.addEventListener('input', updateCalc);
    updateCalc();
  }

  /* ─── BRAND FILTER TABS ──────────────────────────────────────── */
  function initProductFilter() {
    const btns  = document.querySelectorAll('.abc-filter-btn');
    const items = document.querySelectorAll('.abc-product-item');
    if (!btns.length || !items.length) return;

    btns.forEach(function(btn) {
      btn.addEventListener('click', function() {
        btns.forEach(function(b) { b.classList.remove('active'); });
        btn.classList.add('active');

        var filter = btn.dataset.filter;
        items.forEach(function(item) {
          var brand = item.dataset.brand;
          if (filter === 'all' || brand === filter || brand === 'all') {
            item.style.display = '';
            // Small fade-in effect
            item.style.opacity = '0';
            setTimeout(function() { item.style.opacity = '1'; item.style.transition = 'opacity 0.25s'; }, 10);
          } else {
            item.style.display = 'none';
          }
        });
      });
    });
  }

  /* ─── COUNTER ANIMATION ──────────────────────────────────────── */
  function animateCounter(el) {
    var target  = parseInt(el.dataset.target || el.textContent, 10);
    if (isNaN(target)) return;
    var suffix   = el.dataset.suffix || '';
    var duration = 1800;
    var start    = performance.now();

    function tick(now) {
      var elapsed  = now - start;
      var progress = Math.min(elapsed / duration, 1);
      var eased    = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.round(eased * target) + suffix;
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  function initCounters() {
    var counters = document.querySelectorAll('[data-counter]');
    if (!counters.length) return;

    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });

    counters.forEach(function(el) { observer.observe(el); });
  }

  /* ─── SHOP: SIDEBAR — hide junk filters, inject brand categories ─ */

  var CHIP_SVG = {
    antminer: '<svg width="20" height="20" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="1.5" y="1.5" width="19" height="19" rx="4" stroke="#F7931A" stroke-width="1.5" fill="#F7931A" fill-opacity="0.12"/><rect x="6" y="6" width="10" height="10" rx="2" fill="#F7931A" opacity="0.75"/><line x1="1.5" y1="8" x2="6" y2="8" stroke="#F7931A" stroke-width="1.5"/><line x1="1.5" y1="14" x2="6" y2="14" stroke="#F7931A" stroke-width="1.5"/><line x1="16" y1="8" x2="20.5" y2="8" stroke="#F7931A" stroke-width="1.5"/><line x1="16" y1="14" x2="20.5" y2="14" stroke="#F7931A" stroke-width="1.5"/><line x1="8" y1="1.5" x2="8" y2="6" stroke="#F7931A" stroke-width="1.5"/><line x1="14" y1="1.5" x2="14" y2="6" stroke="#F7931A" stroke-width="1.5"/><line x1="8" y1="16" x2="8" y2="20.5" stroke="#F7931A" stroke-width="1.5"/><line x1="14" y1="16" x2="14" y2="20.5" stroke="#F7931A" stroke-width="1.5"/></svg>',
    whatsminer: '<svg width="20" height="20" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="1.5" y="1.5" width="19" height="19" rx="4" stroke="#1A7FF7" stroke-width="1.5" fill="#1A7FF7" fill-opacity="0.12"/><rect x="6" y="6" width="10" height="10" rx="2" fill="#1A7FF7" opacity="0.75"/><line x1="1.5" y1="8" x2="6" y2="8" stroke="#1A7FF7" stroke-width="1.5"/><line x1="1.5" y1="14" x2="6" y2="14" stroke="#1A7FF7" stroke-width="1.5"/><line x1="16" y1="8" x2="20.5" y2="8" stroke="#1A7FF7" stroke-width="1.5"/><line x1="16" y1="14" x2="20.5" y2="14" stroke="#1A7FF7" stroke-width="1.5"/><line x1="8" y1="1.5" x2="8" y2="6" stroke="#1A7FF7" stroke-width="1.5"/><line x1="14" y1="1.5" x2="14" y2="6" stroke="#1A7FF7" stroke-width="1.5"/><line x1="8" y1="16" x2="8" y2="20.5" stroke="#1A7FF7" stroke-width="1.5"/><line x1="14" y1="16" x2="14" y2="20.5" stroke="#1A7FF7" stroke-width="1.5"/></svg>',
    avalon:    '<svg width="20" height="20" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="1.5" y="1.5" width="19" height="19" rx="4" stroke="#00C853" stroke-width="1.5" fill="#00C853" fill-opacity="0.12"/><rect x="6" y="6" width="10" height="10" rx="2" fill="#00C853" opacity="0.75"/><line x1="1.5" y1="8" x2="6" y2="8" stroke="#00C853" stroke-width="1.5"/><line x1="1.5" y1="14" x2="6" y2="14" stroke="#00C853" stroke-width="1.5"/><line x1="16" y1="8" x2="20.5" y2="8" stroke="#00C853" stroke-width="1.5"/><line x1="16" y1="14" x2="20.5" y2="14" stroke="#00C853" stroke-width="1.5"/><line x1="8" y1="1.5" x2="8" y2="6" stroke="#00C853" stroke-width="1.5"/><line x1="14" y1="1.5" x2="14" y2="6" stroke="#00C853" stroke-width="1.5"/><line x1="8" y1="16" x2="8" y2="20.5" stroke="#00C853" stroke-width="1.5"/><line x1="14" y1="16" x2="14" y2="20.5" stroke="#00C853" stroke-width="1.5"/></svg>'
  };

  var BRAND_CATS = [
    { key: 'antminer',    label: 'Antminer / Bitmain',   color: '#F7931A', href: '/shop/category/antminer-bitmain-10'    },
    { key: 'whatsminer',  label: 'Whatsminer / MicroBT', color: '#1A7FF7', href: '/shop/category/whatsminer-microbt-11'  },
    { key: 'avalon',      label: 'Avalon / Canaan',       color: '#00C853', href: '/shop/category/avalon-canaan-12'       }
  ];

  function hideHashrateFilter() {
    if (!window.location.pathname.startsWith('/shop')) return;

    // Hide all sidebar filter sections (Hashrate, Etiquetas, and other attrs)
    // We will replace them with our own category section
    var allSections = document.querySelectorAll(
      'form.js_attributes > div, ' +
      'form.js_attributes .accordion-item, ' +
      '#o_wsale_form aside > div, ' +
      '#o_wsale_form aside .accordion-item'
    );
    allSections.forEach(function(el) {
      var title = el.querySelector('b, h6');
      if (title) el.style.display = 'none';
    });
  }

  function injectShopCategories() {
    if (!window.location.pathname.startsWith('/shop')) return;

    // Find the sidebar form
    var sidebar = document.querySelector('form.js_attributes, #o_wsale_form aside');
    if (!sidebar) return;

    // Don't inject twice
    if (sidebar.querySelector('.abc-sidebar-cats')) return;

    // Detect currently active category from URL
    var currentPath = window.location.pathname;

    var html = '<div class="abc-sidebar-cats" style="padding: 0 0 1.5rem;">';
    html += '<h6 style="color: var(--abc-muted); font-size: .7rem; text-transform: uppercase; letter-spacing: .1em; font-weight: 700; margin-bottom: .85rem;">Categorías</h6>';
    html += '<ul style="list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:.4rem;">';

    // "Todos" link
    var allActive = !BRAND_CATS.some(function(c) { return currentPath.includes(c.key); });
    html += '<li><a href="/shop" style="display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:8px;text-decoration:none;border:1.5px solid ' +
      (allActive ? 'var(--abc-yellow)' : 'var(--abc-border)') +
      ';background:' + (allActive ? 'var(--abc-yellow-bg)' : 'var(--abc-card)') +
      ';color:' + (allActive ? 'var(--abc-yellow)' : 'var(--abc-text)') +
      ';font-weight:600;font-size:.88rem;transition:all .2s;">' +
      '<span style="width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:1rem;">⊞</span>' +
      'Todos los equipos</a></li>';

    BRAND_CATS.forEach(function(cat) {
      var isActive = currentPath.includes(cat.key);
      html += '<li><a href="' + cat.href + '" style="display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:8px;text-decoration:none;border:1.5px solid ' +
        (isActive ? cat.color : 'rgba(' + hexToRgb(cat.color) + ',.3)') +
        ';background:' + (isActive ? 'rgba(' + hexToRgb(cat.color) + ',.12)' : 'var(--abc-card)') +
        ';color:' + (isActive ? cat.color : 'var(--abc-text)') +
        ';font-weight:600;font-size:.88rem;transition:all .2s;">' +
        CHIP_SVG[cat.key] + cat.label + '</a></li>';
    });

    html += '</ul></div>';

    sidebar.insertAdjacentHTML('afterbegin', html);
  }

  function hexToRgb(hex) {
    var r = parseInt(hex.slice(1,3),16);
    var g = parseInt(hex.slice(3,5),16);
    var b = parseInt(hex.slice(5,7),16);
    return r + ',' + g + ',' + b;
  }

  /* ─── STICKY HEADER SHADOW ───────────────────────────────────── */
  function initStickyHeader() {
    var header = document.querySelector('header, nav.navbar');
    if (!header) return;
    window.addEventListener('scroll', function() {
      if (window.scrollY > 40) {
        header.style.boxShadow = '0 4px 30px rgba(0,0,0,0.6)';
      } else {
        header.style.boxShadow = '';
      }
    }, { passive: true });
  }

  /* ─── INIT ───────────────────────────────────────────────────── */
  function init() {
    initCalc();
    initProductFilter();
    initCounters();
    initStickyHeader();
    hideHashrateFilter();
    injectShopCategories();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
