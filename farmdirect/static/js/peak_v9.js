/* FarmDirect V9 — premium cross-site interaction layer.
   UI only. No API, route, form semantics or business logic changes. */
(() => {
  'use strict';
  if (window.__FD_V9_READY__) return;
  window.__FD_V9_READY__ = true;

  const doc = document;
  const root = doc.documentElement;
  const body = doc.body;
  const motionLevel = window.FD_MOTION_LEVEL || 'balanced';
  const reduced = motionLevel === 'reduced' || matchMedia('(prefers-reduced-motion: reduce)').matches;
  const fine = matchMedia('(hover:hover) and (pointer:fine)').matches;
  const mobile = matchMedia('(max-width: 767.98px)').matches;

  const ready = (fn) => doc.readyState === 'loading'
    ? doc.addEventListener('DOMContentLoaded', fn, { once: true })
    : fn();

  ready(() => {
    body.classList.add('fd-v9-ready');
    installGlobalGlow();
    installPremiumSurfaces();
    installReveals();
    installProductStagger();
    installMobileMarketplaceFilters();
    installTouchPolish();
    installButtonSparks();
    installMagneticMicroMotion();
    installResponsiveSanity();
  });

  function installGlobalGlow() {
    if (!fine || reduced || motionLevel === 'lite') return;
    let glow = doc.querySelector('.fd-v9-page-glow');
    if (!glow) {
      glow = doc.createElement('span');
      glow.className = 'fd-v9-page-glow';
      glow.setAttribute('aria-hidden', 'true');
      body.appendChild(glow);
    }
    const main = doc.querySelector('body:not(.fd-route-views-landing) main');
    // The moving gradient belongs only to main::before. Give that pseudo-element
    // its own rule so a pointer move does not invalidate every product's style.
    let backdropStyle = null;
    if (main) {
      const style = doc.createElement('style');
      style.textContent = 'body:not(.fd-route-views-landing) main::before { --fd-v9-x: 50%; }';
      doc.head.appendChild(style);
      backdropStyle = style.sheet.cssRules[0].style;
    }
    let raf = 0;
    let x = -999, y = -999;
    const paint = () => {
      raf = 0;
      if (backdropStyle) backdropStyle.setProperty('--fd-v9-x', `${(x / Math.max(1, innerWidth) * 100).toFixed(1)}%`);
      glow.style.setProperty('--fd-v9-pointer-left', `${x}px`);
      glow.style.setProperty('--fd-v9-pointer-top', `${y}px`);
    };
    addEventListener('pointermove', (e) => {
      x = e.clientX; y = e.clientY;
      body.classList.add('fd-v9-pointer-active');
      if (!raf) raf = requestAnimationFrame(paint);
    }, { passive: true });
    doc.addEventListener('mouseleave', () => body.classList.remove('fd-v9-pointer-active'));
  }

  function installPremiumSurfaces() {
    const selector = [
      'main .fd-card', 'main .fd-stat', 'main .fd-benefit', 'main .fd-table',
      'main .fd-product-card-v9', 'main .fd-market-hero'
    ].join(',');
    const surfaces = [...doc.querySelectorAll(selector)]
      .filter((el, i, arr) => arr.indexOf(el) === i);

    surfaces.forEach(el => el.classList.add('fd-v9-rich-surface'));
    if (!fine || reduced || motionLevel === 'lite') return;

    surfaces.forEach(el => FDMotion.pointer(el, (r, clientX, clientY) => {
      if (!r.width || !r.height) return;
      const x = Math.max(0, Math.min(1, (clientX - r.left) / r.width));
      const y = Math.max(0, Math.min(1, (clientY - r.top) / r.height));
      el.style.setProperty('--fd-v9-local-x', `${(x * 100).toFixed(1)}%`);
      el.style.setProperty('--fd-v9-local-y', `${(y * 100).toFixed(1)}%`);
    }));
  }

  function installReveals() {
    const targets = [...doc.querySelectorAll([
      'main .fd-card:not(.fd-product-card-v9)',
      'main .fd-stat',
      'main .fd-table',
      'main .fd-section-title',
      'main .fd-market-hero',
      'main .breadcrumb',
      'main .chart-box',
      'main .chart-box-sm',
      'main #fd-map'
    ].join(','))].filter((el, i, arr) => arr.indexOf(el) === i);

    if (reduced || !('IntersectionObserver' in window)) {
      targets.forEach(el => el.classList.add('fd-v9-visible'));
      return;
    }

    targets.forEach((el, i) => {
      if (el.closest('.fd-hero')) return;
      el.classList.add('fd-v9-reveal');
      el.style.setProperty('--fd-v9-delay', `${Math.min((i % 8) * 36, 180)}ms`);
    });
    const io = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('fd-v9-visible');
        obs.unobserve(entry.target);
      });
    }, { threshold: .055, rootMargin: '0px 0px -3% 0px' });
    targets.filter(el => el.classList.contains('fd-v9-reveal')).forEach(el => io.observe(el));
  }

  function installProductStagger() {
    const cards = [...doc.querySelectorAll('.fd-product-card-v9')];
    if (!cards.length) return;
    if (reduced) return;
    cards.forEach((card, i) => {
      card.classList.add('fd-v9-card-enter');
      card.style.setProperty('--fd-v9-enter-delay', `${Math.min((i % 9) * 55, 330)}ms`);
    });
  }

  function installMobileMarketplaceFilters() {
    const trigger = doc.querySelector('[data-fd-filter-toggle]');
    const sidebar = doc.querySelector('.fd-market-sidebar-col');
    if (!trigger || !sidebar) return;

    const mq = matchMedia('(max-width: 991.98px)');
    const sync = () => {
      if (mq.matches) {
        sidebar.classList.add('fd-v9-filter-collapsed');
        trigger.setAttribute('aria-expanded', 'false');
      } else {
        sidebar.classList.remove('fd-v9-filter-collapsed');
        trigger.setAttribute('aria-expanded', 'true');
      }
    };
    sync();
    if (mq.addEventListener) mq.addEventListener('change', sync);

    trigger.addEventListener('click', () => {
      const collapsed = sidebar.classList.toggle('fd-v9-filter-collapsed');
      trigger.setAttribute('aria-expanded', String(!collapsed));
      trigger.innerHTML = collapsed
        ? '<i class="bi bi-sliders"></i> Filters'
        : '<i class="bi bi-x-lg"></i> Close filters';
      if (!collapsed) {
        requestAnimationFrame(() => sidebar.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' }));
      }
    });
  }

  function installTouchPolish() {
    if (!mobile) return;
    doc.addEventListener('pointerdown', (e) => {
      const el = e.target.closest('.fd-product-card-v9,.fd-stat,.fd-card .btn,.fd-demo-account');
      if (!el || el.classList.contains('demo-cred')) return;
      el.classList.remove('fd-v9-touch-pop');
      requestAnimationFrame(() => el.classList.add('fd-v9-touch-pop'));
      setTimeout(() => el.classList.remove('fd-v9-touch-pop'), 450);
    }, { passive: true });
  }

  function installButtonSparks() {
    if (reduced) return;
    doc.addEventListener('click', (e) => {
      const button = e.target.closest('.btn-fd');
      if (!button || button.classList.contains('demo-cred')) return;
      const r = button.getBoundingClientRect();
      const cx = e.clientX || (r.left + r.width / 2);
      const cy = e.clientY || (r.top + r.height / 2);
      for (let i = 0; i < (mobile ? 4 : 6); i++) {
        const spark = doc.createElement('span');
        spark.className = 'fd-v9-spark';
        const angle = (Math.PI * 2 * i / (mobile ? 4 : 6)) + Math.random() * .35;
        const distance = 18 + Math.random() * 18;
        spark.style.left = `${cx - r.left - 4}px`;
        spark.style.top = `${cy - r.top - 4}px`;
        spark.style.setProperty('--fd-v9-sx', `${Math.cos(angle) * distance}px`);
        spark.style.setProperty('--fd-v9-sy', `${Math.sin(angle) * distance}px`);
        button.appendChild(spark);
        spark.addEventListener('animationend', () => spark.remove(), { once: true });
      }
    });
  }

  function installMagneticMicroMotion() {
    if (!fine || reduced || motionLevel === 'lite') return;
    document.querySelectorAll('.fd-market-hero .btn,.fd-product-actions .btn,.fd-auth-submit,.fd-mobile-filter-trigger').forEach(el => {
      FDMotion.pointer(el, (r, clientX, clientY) => {
        const dx = (clientX - (r.left + r.width / 2)) / Math.max(1, r.width);
        const dy = (clientY - (r.top + r.height / 2)) / Math.max(1, r.height);
        el.style.transform = `translate(${(dx * 4).toFixed(1)}px, ${(dy * 3).toFixed(1)}px)`;
      }, () => { el.style.transform = ''; });
    });
  }

  function installResponsiveSanity() {
    // Long dynamic values must never overflow cards on small screens.
    const risky = doc.querySelectorAll('.fd-card b,.fd-card strong,.fd-card .fw-bold,.fd-table td,.fd-table th');
    risky.forEach(el => {
      el.style.overflowWrap ||= 'anywhere';
    });

    // Avoid off-screen animation cost on product cards and stats.
    if (!('IntersectionObserver' in window)) return;
    const animated = [...doc.querySelectorAll('.fd-product-card-v9,.fd-stat')];
    const io = new IntersectionObserver(entries => {
      entries.forEach(entry => entry.target.classList.toggle('fd-v9-offscreen', !entry.isIntersecting));
    }, { rootMargin: '180px 0px' });
    animated.forEach(el => io.observe(el));
  }
})();
