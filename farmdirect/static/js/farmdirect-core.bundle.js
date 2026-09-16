document.documentElement.classList.remove('no-js');
document.documentElement.classList.add('js');

/* FarmDirect — frontend interactions (vanilla JS, no build step) */

// Works both standalone ("/") and behind a URL prefix (sandbox preview)
const S = window.SCRIPT_ROOT || '';

// ---------- Adaptive motion/performance profile ----------
// Decided synchronously so the cinematic layer that loads after this file can
// scale itself before it starts any expensive visual work.
(() => {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const coarse = window.matchMedia('(pointer: coarse)').matches;
  const saveData = !!(navigator.connection && navigator.connection.saveData);
  const memory = Number(navigator.deviceMemory || 8);
  const cores = Number(navigator.hardwareConcurrency || 8);
  const narrow = Math.min(window.innerWidth, window.screen?.width || window.innerWidth) < 900;

  let level = 'max';
  if (reduced) level = 'reduced';
  else if (saveData || memory <= 2 || cores <= 2) level = 'lite';
  else if (coarse || narrow || memory <= 4 || cores <= 4) level = 'balanced';

  window.FD_MOTION_LEVEL = level;
  document.documentElement.dataset.fdMotion = level;
  document.documentElement.classList.add(`fd-motion-${level}`);
  if (coarse) document.documentElement.classList.add('fd-touch-device');
})();

// ---------- Toast helper ----------
function fdToast(msg, isError) {
  let wrap = document.querySelector('.fd-toast-wrap');
  if (!wrap) {
    wrap = document.createElement('div');
    wrap.className = 'fd-toast-wrap';
    document.body.appendChild(wrap);
  }
  const t = document.createElement('div');
  t.className = 'fd-toast' + (isError ? ' err' : '');
  t.innerHTML = `<i class="bi ${isError ? 'bi-exclamation-circle' : 'bi-check-circle'} me-2"></i>${msg}`;
  wrap.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .4s'; }, 2600);
  setTimeout(() => t.remove(), 3100);
}

// ---------- Cart API ----------
async function api(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data || {}),
  });
  if (res.status === 401 || res.redirected) {
    fdToast('Please log in first', true);
    setTimeout(() => window.location.href = (window.AUTH_URL || S + '/login') + '?next=' + encodeURIComponent(location.pathname), 700);
    throw new Error('unauthorized');
  }
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.error || 'Request failed');
  return json;
}

async function addToCart(productId, qty) {
  try {
    const r = await api(S + '/api/cart/add', { product_id: productId, quantity_kg: qty || 1 });
    fdToast(r.message || 'Added to cart');
    updateCartBadge(r.cart_items);
  } catch (e) { if (e.message !== 'unauthorized') fdToast(e.message, true); }
}

function updateCartBadge(n) {
  document.querySelectorAll('.fd-cart-count').forEach(el => {
    el.textContent = n;
    el.style.display = n > 0 ? 'inline-flex' : 'none';
  });
}

async function cartUpdateQty(cartId, input) {
  const qty = parseFloat(input.value) || 0.5;
  if (qty < 0.5) { input.value = 0.5; return; }
  try {
    await api(S + '/api/cart/update', { cart_id: cartId, quantity_kg: qty });
    setTimeout(() => location.reload(), 250);
  } catch (e) { fdToast(e.message, true); }
}

async function cartRemove(cartId) {
  try {
    await api(S + '/api/cart/remove', { cart_id: cartId });
    const row = document.getElementById('cart-row-' + cartId);
    if (row) row.remove();
    setTimeout(() => location.reload(), 250);
  } catch (e) { fdToast(e.message, true); }
}

// ---------- Farmer order actions ----------
async function itemStatus(orderId, itemId, action) {
  try {
    await api(`${S}/api/orders/${orderId}/item/${iidToPath(itemId)}/status`, { action });
    fdToast(action === 'accept' ? 'Order accepted ✅' : 'Order rejected');
    setTimeout(() => location.reload(), 600);
  } catch (e) { fdToast(e.message, true); }
}
// helper kept trivial for clarity
const iidToPath = (id) => id;

// ---------- Logistics pipeline ----------
async function deliveryAdvance(deliveryId, nextStatus) {
  try {
    await api(`${S}/api/deliveries/${deliveryId}/status`, { status: nextStatus });
    fdToast('Status updated → ' + nextStatus.replace('_', ' '));
    setTimeout(() => location.reload(), 600);
  } catch (e) { fdToast(e.message, true); }
}

// ---------- Bulk quotes ----------
async function requestQuote() {
  const crop = document.getElementById('q-crop').value;
  const qty = document.getElementById('q-qty').value;
  const grade = document.getElementById('q-grade').value;
  const city = document.getElementById('q-city').value;
  try {
    await api(S + '/api/quotes', { crop, quantity_kg: qty, grade, city });
    fdToast('Quotation requested — comparing suppliers…');
    setTimeout(() => location.reload(), 900);
  } catch (e) { fdToast(e.message, true); }
}

async function acceptQuote(qid, rid) {
  try {
    const r = await api(`${S}/api/quotes/${qid}/accept/${rid}`, {});
    fdToast('Supplier accepted — bulk order placed! 🎉');
    setTimeout(() => window.location.href = S + '/track/' + r.order_id, 900);
  } catch (e) { fdToast(e.message, true); }
}

// ---------- Marketplace filters (client-side quick filter) ----------
function quickFilter(input) {
  const q = input.value.toLowerCase();
  document.querySelectorAll('[data-product-card]').forEach(card => {
    const text = card.textContent.toLowerCase();
    card.style.display = text.includes(q) ? '' : 'none';
  });
}

// ---------- Price calculator (listing form) ----------
async function refreshSuggestedPrice() {
  const crop = document.getElementById('f-crop')?.value;
  const grade = document.getElementById('f-grade')?.value;
  const qty = document.getElementById('f-qty')?.value;
  if (!crop) return;
  try {
    const r = await fetch(`${S}/api/ai/price?crop=${encodeURIComponent(crop)}&grade=${grade}&qty=${qty}`);
    const rec = await r.json();
    const el = document.getElementById('suggested-price');
    if (el && rec.suggested_price) {
      el.textContent = '₹' + rec.suggested_price.toFixed(1) + ' /kg';
      const gain = document.getElementById('price-gain-note');
      if (gain) gain.textContent = `${rec.earnings_gain_pct > 0 ? '+' : ''}${rec.earnings_gain_pct}% vs mandi · consumer pays ≈ ₹${rec.consumer_price}/kg`;
    }
  } catch (e) { /* silent */ }
}

// ---------- Chart.js defaults ----------
document.addEventListener('DOMContentLoaded', () => {
  if (window.Chart) {
    Chart.defaults.font.family = "Inter, 'Segoe UI', system-ui, sans-serif";
    Chart.defaults.color = '#65756b';
    Chart.defaults.plugins.legend.labels.boxWidth = 12;
    Chart.defaults.plugins.tooltip.backgroundColor = '#1c2b22';
    Chart.defaults.responsive = true;
    Chart.defaults.maintainAspectRatio = false;
  }
});


// ---------- Visual UX enhancements (no content / business-logic changes) ----------
document.addEventListener('DOMContentLoaded', () => {
  const nav = document.querySelector('.fd-navbar');
  if (nav) {
    let navShadowRaf = 0;
    const syncNavShadow = () => {
      navShadowRaf = 0;
      nav.classList.toggle('fd-scrolled', window.scrollY > 10);
    };
    const requestNavShadow = () => {
      if (!navShadowRaf) navShadowRaf = requestAnimationFrame(syncNavShadow);
    };
    syncNavShadow();
    window.addEventListener('scroll', requestNavShadow, { passive: true });

    const path = window.location.pathname.replace(/\/$/, '') || '/';
    nav.querySelectorAll('a.nav-link[href]').forEach(link => {
      try {
        const target = new URL(link.href, window.location.origin).pathname.replace(/\/$/, '') || '/';
        if (target === path) link.classList.add('active');
      } catch (_) { /* ignore non-URL links */ }
    });
  }

  // Gentle entrance hierarchy for static visual surfaces only.
  // Content remains visible immediately when reduced motion is preferred.
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches && 'IntersectionObserver' in window) {
    const revealTargets = document.querySelectorAll('.fd-benefit, .fd-product-card, .fd-stat, main .fd-card');
    const observer = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('fd-visible');
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.06, rootMargin: '0px 0px -18px 0px' });

    revealTargets.forEach((el, i) => {
      el.classList.add('fd-reveal');
      el.style.transitionDelay = `${Math.min((i % 6) * 35, 175)}ms`;
      observer.observe(el);
    });
  }
});

/* Shared frame phases: measure every active pointer surface before painting any.
   Effects retain their own coordinates, easing, transforms and particle counts. */
(() => {
  'use strict';
  const pending = new Map();
  let raf = 0;

  function flush() {
    raf = 0;
    const jobs = [...pending.values()];
    pending.clear();
    const rects = new Map();
    const measure = el => {
      if (!rects.has(el)) rects.set(el, el.getBoundingClientRect());
      return rects.get(el);
    };
    const values = jobs.map(job => job.read(measure));
    jobs.forEach((job, i) => job.write(values[i]));
  }

  function schedule(key, read, write) {
    pending.set(key, { read, write });
    if (!raf) raf = requestAnimationFrame(flush);
  }

  function cancel(key) {
    pending.delete(key);
    if (!pending.size && raf) {
      cancelAnimationFrame(raf);
      raf = 0;
    }
  }

  function pointer(el, paint, leave) {
    const key = {};
    el.addEventListener('pointermove', e => {
      const x = e.clientX, y = e.clientY;
      schedule(key, measure => ({ rect: measure(el), x, y }), value => {
        if (el.isConnected) paint(value.rect, value.x, value.y);
      });
    }, { passive: true });
    el.addEventListener('pointerleave', () => {
      cancel(key);
      if (leave) leave();
    }, { passive: true });
  }

  window.FDMotion = { schedule, cancel, pointer };
})();

/* FarmDirect — cinematic UI motion system (visual layer only) */
(() => {
  'use strict';

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const finePointer = window.matchMedia('(hover:hover) and (pointer:fine)').matches;
  const motionLevel = window.FD_MOTION_LEVEL || (reduceMotion ? 'reduced' : (finePointer ? 'max' : 'balanced'));
  const liteMotion = motionLevel === 'lite';
  const fullMotion = motionLevel === 'max';
  const root = document.documentElement;
  const body = document.body;

  function ready(fn) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn, { once: true });
    else fn();
  }

  ready(() => {
    installIntroLoader();
    installHeroDecor();
    installKineticBand();
    installGlobalTrail();
    installSectionSpotlights();
    installPressPhysics();
    installScrollProgress();
    installRevealSystem();
    installCounterMotion();
    installTilt();
    installMagnetism();
    installCursorAura();
    installHeroInteraction();
    installHeroParticles();
    installParallax();
    installEnergyDots();
    installRippleFeedback();
  });

  function installScrollProgress() {
    let bar = document.getElementById('fd-scroll-progress');
    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'fd-scroll-progress';
      bar.setAttribute('aria-hidden', 'true');
      body.appendChild(bar);
    }
    // Keep exactly the same scroll-driven visuals, but avoid forcing a full
    // document style/layout invalidation on every scroll frame.
    const heroCopy = document.querySelector('.fd-route-views-landing .fd-hero .col-lg-7');
    const main = document.querySelector('main');
    const scrollStyle = document.createElement('style');
    scrollStyle.textContent = '.fd-shell main::before, .fd-shell main::after { --fd-scroll-p: 0; }';
    document.head.appendChild(scrollStyle);
    const filmStyle = scrollStyle.sheet.cssRules[0].style;
    let maxScroll = 1;
    let ticking = false;
    const measure = () => {
      maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    };
    const sync = () => {
      ticking = false;
      const p = Math.min(1, Math.max(0, window.scrollY / maxScroll));
      const value = p.toFixed(4);
      bar.style.transform = `scaleX(${p})`;
      if (heroCopy) heroCopy.style.setProperty('--fd-scroll-p', value);
      filmStyle.setProperty('--fd-scroll-p', value);
    };
    const request = () => {
      if (!ticking) { ticking = true; requestAnimationFrame(sync); }
    };
    const remeasure = () => { measure(); request(); };
    measure();
    sync();
    window.addEventListener('scroll', request, { passive: true });
    window.addEventListener('resize', remeasure, { passive: true });
    if ('ResizeObserver' in window && main) {
      const ro = new ResizeObserver(remeasure);
      ro.observe(main);
    }
  }

  function installRevealSystem() {
    const selectors = [
      '.fd-route-views-landing main > section:not(.fd-hero) .fd-section-title',
      '.fd-route-views-landing .fd-benefit',
      '.fd-route-views-landing .fd-product-card',
      '.fd-route-views-landing main > section:not(.fd-hero) .fd-card',
      '.fd-route-views-landing main > section:not(.fd-hero) .fd-chain-row',
      '.fd-shell:not(.fd-route-views-landing) main .fd-card',
      '.fd-shell:not(.fd-route-views-landing) main .fd-stat',
      '.fd-shell:not(.fd-route-views-landing) main .fd-table'
    ];
    const items = [...document.querySelectorAll(selectors.join(','))]
      .filter((el, idx, arr) => arr.indexOf(el) === idx);
    if (!items.length || reduceMotion || !('IntersectionObserver' in window)) {
      items.forEach(el => el.classList.add('fd-cine-visible'));
      return;
    }

    items.forEach((el, i) => {
      el.classList.add('fd-cine-reveal');
      if (i % 7 === 2) el.classList.add('fd-cine-from-left');
      else if (i % 7 === 5) el.classList.add('fd-cine-from-right');
      el.style.transitionDelay = `${Math.min((i % 5) * 55, 220)}ms`;
    });

    const io = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('fd-cine-visible');
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -6% 0px' });
    items.forEach(el => io.observe(el));
  }

  function installCounterMotion() {
    if (reduceMotion || !('IntersectionObserver' in window)) return;
    const values = [...document.querySelectorAll('.fd-hero .stat-value')];
    if (!values.length) return;
    const io = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        obs.unobserve(el);
        const raw = el.textContent.trim();
        const m = raw.match(/^([^\d-]*)(-?\d+(?:\.\d+)?)(.*)$/);
        if (!m) return;
        const [, prefix, numText, suffix] = m;
        const target = Number(numText);
        if (!Number.isFinite(target)) return;
        const decimal = numText.includes('.') ? (numText.split('.')[1] || '').length : 0;
        const started = performance.now();
        const duration = 1150;
        const frame = now => {
          const t = Math.min(1, (now - started) / duration);
          const eased = 1 - Math.pow(1 - t, 4);
          const v = target * eased;
          el.textContent = prefix + v.toFixed(decimal) + suffix;
          if (t < 1) requestAnimationFrame(frame);
          else el.textContent = raw;
        };
        requestAnimationFrame(frame);
      });
    }, { threshold: .65 });
    values.forEach(el => io.observe(el));
  }

  function installTilt() {
    if (!finePointer || reduceMotion || !fullMotion) return;
    document.querySelectorAll('.fd-benefit, .fd-product-card, .fd-card-hover, .fd-hero-art').forEach(el => {
      el.classList.add('fd-tilt-ready');
      FDMotion.pointer(el, (r, clientX, clientY) => {
        const x = (clientX - r.left) / Math.max(1, r.width);
        const y = (clientY - r.top) / Math.max(1, r.height);
        el.style.setProperty('--fd-tilt-x', `${((.5 - y) * 6.4).toFixed(2)}deg`);
        el.style.setProperty('--fd-tilt-y', `${((x - .5) * 7.2).toFixed(2)}deg`);
        el.style.setProperty('--fd-light-x', `${(x * 100).toFixed(1)}%`);
        el.style.setProperty('--fd-light-y', `${(y * 100).toFixed(1)}%`);
        if (el.classList.contains('fd-hero-art')) {
          el.style.setProperty('--fd-art-x', `${(x * 100).toFixed(1)}%`);
          el.style.setProperty('--fd-art-y', `${(y * 100).toFixed(1)}%`);
        }
      }, () => {
        el.style.setProperty('--fd-tilt-x', '0deg');
        el.style.setProperty('--fd-tilt-y', '0deg');
        el.style.setProperty('--fd-light-x', '50%');
        el.style.setProperty('--fd-light-y', '50%');
      });
    });
  }

  function installMagnetism() {
    if (!finePointer || reduceMotion || liteMotion) return;
    document.querySelectorAll('.btn, .fd-language-trigger, .fd-nav-language-btn').forEach(el => {
      el.classList.add('fd-magnetic');
      FDMotion.pointer(el, (r, clientX, clientY) => {
        const dx = clientX - (r.left + r.width / 2);
        const dy = clientY - (r.top + r.height / 2);
        el.style.transform = `translate(${(dx * .075).toFixed(1)}px, ${(dy * .10).toFixed(1)}px)`;
      }, () => { el.style.transform = ''; });
    });
  }

  function installCursorAura() {
    if (!finePointer || reduceMotion || !fullMotion) return;
    const aura = document.createElement('div');
    aura.className = 'fd-cursor-aura';
    aura.setAttribute('aria-hidden', 'true');
    body.appendChild(aura);
    let tx = -999, ty = -999, x = tx, y = ty, raf = 0;
    const stop = () => { cancelAnimationFrame(raf); raf = 0; };
    const frame = () => {
      raf = 0;
      if (document.hidden || !aura.isConnected) return;
      x += (tx - x) * .12;
      y += (ty - y) * .12;
      // Below the existing 0.1px output precision there is no visible movement.
      const settled = Math.abs(tx - x) < .01 && Math.abs(ty - y) < .01;
      if (settled) { x = tx; y = ty; }
      aura.style.setProperty('--fd-cursor-x', `${x.toFixed(1)}px`);
      aura.style.setProperty('--fd-cursor-y', `${y.toFixed(1)}px`);
      if (!settled) raf = requestAnimationFrame(frame);
    };
    const wake = () => { if (!raf && !document.hidden) raf = requestAnimationFrame(frame); };
    window.addEventListener('pointermove', e => { tx = e.clientX; ty = e.clientY; wake(); }, { passive: true });
    window.addEventListener('blur', () => { aura.style.opacity = '0'; stop(); });
    window.addEventListener('focus', () => { aura.style.opacity = ''; wake(); });
    document.addEventListener('visibilitychange', () => document.hidden ? stop() : wake());
    window.addEventListener('pagehide', stop);
    window.addEventListener('pageshow', wake);
  }

  function installHeroInteraction() {
    const hero = document.querySelector('.fd-route-views-landing .fd-hero');
    if (!hero || reduceMotion) return;
    const lens = hero.querySelector('.fd-hero-lens');
    if (!lens) return;
    FDMotion.pointer(hero, (r, x, y) => {
      lens.style.setProperty('--fd-mouse-x', `${((x - r.left) / Math.max(1, r.width) * 100).toFixed(1)}%`);
      lens.style.setProperty('--fd-mouse-y', `${((y - r.top) / Math.max(1, r.height) * 100).toFixed(1)}%`);
    });
  }

  function installParallax() {
    if (reduceMotion) return;
    const hero = document.querySelector('.fd-route-views-landing .fd-hero');
    if (!hero) return;
    const stage = hero.querySelector('.fd-crop-viz');
    const chip = hero.querySelector('.fd-hero-chip');
    let ticking = false;
    let active = true;
    const sync = () => {
      ticking = false;
      if (!active) return;
      const y = Math.min(window.innerHeight, Math.max(0, window.scrollY));
      if (stage) stage.style.transform = `translate3d(0, ${(y * .055).toFixed(1)}px, 0)`;
      if (chip) chip.style.transform = `translate3d(0, ${(y * .025).toFixed(1)}px, 0)`;
    };
    const request = () => { if (active && !ticking) { ticking = true; requestAnimationFrame(sync); } };
    window.addEventListener('scroll', request, { passive: true });
    if ('IntersectionObserver' in window) {
      const io = new IntersectionObserver(entries => {
        active = !!entries[0]?.isIntersecting;
        if (active) request();
      }, { rootMargin: '140px 0px' });
      io.observe(hero);
    }
  }


  function installEnergyDots() {
    const hero = document.querySelector('.fd-route-views-landing .fd-hero');
    if (!hero || reduceMotion || hero.querySelector('.fd-hero-energy-dot')) return;
    const count = liteMotion ? 7 : (fullMotion ? 22 : 12);
    for (let i = 0; i < count; i += 1) {
      const dot = document.createElement('span');
      dot.className = 'fd-hero-energy-dot';
      dot.setAttribute('aria-hidden', 'true');
      dot.style.left = `${8 + Math.random() * 84}%`;
      dot.style.top = `${32 + Math.random() * 62}%`;
      dot.style.setProperty('--fd-dot-speed', `${6 + Math.random() * 8}s`);
      dot.style.setProperty('--fd-dot-x', `${-55 + Math.random() * 110}px`);
      dot.style.animationDelay = `${-Math.random() * 10}s`;
      hero.appendChild(dot);
    }
  }

  function installRippleFeedback() {
    document.querySelectorAll('.fd-route-views-landing .btn, .fd-route-views-landing .fd-language-trigger, .fd-route-views-landing .fd-nav-language-btn').forEach(el => {
      if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
      el.style.overflow = 'hidden';
      el.addEventListener('pointerdown', ev => {
        if (reduceMotion) return;
        const rect = el.getBoundingClientRect();
        const ripple = document.createElement('span');
        ripple.className = 'fd-click-ripple';
        ripple.style.left = `${ev.clientX - rect.left}px`;
        ripple.style.top = `${ev.clientY - rect.top}px`;
        ripple.setAttribute('aria-hidden', 'true');
        el.appendChild(ripple);
        ripple.addEventListener('animationend', () => ripple.remove(), { once:true });
      });
    });
  }

  function installHeroParticles() {
    const hero = document.querySelector('.fd-route-views-landing .fd-hero');
    if (!hero || reduceMotion) return;
    let canvas = hero.querySelector('.fd-cinematic-canvas');
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.className = 'fd-cinematic-canvas';
      canvas.setAttribute('aria-hidden', 'true');
      hero.prepend(canvas);
    }
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;
    let w = 0, h = 0, dpr = 1, nodes = [], raf = 0;
    let pageVisible = !document.hidden, inViewport = true, running = false;
    const pointer = { x: .55, y: .42 };

    function resize() {
      const rect = hero.getBoundingClientRect();
      w = Math.max(320, rect.width);
      h = Math.max(420, rect.height);
      dpr = Math.min(fullMotion ? 2 : 1.35, window.devicePixelRatio || 1);
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = liteMotion ? Math.max(18, Math.min(30, Math.round(w / 30))) : (fullMotion ? Math.max(42, Math.min(95, Math.round(w / 16))) : Math.max(28, Math.min(52, Math.round(w / 22))));
      nodes = Array.from({ length: count }, (_, i) => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - .5) * .16,
        vy: (Math.random() - .5) * .14,
        r: .6 + Math.random() * 1.45,
        a: .11 + Math.random() * .36,
        phase: Math.random() * Math.PI * 2,
        green: i % 5 !== 0
      }));
    }

    function draw(t) {
      if (!pageVisible || !inViewport) { running = false; raf = 0; return; }
      running = true;
      ctx.clearRect(0, 0, w, h);
      const px = pointer.x * w, py = pointer.y * h;
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        n.x += n.vx; n.y += n.vy;
        if (n.x < -20) n.x = w + 20; else if (n.x > w + 20) n.x = -20;
        if (n.y < -20) n.y = h + 20; else if (n.y > h + 20) n.y = -20;
        const dxp = n.x - px, dyp = n.y - py;
        const dp2 = dxp * dxp + dyp * dyp;
        if (dp2 < 125 * 125 && dp2 > 1) {
          const dp = Math.sqrt(dp2);
          n.x += (dxp / dp) * .17;
          n.y += (dyp / dp) * .17;
        }
        const pulse = .78 + Math.sin(t * .0012 + n.phase) * .22;
        ctx.beginPath();
        ctx.fillStyle = n.green ? `rgba(148,255,184,${n.a * pulse})` : `rgba(225,255,128,${n.a * pulse})`;
        ctx.arc(n.x, n.y, n.r * pulse, 0, Math.PI * 2);
        ctx.fill();
      }
      // only connect a bounded number of neighboring pairs for performance
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < Math.min(nodes.length, i + 9); j++) {
          const b = nodes[j];
          const dx = a.x - b.x, dy = a.y - b.y;
          const d2 = dx * dx + dy * dy;
          if (d2 < 118 * 118) {
            const d = Math.sqrt(d2);
            ctx.beginPath();
            ctx.strokeStyle = `rgba(121,240,163,${(1 - d / 118) * .085})`;
            ctx.lineWidth = .6;
            ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
          }
        }
      }
      raf = requestAnimationFrame(draw);
    }

    const ensureRunning = () => {
      if (pageVisible && inViewport && !running) {
        running = true;
        raf = requestAnimationFrame(draw);
      }
    };
    const stopIfIdle = () => {
      if ((!pageVisible || !inViewport) && raf) {
        cancelAnimationFrame(raf);
        raf = 0;
        running = false;
      }
    };

    FDMotion.pointer(hero, (r, x, y) => {
      pointer.x = Math.max(0, Math.min(1, (x - r.left) / Math.max(1, r.width)));
      pointer.y = Math.max(0, Math.min(1, (y - r.top) / Math.max(1, r.height)));
    });
    document.addEventListener('visibilitychange', () => {
      pageVisible = !document.hidden;
      if (pageVisible) ensureRunning(); else stopIfIdle();
    });
    if ('IntersectionObserver' in window) {
      const heroVisibility = new IntersectionObserver(entries => {
        inViewport = !!entries[0]?.isIntersecting;
        if (inViewport) ensureRunning(); else stopIfIdle();
      }, { rootMargin: '180px 0px' });
      heroVisibility.observe(hero);
    }
    window.addEventListener('resize', resize, { passive: true });
    window.addEventListener('pagehide', () => {
      if (raf) cancelAnimationFrame(raf);
      raf = 0; running = false;
    });
    window.addEventListener('pageshow', ensureRunning);
    resize();
    ensureRunning();
  }

  function installIntroLoader() {
    if (!body.classList.contains('fd-route-views-landing') || reduceMotion || document.querySelector('.fd-cine-loader')) return;
    const loader = document.createElement('div');
    loader.className = 'fd-cine-loader';
    loader.setAttribute('aria-hidden', 'true');
    loader.innerHTML = '<div class="fd-cine-loader-core"><span class="fd-cine-loader-ring"></span><span class="fd-cine-loader-ring r2"></span><div class="fd-cine-loader-brand">Farm to future<b>FarmDirect</b></div><span class="fd-cine-loader-bar"></span></div>';
    body.appendChild(loader);
    requestAnimationFrame(() => requestAnimationFrame(() => {
      window.setTimeout(() => loader.classList.add('is-done'), 460);
      window.setTimeout(() => loader.remove(), 1280);
    }));
  }

  function installHeroDecor() {
    const hero = document.querySelector('.fd-route-views-landing .fd-hero');
    if (!hero) return;
    if (!hero.querySelector('.fd-hero-wordmark')) {
      const mark = document.createElement('div');
      mark.className = 'fd-hero-wordmark';
      mark.setAttribute('aria-hidden','true');
      mark.textContent = 'FARM DIRECT • FARM DIRECT • FARM DIRECT';
      hero.prepend(mark);
    }
    if (!hero.querySelector('.fd-hero-lens')) {
      const lens = document.createElement('div');
      lens.className = 'fd-hero-lens';
      lens.setAttribute('aria-hidden','true');
      hero.appendChild(lens);
    }
  }

  function installKineticBand() {
    const hero = document.querySelector('.fd-route-views-landing .fd-hero');
    if (!hero || document.querySelector('.fd-kinetic-band')) return;
    const band = document.createElement('div');
    band.className = 'fd-kinetic-band';
    band.setAttribute('aria-hidden','true');
    const unit = '<span>FARM FRESH</span><i></i><span>DIRECT MARKET</span><i></i><span>AI LOGISTICS</span><i></i><span>FAIR PRICE</span><i></i><span>INDIA</span><i></i>';
    band.innerHTML = `<div class="fd-kinetic-track">${unit}${unit}${unit}${unit}</div>`;
    hero.insertAdjacentElement('afterend', band);
  }

  function installPressPhysics() {
    document.querySelectorAll('.fd-route-views-landing .btn, .fd-route-views-landing .fd-language-option, .fd-route-views-landing .fd-nav-language-btn').forEach(el => el.classList.add('fd-cine-press'));
    document.querySelectorAll('.fd-route-views-landing .fd-benefit, .fd-route-views-landing .fd-product-card, .fd-route-views-landing .fd-card-hover').forEach(el => el.classList.add('fd-cine-spring'));
  }

  function installSectionSpotlights() {
    const sections = [...document.querySelectorAll('.fd-route-views-landing main > section:not(.fd-hero)')];
    if (!sections.length) return;
    const activeSections = new Set(sections);
    const scrollKey = {};
    const requestSync = () => FDMotion.schedule(scrollKey, measure => {
      const vh = Math.max(1, window.innerHeight);
      return [...activeSections].map(section => {
        const r = measure(section);
        return [section, Math.max(0, Math.min(1, (vh - r.top) / Math.max(vh + r.height, 1)))];
      });
    }, values => values.forEach(([section, p]) => {
      section.style.setProperty('--fd-section-progress', p.toFixed(4));
      section.style.setProperty('--fd-section-shift', `${((.5 - p) * 22).toFixed(1)}px`);
      section.style.setProperty('--fd-section-scan', `${(p * 88).toFixed(1)}%`);
    }));
    if ('IntersectionObserver' in window) {
      activeSections.clear();
      const io = new IntersectionObserver(entries => {
        entries.forEach(entry => entry.isIntersecting ? activeSections.add(entry.target) : activeSections.delete(entry.target));
        requestSync();
      }, { rootMargin: '45% 0px' });
      sections.forEach(section => io.observe(section));
    }
    requestSync();
    window.addEventListener('scroll', requestSync, { passive: true });
    window.addEventListener('resize', requestSync, { passive: true });
    if (!finePointer || reduceMotion) return;
    sections.forEach(section => FDMotion.pointer(section, (r, x, y) => {
      section.style.setProperty('--fd-section-x', `${((x-r.left)/Math.max(1,r.width)*100).toFixed(1)}%`);
      section.style.setProperty('--fd-section-y', `${((y-r.top)/Math.max(1,r.height)*100).toFixed(1)}%`);
    }, () => {
      section.style.setProperty('--fd-section-x', '50%');
      section.style.setProperty('--fd-section-y', '50%');
    }));
  }

  function installGlobalTrail() {
    if (!body.classList.contains('fd-route-views-landing') || !finePointer || reduceMotion || !fullMotion) return;
    const canvas = document.createElement('canvas');
    canvas.className = 'fd-cine-trail-canvas';
    canvas.setAttribute('aria-hidden','true');
    body.appendChild(canvas);
    const ctx = canvas.getContext('2d', {alpha:true});
    if (!ctx) { canvas.remove(); return; }
    let w=0,h=0,dpr=1,raf=0,visible=!document.hidden;
    const pts=[];
    let px=-200,py=-200,last=0;
    const resize=()=>{
      w=Math.max(320,window.innerWidth);h=Math.max(320,window.innerHeight);dpr=Math.min(1.6,window.devicePixelRatio||1);
      canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);canvas.style.width=`${w}px`;canvas.style.height=`${h}px`;ctx.setTransform(dpr,0,0,dpr,0,0);
    };
    window.addEventListener('pointermove',e=>{
      px=e.clientX;py=e.clientY;
      const now=performance.now();
      if(now-last>12){pts.push({x:px,y:py,life:1,size:3+Math.random()*3});last=now;if(pts.length>28)pts.shift();}
      wake();
    },{passive:true});
    const draw=()=>{
      raf=0;
      if(!visible)return;
      ctx.clearRect(0,0,w,h);
      for(let i=pts.length-1;i>=0;i--){
        const p=pts[i];p.life-=.035;p.size*=.985;
        if(p.life<=0){pts.splice(i,1);continue;}
        const g=ctx.createRadialGradient(p.x,p.y,0,p.x,p.y,p.size*5);
        g.addColorStop(0,`rgba(190,255,210,${p.life*.42})`);g.addColorStop(.3,`rgba(72,237,137,${p.life*.18})`);g.addColorStop(1,'rgba(72,237,137,0)');
        ctx.fillStyle=g;ctx.beginPath();ctx.arc(p.x,p.y,p.size*5,0,Math.PI*2);ctx.fill();
      }
      if(pts.length>2){
        ctx.beginPath();ctx.moveTo(pts[0].x,pts[0].y);
        for(let i=1;i<pts.length;i++)ctx.lineTo(pts[i].x,pts[i].y);
        ctx.strokeStyle='rgba(123,255,170,.08)';ctx.lineWidth=1;ctx.stroke();
      }
      if(pts.length)raf=requestAnimationFrame(draw);
    };
    const wake=()=>{if(visible&&pts.length&&!raf)raf=requestAnimationFrame(draw);};
    const stop=()=>{cancelAnimationFrame(raf);raf=0;};
    document.addEventListener('visibilitychange',()=>{visible=!document.hidden;if(visible)wake();else stop();});
    window.addEventListener('resize',resize,{passive:true});
    window.addEventListener('pagehide',stop);
    window.addEventListener('pageshow',wake);
    resize();
  }

})();

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

(function () {
  'use strict';

  function addParticles(container, count) {
    if (!container || container.querySelector('.fd-motion-particle-field')) return;
    const field = document.createElement('div');
    field.className = 'fd-motion-particle-field';
    for (let i = 0; i < count; i += 1) {
      const p = document.createElement('span');
      p.className = 'fd-motion-particle';
      p.style.left = `${Math.random() * 100}%`;
      p.style.top = `${55 + Math.random() * 40}%`;
      p.style.setProperty('--x', `${(Math.random() * 80) - 40}px`);
      p.style.setProperty('--d', `${10 + Math.random() * 10}s`);
      p.style.animationDelay = `${Math.random() * -12}s`;
      p.style.transform = `scale(${0.7 + Math.random() * 1.2})`;
      field.appendChild(p);
    }
    container.prepend(field);
  }

  function bindCardParallax(card) {
    if (!card || card.dataset.v11Bound === '1') return;
    card.dataset.v11Bound = '1';
    const media = card.querySelector('.fd-product-img-v9');
    const mark = card.querySelector('[data-crop-mark]');
    FDMotion.pointer(card, (rect, latestX, latestY) => {
      if (!rect.width || !rect.height) return;
      const x = latestX - rect.left;
      const y = latestY - rect.top;
      const px = `${(x / rect.width) * 100}%`;
      const py = `${(y / rect.height) * 100}%`;
      card.style.setProperty('--fd-px', px);
      card.style.setProperty('--fd-py', py);
      const rx = ((y / rect.height) - 0.5) * -6;
      const ry = ((x / rect.width) - 0.5) * 8;
      card.style.transform = `translateY(-9px) perspective(1000px) rotateX(${rx}deg) rotateY(${ry}deg) scale(1.012)`;
      if (media) media.style.transform = `translate3d(${ry * -0.5}px, ${rx * 0.5}px, 0)`;
      if (mark) mark.style.transform = `translate3d(${ry * 0.35}px, ${rx * -0.25}px, 0)`;
    }, () => {
      card.style.removeProperty('--fd-px');
      card.style.removeProperty('--fd-py');
      card.style.transform = '';
      if (media) media.style.transform = '';
      if (mark) mark.style.transform = '';
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    addParticles(document.querySelector('.fd-market-stage'), 18);
    addParticles(document.querySelector('.fd-product-hero-art'), 12);
    document.querySelectorAll('.fd-product-card-v9').forEach(bindCardParallax);
  });
})();

(() => {
  'use strict';
  if (window.__FD_FINAL_V15__) return;
  window.__FD_FINAL_V15__ = true;

  const root = document.documentElement;
  const body = document.body;
  const scriptRoot = window.SCRIPT_ROOT || '';
  const qs = (sel, scope = document) => scope.querySelector(sel);
  const qsa = (sel, scope = document) => Array.from(scope.querySelectorAll(sel));

  function toast(title, detail = '', icon = 'bi-check-circle') {
    let stack = qs('.fd-final-toast-stack');
    if (!stack) {
      stack = document.createElement('div');
      stack.className = 'fd-final-toast-stack';
      document.body.appendChild(stack);
    }
    const el = document.createElement('div');
    el.className = 'fd-final-toast';
    el.innerHTML = `<i class="bi ${icon}"></i><div><b></b><small></small></div>`;
    qs('b', el).textContent = title;
    qs('small', el).textContent = detail;
    stack.appendChild(el);
    window.setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(8px)';
      window.setTimeout(() => el.remove(), 240);
    }, 3200);
  }
  window.fdFinalToast = toast;

  function setConnectivity() {
    const bar = qs('#fd-final-network-bar');
    if (!bar) return;
    const online = navigator.onLine;
    bar.classList.toggle('is-visible', !online);
    if (online && bar.dataset.wasOffline === '1') toast('Connection restored', 'Official market sources can sync again.', 'bi-wifi');
    if (!online) bar.dataset.wasOffline = '1';
  }

  let statusInFlight = false;

  async function refreshMarketStatus(silent = true) {
    const pill = qs('#fd-final-system-pill');
    if (!pill || statusInFlight || (silent && document.hidden)) return;
    if (!navigator.onLine) {
      pill.className = 'fd-final-system-pill is-offline';
      pill.innerHTML = '<i class="bi bi-wifi-off"></i><span>Offline · cache</span>';
      return;
    }
    statusInFlight = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 9000);
    try {
      const response = await fetch(`${scriptRoot}/api/market/status`, {headers: {'Accept':'application/json'}, cache:'no-store', signal: controller.signal});
      if (!response.ok) throw new Error('status unavailable');
      const data = await response.json();
      const providers = Array.isArray(data.providers) ? data.providers : [];
      const onlineProvider = providers.find(p => ['online','reachable-no-feed','reachable-no-match'].includes(String(p.status || '').toLowerCase()));
      const successes = providers.filter(p => p.last_success_at);
      if (successes.length || Number(data.cached_rows || 0) > 0) {
        pill.className = `fd-final-system-pill ${successes.length ? 'is-online' : 'is-cached'}`;
        pill.innerHTML = `<i class="bi ${successes.length ? 'bi-broadcast-pin' : 'bi-database-check'}"></i><span>${successes.length ? 'Mandi sync ready' : 'Mandi cache ready'}</span>`;
      } else if (onlineProvider) {
        pill.className = 'fd-final-system-pill is-cached';
        pill.innerHTML = '<i class="bi bi-arrow-repeat"></i><span>Sources reachable</span>';
      } else {
        pill.className = 'fd-final-system-pill is-cached';
        pill.innerHTML = '<i class="bi bi-shield-check"></i><span>Cache fallback</span>';
      }
      pill.title = `${data.cached_crops || 0} crops cached · ${data.cached_rows || 0} verified rows`;
    } catch (err) {
      pill.className = 'fd-final-system-pill is-cached';
      pill.innerHTML = '<i class="bi bi-database-check"></i><span>Local cache</span>';
      if (!silent) toast('Market status unavailable', 'The local FarmDirect database is still usable.', 'bi-database');
    } finally {
      clearTimeout(timeout);
      statusInFlight = false;
    }
  }

  function initActiveNav() {
    const path = window.location.pathname.replace(/\/$/, '') || '/';
    qsa('a[href]').forEach(a => {
      try {
        const target = new URL(a.href, location.href).pathname.replace(/\/$/, '') || '/';
        const active = target !== '/' ? path === target || path.startsWith(`${target}/`) : path === '/';
        if (active && (a.closest('.fd-navbar') || a.closest('.fd-final-mobile-nav'))) a.classList.add(a.closest('.fd-final-mobile-nav') ? 'is-active' : 'fd-final-active');
      } catch (_) {}
    });
  }

  function initRouteLoader() {
    const loader = qs('#fd-final-loader');
    if (!loader) return;
    document.addEventListener('click', ev => {
      const a = ev.target.closest('a[href]');
      if (!a || a.target || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
      const url = new URL(a.href, location.href);
      if (url.origin !== location.origin || url.hash || a.hasAttribute('download')) return;
      loader.classList.add('is-loading');
    });
    window.addEventListener('pageshow', () => loader.classList.remove('is-loading'));
  }

  function initTopButton() {
    const btn = qs('#fd-final-top');
    if (!btn) return;
    let topRaf = 0;
    const onScroll = () => {
      topRaf = 0;
      btn.classList.toggle('is-visible', window.scrollY > 520);
    };
    const requestTopSync = () => { if (!topRaf) topRaf = requestAnimationFrame(onScroll); };
    window.addEventListener('scroll', requestTopSync, {passive:true});
    btn.addEventListener('click', () => window.scrollTo({top:0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'}));
    onScroll();
  }

  function initLift() {
    qsa('.fd-card,.fd-stat').forEach(el => {
      if (!el.closest('.ivr-phone') && !el.classList.contains('fd-product-card-v9')) el.classList.add('fd-final-hover-lift');
    });
  }

  function initPWA() {
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => navigator.serviceWorker.register(`${scriptRoot}/sw.js`).catch(() => {}));
    }
    let deferred = null;
    const prompt = qs('#fd-final-install');
    const install = qs('#fd-final-install-btn');
    const close = qs('#fd-final-install-close');
    window.addEventListener('beforeinstallprompt', event => {
      event.preventDefault();
      deferred = event;
      if (prompt) prompt.classList.add('is-visible');
    });
    if (install) install.addEventListener('click', async () => {
      if (!deferred) return;
      prompt?.classList.remove('is-visible');
      await deferred.prompt();
      const choice = await deferred.userChoice;
      if (choice.outcome === 'accepted') toast('FarmDirect installed', 'You can open it like an app from your home screen.', 'bi-phone');
      deferred = null;
    });
    if (close) close.addEventListener('click', () => prompt?.classList.remove('is-visible'));
  }

  function initTouchFeedback() {
    document.addEventListener('pointerdown', ev => {
      const target = ev.target.closest('.btn,.ivr-key,.fd-demo-account,.fd-final-mobile-nav a');
      if (!target) return;
      target.animate([{transform:'scale(1)'},{transform:'scale(.975)'},{transform:'scale(1)'}], {duration:210,easing:'ease-out'});
    });
  }

  function initMarketSyncForms() {
    qsa('.fd-market-sync-form').forEach(form => {
      form.addEventListener('submit', () => {
        const btn = qs('button[type="submit"]', form);
        if (!btn) return;
        btn.disabled = true;
        btn.dataset.original = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Syncing providers…';
      });
    });
  }

  function initQuickDiagnostics() {
    const pill = qs('#fd-final-system-pill');
    if (!pill) return;
    pill.addEventListener('click', () => refreshMarketStatus(false));
    pill.style.cursor = 'pointer';
  }

  body.classList.add('fd-final-page-enter');
  setConnectivity();
  window.addEventListener('online', () => { setConnectivity(); refreshMarketStatus(false); });
  window.addEventListener('offline', setConnectivity);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refreshMarketStatus(true); });
  initActiveNav();
  initRouteLoader();
  initTopButton();
  initLift();
  initPWA();
  initTouchFeedback();
  initMarketSyncForms();
  initQuickDiagnostics();
  refreshMarketStatus(true);
  window.setInterval(() => refreshMarketStatus(true), 60000);
})();
