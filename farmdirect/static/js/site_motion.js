/* FarmDirect V5 — site-wide adaptive motion & responsive interaction layer.
   UI only: no business logic, routes, data, or API semantics are changed. */
(() => {
  'use strict';

  const root = document.documentElement;
  const body = document.body;
  const level = window.FD_MOTION_LEVEL || 'balanced';
  const reduced = level === 'reduced' || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const finePointer = window.matchMedia('(hover:hover) and (pointer:fine)').matches;
  const isMax = level === 'max';
  const isLite = level === 'lite';

  const ready = fn => {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn, { once: true });
    else fn();
  };

  ready(() => {
    body.classList.add('fd-v5-ready', `fd-v5-${level}`);
    installAtmosphere();
    installPointerAndScrollVars();
    installLiveSurfaces();
    installTouchFeedback();
    installSiteReveal();
    installStatsMotion();
    installTableMotion();
    installMobileNav();
    installPageTransitions();
    installAnimationPausing();
    installFormFeedback();
    installIVREnhancements();
  });

  function installAtmosphere() {
    if (document.querySelector('.fd-v5-atmosphere')) return;
    const layer = document.createElement('div');
    layer.className = 'fd-v5-atmosphere';
    layer.setAttribute('aria-hidden', 'true');
    layer.innerHTML = '<span class="fd-v5-orb o1"></span><span class="fd-v5-orb o2"></span><span class="fd-v5-orb o3"></span><span class="fd-v5-grid"></span><span class="fd-v5-pointer-light"></span>';
    body.prepend(layer);
  }

  function installPointerAndScrollVars() {
    let pointerRaf = 0;
    const pointerTargets = document.querySelectorAll('.fd-v5-atmosphere, .fd-auth-wrap > .fd-card:first-child');
    let px = 50, py = 18;
    const syncPointer = () => {
      pointerRaf = 0;
      pointerTargets.forEach(el => {
        el.style.setProperty('--fd-v5-x', `${px.toFixed(2)}%`);
        el.style.setProperty('--fd-v5-y', `${py.toFixed(2)}%`);
      });
    };
    if (finePointer && !reduced && !isLite) {
      window.addEventListener('pointermove', e => {
        px = e.clientX / Math.max(1, window.innerWidth) * 100;
        py = e.clientY / Math.max(1, window.innerHeight) * 100;
        if (!pointerRaf) pointerRaf = requestAnimationFrame(syncPointer);
      }, { passive: true });
    }

    let scrollRaf = 0;
    let maxScroll = 1;
    const atmosphere = document.querySelector('.fd-v5-atmosphere');
    const main = document.querySelector('main');
    const measureScroll = () => {
      maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    };
    const syncScroll = () => {
      scrollRaf = 0;
      const progress = Math.max(0, Math.min(1, window.scrollY / maxScroll));
      // --fd-v5-scroll is consumed only by the atmosphere grid. Scoping the
      // variable here avoids recalculating styles for the entire document.
      if (atmosphere) atmosphere.style.setProperty('--fd-v5-scroll', progress.toFixed(4));
    };
    const requestScroll = () => { if (!scrollRaf) scrollRaf = requestAnimationFrame(syncScroll); };
    const remeasureScroll = () => { measureScroll(); requestScroll(); };
    measureScroll();
    syncScroll();
    window.addEventListener('scroll', requestScroll, { passive: true });
    window.addEventListener('resize', remeasureScroll, { passive: true });
    if ('ResizeObserver' in window && main) {
      const ro = new ResizeObserver(remeasureScroll);
      ro.observe(main);
    }
  }

  function installLiveSurfaces() {
    const selectors = [
      'main .fd-card:not(.fd-table)',
      'main .fd-stat',
      'main .fd-benefit',
      'main .fd-product-card',
      '.fd-auth-wrap > .fd-card',
      '.ivr-phone'
    ];
    const surfaces = [...document.querySelectorAll(selectors.join(','))]
      .filter((el, i, arr) => arr.indexOf(el) === i);

    surfaces.forEach(el => el.classList.add('fd-v5-surface'));
    if (!finePointer || reduced || !isMax) return;

    surfaces.forEach(el => {
      if (el.classList.contains('fd-tilt-ready')) return;
      FDMotion.pointer(el, (r, clientX, clientY) => {
        if (!r.width || !r.height) return;
        const x = Math.max(0, Math.min(1, (clientX - r.left) / r.width));
        const y = Math.max(0, Math.min(1, (clientY - r.top) / r.height));
        el.style.setProperty('--fd-v5-card-x', `${(x * 100).toFixed(1)}%`);
        el.style.setProperty('--fd-v5-card-y', `${(y * 100).toFixed(1)}%`);
        el.style.setProperty('--fd-v5-rx', `${((.5 - y) * 3.4).toFixed(2)}deg`);
        el.style.setProperty('--fd-v5-ry', `${((x - .5) * 4.2).toFixed(2)}deg`);
      }, () => {
        el.style.setProperty('--fd-v5-card-x', '50%');
        el.style.setProperty('--fd-v5-card-y', '50%');
        el.style.setProperty('--fd-v5-rx', '0deg');
        el.style.setProperty('--fd-v5-ry', '0deg');
      });
    });
  }

  function installTouchFeedback() {
    document.addEventListener('pointerdown', e => {
      const target = e.target.closest('.btn,.nav-link,.fd-card-hover,.fd-product-card,.ivr-key,.ivr-script-btn,.ivr-caller-card,.fd-nav-language-btn');
      if (!target || target.classList.contains('demo-cred')) return;
      target.classList.remove('fd-v5-pressed');
      void target.offsetWidth;
      target.classList.add('fd-v5-pressed');
      window.setTimeout(() => target.classList.remove('fd-v5-pressed'), 360);

      if (reduced) return;
      const r = target.getBoundingClientRect();
      const ripple = document.createElement('span');
      ripple.className = 'fd-v5-tap-ripple';
      ripple.style.left = `${e.clientX - r.left}px`;
      ripple.style.top = `${e.clientY - r.top}px`;
      target.appendChild(ripple);
      ripple.addEventListener('animationend', () => ripple.remove(), { once: true });
    }, { passive: true });
  }

  function installSiteReveal() {
    const targets = [...document.querySelectorAll([
      'main .fd-section-title',
      'main .fd-subtle',
      'main .breadcrumb',
      'main .progress',
      'main .fd-pipeline',
      'main form',
      'main .alert',
      'main .ivr-script-btn',
      'main .ivr-caller-card'
    ].join(','))].filter((el, i, arr) => arr.indexOf(el) === i && !el.classList.contains('fd-cine-reveal'));

    if (reduced || !('IntersectionObserver' in window)) {
      targets.forEach(el => el.classList.add('fd-v5-reveal-visible'));
      return;
    }
    targets.forEach((el, i) => {
      el.classList.add('fd-v5-reveal');
      el.style.setProperty('--fd-v5-delay', `${Math.min((i % 7) * 34, 180)}ms`);
    });
    const io = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('fd-v5-reveal-visible');
        obs.unobserve(entry.target);
      });
    }, { threshold: .06, rootMargin: '0px 0px -5% 0px' });
    targets.forEach(el => io.observe(el));
  }

  function installStatsMotion() {
    if (reduced || !('IntersectionObserver' in window)) return;
    const values = [...document.querySelectorAll('main .stat-value')]
      .filter(el => !el.closest('.fd-hero'));
    const io = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        obs.unobserve(entry.target);
        const el = entry.target;
        const raw = el.textContent.trim();
        const m = raw.match(/^([^\d-]*)(-?\d[\d,]*(?:\.\d+)?)(.*)$/);
        if (!m) return;
        const numText = m[2].replace(/,/g, '');
        const target = Number(numText);
        if (!Number.isFinite(target)) return;
        const decimals = numText.includes('.') ? numText.split('.')[1].length : 0;
        const formatter = new Intl.NumberFormat(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
        const start = performance.now();
        const duration = level === 'max' ? 980 : 650;
        const frame = now => {
          const t = Math.min(1, (now - start) / duration);
          const eased = 1 - Math.pow(1 - t, 4);
          const val = target * eased;
          const formatted = formatter.format(val);
          el.textContent = m[1] + formatted + m[3];
          if (t < 1) requestAnimationFrame(frame); else el.textContent = raw;
        };
        requestAnimationFrame(frame);
      });
    }, { threshold: .55 });
    values.forEach(el => io.observe(el));
  }

  function installTableMotion() {
    const rows = [...document.querySelectorAll('.fd-table tbody tr')];
    if (!rows.length) return;
    rows.forEach((row, i) => {
      row.classList.add('fd-v5-row');
      row.style.setProperty('--fd-v5-row-delay', `${Math.min((i % 10) * 22, 180)}ms`);
    });
    if (reduced || !('IntersectionObserver' in window)) {
      rows.forEach(row => row.classList.add('fd-v5-row-visible'));
      return;
    }
    const io = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('fd-v5-row-visible');
        obs.unobserve(entry.target);
      });
    }, { threshold: .02, rootMargin: '0px 0px -2% 0px' });
    rows.forEach(row => io.observe(row));
  }

  function installMobileNav() {
    const nav = document.getElementById('fdnav');
    if (!nav || !window.bootstrap) return;
    let backdrop = document.querySelector('.fd-v5-nav-backdrop');
    if (!backdrop) {
      backdrop = document.createElement('button');
      backdrop.type = 'button';
      backdrop.className = 'fd-v5-nav-backdrop';
      backdrop.setAttribute('aria-label', 'Close menu');
      body.appendChild(backdrop);
    }
    const open = () => body.classList.add('fd-mobile-nav-open');
    const close = () => body.classList.remove('fd-mobile-nav-open');
    nav.addEventListener('show.bs.collapse', open);
    nav.addEventListener('hidden.bs.collapse', close);
    backdrop.addEventListener('click', () => {
      const instance = bootstrap.Collapse.getOrCreateInstance(nav, { toggle: false });
      instance.hide();
    });
    nav.querySelectorAll('a[href]:not([data-bs-toggle])').forEach(link => link.addEventListener('click', close));
  }

  function installPageTransitions() {
    if (reduced || document.querySelector('.fd-v5-page-wipe')) return;
    const wipe = document.createElement('div');
    wipe.className = 'fd-v5-page-wipe';
    wipe.setAttribute('aria-hidden', 'true');
    body.appendChild(wipe);
    requestAnimationFrame(() => requestAnimationFrame(() => body.classList.add('fd-page-arrived')));

    document.addEventListener('click', e => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = e.target.closest('a[href]');
      if (!a || a.target === '_blank' || a.hasAttribute('download') || a.hasAttribute('data-bs-toggle')) return;
      let url;
      try { url = new URL(a.href, location.href); } catch (_) { return; }
      if (url.origin !== location.origin || url.protocol !== location.protocol) return;
      if (url.pathname === location.pathname && url.search === location.search && url.hash) return;
      if (!url.href || url.href === location.href) return;
      e.preventDefault();
      body.classList.add('fd-page-leaving');
      window.setTimeout(() => { location.href = url.href; }, level === 'max' ? 210 : 145);
    });

    window.addEventListener('pageshow', () => body.classList.remove('fd-page-leaving'));
  }

  function installAnimationPausing() {
    const heavyZones = [...document.querySelectorAll('.fd-hero,.fd-hero-art,.fd-kinetic-band,.ivr-phone-wrap,.fd-footer')];
    if ('IntersectionObserver' in window && heavyZones.length) {
      const io = new IntersectionObserver(entries => {
        entries.forEach(entry => entry.target.classList.toggle('fd-v5-offscreen', !entry.isIntersecting));
      }, { rootMargin: '180px 0px' });
      heavyZones.forEach(el => io.observe(el));
    }
    const syncVisibility = () => body.classList.toggle('fd-v5-page-hidden', document.hidden);
    syncVisibility();
    document.addEventListener('visibilitychange', syncVisibility);
  }

  function installFormFeedback() {
    document.addEventListener('focusin', e => {
      const field = e.target.closest('.form-control,.form-select,textarea');
      if (!field) return;
      field.closest('.mb-3,.mb-2,[class*="col-"]')?.classList.add('fd-v5-field-focus');
    });
    document.addEventListener('focusout', e => {
      const field = e.target.closest('.form-control,.form-select,textarea');
      if (!field) return;
      field.closest('.mb-3,.mb-2,[class*="col-"]')?.classList.remove('fd-v5-field-focus');
    });
    document.addEventListener('change', e => {
      const field = e.target.closest('.form-control,.form-select,textarea');
      if (!field) return;
      field.classList.remove('fd-v5-field-confirm');
      void field.offsetWidth;
      field.classList.add('fd-v5-field-confirm');
      setTimeout(() => field.classList.remove('fd-v5-field-confirm'), 520);
    });
  }

  function installIVREnhancements() {
    const visual = document.querySelector('.ivr-call-visual');
    const phone = document.querySelector('.ivr-phone');
    if (!visual || !phone) return;
    body.classList.add('fd-ivr-v5');
    if (!visual.querySelector('.ivr-v5-eq')) {
      const eq = document.createElement('div');
      eq.className = 'ivr-v5-eq';
      eq.setAttribute('aria-hidden', 'true');
      eq.innerHTML = Array.from({ length: 11 }, (_, i) => `<i style="--i:${i}"></i>`).join('');
      visual.appendChild(eq);
    }
    if (!visual.querySelector('.ivr-v5-radar')) {
      const radar = document.createElement('span');
      radar.className = 'ivr-v5-radar';
      radar.setAttribute('aria-hidden', 'true');
      visual.appendChild(radar);
    }

    const state = document.getElementById('ivr-call-state');
    if (state && 'MutationObserver' in window) {
      const sync = () => {
        const text = state.textContent.toLowerCase();
        phone.dataset.voiceState = text.includes('listen') ? 'listening' : text.includes('speak') ? 'speaking' : text.includes('call') ? 'call' : 'idle';
      };
      sync();
      new MutationObserver(sync).observe(state, { childList: true, characterData: true, subtree: true });
    }
  }
})();
