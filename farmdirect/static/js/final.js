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

  async function refreshMarketStatus(silent = true) {
    const pill = qs('#fd-final-system-pill');
    if (!pill) return;
    if (!navigator.onLine) {
      pill.className = 'fd-final-system-pill is-offline';
      pill.innerHTML = '<i class="bi bi-wifi-off"></i><span>Offline · cache</span>';
      return;
    }
    try {
      const response = await fetch(`${scriptRoot}/api/market/status`, {headers: {'Accept':'application/json'}, cache:'no-store'});
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
    const onScroll = () => btn.classList.toggle('is-visible', window.scrollY > 520);
    window.addEventListener('scroll', onScroll, {passive:true});
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
