/* FarmDirect live official mandi bridge.
   Keeps every marked mandi-price surface converged on the same verified cache
   while refreshing that cache asynchronously from AGMARKNET 2.0.

   Performance rule: no visual effects are changed here. Network work is
   de-duplicated, DOM nodes are indexed once, and DOM writes are batched per
   animation frame so live pricing cannot make scrolling/animation janky. */
(() => {
  'use strict';

  const ROOT = window.SCRIPT_ROOT || '';
  const REFRESH_MS = 10 * 60 * 1000;
  const FOLLOW_UP_MS = [3500, 7500, 14000];
  let nodeIndex = null;
  let syncInFlight = null;
  let refreshTimer = 0;
  const followTimers = new Set();
  const pendingReferences = new Map();
  const appliedReferences = new Map();
  let referenceFrame = 0;
  let refreshCycle = 0;

  function keyFor(crop, state) {
    return `${String(state || '').trim()}\u0000${String(crop || '').trim()}`;
  }

  function buildIndex() {
    appliedReferences.clear();
    const byPair = new Map();
    const byState = new Map();
    document.querySelectorAll('[data-live-market-price][data-live-market-crop]').forEach((el) => {
      const crop = (el.dataset.liveMarketCrop || '').trim();
      const state = (el.dataset.liveMarketState || '').trim();
      if (!crop) return;
      const key = keyFor(crop, state);
      if (!byPair.has(key)) byPair.set(key, []);
      byPair.get(key).push(el);
      if (!byState.has(state)) byState.set(state, new Set());
      byState.get(state).add(crop);
    });
    nodeIndex = { byPair, byState };
    return nodeIndex;
  }

  function index() {
    return nodeIndex || buildIndex();
  }

  function formatNumber(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return '';
    return Number.isInteger(n) ? String(n) : n.toFixed(1).replace(/\.0$/, '');
  }

  function badgeFor(el) {
    const direct = el.closest('[data-live-market-badge]');
    if (direct) return direct;
    const card = el.closest('.fd-card, .fd-product-card-v9, .card');
    return card ? card.querySelector('[data-live-market-badge]') : null;
  }

  function applyReference(crop, requestedState, ref) {
    if (!ref || !Number.isFinite(Number(ref.modal))) return;
    pendingReferences.set(keyFor(crop, requestedState), { crop, requestedState, ref });
    if (referenceFrame) return;
    referenceFrame = requestAnimationFrame(() => {
      referenceFrame = 0;
      const updates = [...pendingReferences.values()];
      pendingReferences.clear();
      updates.forEach(({ crop, requestedState, ref }) => {
        const key = keyFor(crop, requestedState);
        const signature = JSON.stringify(ref);
        if (appliedReferences.get(key) === signature || !index().byPair.has(key)) return;
        appliedReferences.set(key, signature);
        renderReference(crop, requestedState, ref);
      });
    });
  }

  function renderReference(crop, requestedState, ref) {
    if (!ref || !Number.isFinite(Number(ref.modal))) return;
    const idx = index();
    const nodes = idx.byPair.get(keyFor(crop, requestedState || '')) || [];
    if (!nodes.length) return;
    const modal = formatNumber(ref.modal);

    {
      const touchedBadges = new Set();
      nodes.forEach((el) => {
        const suffix = el.dataset.liveMarketSuffix || '';
        const value = (el.dataset.liveMarketFormat || '') === 'number' ? modal : `₹${modal}${suffix}`;
        if (el.textContent !== value) el.textContent = value;

        const badge = badgeFor(el);
        if (badge && !touchedBadges.has(badge)) {
          touchedBadges.add(badge);
          badge.classList.remove('fd-mandi-official', 'fd-mandi-cached', 'fd-mandi-syncing',
                                 'fd-market-source-official', 'fd-market-source-cached');
          badge.classList.add(ref.status === 'official' ? 'fd-mandi-official' : 'fd-mandi-cached');
          const label = badge.querySelector('[data-live-market-label]');
          if (label) {
            label.textContent = ref.is_today ? 'TODAY\'S OFFICIAL MANDI' :
              (ref.status === 'official' ? 'LATEST OFFICIAL MANDI' : 'CACHED OFFICIAL MANDI');
          }
        }
      });

      // Source/date placeholders occur on single-crop detail/intelligence pages.
      if (idx.byPair.size === 1) {
        document.querySelectorAll('[data-live-market-date]').forEach((el) => {
          el.textContent = ref.arrival_date || '—';
        });
        document.querySelectorAll('[data-live-market-source]').forEach((el) => {
          el.textContent = ref.source || ref.provider || 'Official market source';
        });
        document.querySelectorAll('[data-live-market-label]').forEach((el) => {
          if (!el.closest('[data-live-market-badge]')) {
            el.textContent = ref.reporting_label || (ref.is_today ? "TODAY'S OFFICIAL MANDI" : 'LATEST OFFICIAL MANDI');
          }
        });
        document.querySelectorAll('[data-live-market-empty]').forEach((el) => {
          el.hidden = true;
        });
      }

      window.dispatchEvent(new CustomEvent('farmdirect:market-updated', {
        detail: { crop, state: requestedState || '', reference: ref }
      }));
    }
  }

  async function loadGroup(state, crops, refresh) {
    if (!crops.length || !navigator.onLine) return;
    const params = new URLSearchParams({ crops: crops.join(','), refresh: refresh ? '1' : '0', status: '0' });
    if (state) params.set('state', state);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 9000);
    try {
      const response = await fetch(`${ROOT}/api/market/live-batch?${params.toString()}`, {
        headers: { Accept: 'application/json' },
        cache: 'no-store',
        signal: controller.signal
      });
      if (!response.ok) return;
      const data = await response.json();
      Object.entries(data.prices || {}).forEach(([crop, ref]) => applyReference(crop, state, ref));
    } catch (_) {
      // Keep the last verified value already rendered by Flask.
    } finally {
      clearTimeout(timer);
    }
  }

  async function runSync(refresh) {
    const idx = index();
    for (const [state, cropSet] of idx.byState.entries()) {
      if (document.hidden) break;
      const crops = Array.from(cropSet);
      for (let offset = 0; offset < crops.length; offset += 16) {
        if (document.hidden) return;
        await loadGroup(state, crops.slice(offset, offset + 16), refresh);
      }
    }
  }

  function syncAll(refresh) {
    // Never stack duplicate live-price polls; one response updates every matching
    // surface through the central node index.
    if (syncInFlight) return syncInFlight;
    syncInFlight = runSync(refresh).finally(() => { syncInFlight = null; });
    return syncInFlight;
  }

  function later(ms, refresh) {
    const id = setTimeout(() => {
      followTimers.delete(id);
      if (!document.hidden && navigator.onLine) syncAll(refresh);
    }, ms);
    followTimers.add(id);
  }

  function queueRefreshCycle() {
    if (!navigator.onLine || document.hidden) return;
    followTimers.forEach(clearTimeout);
    followTimers.clear();
    const cycle = ++refreshCycle;
    // Paint cached data first; queue external I/O only after the page has had a
    // chance to become interactive. This changes no animation or visual effect.
    syncAll(false).finally(() => {
      const askServerToRefresh = () => {
        if (cycle === refreshCycle && !document.hidden && navigator.onLine) syncAll(true);
      };
      if ('requestIdleCallback' in window) {
        window.requestIdleCallback(askServerToRefresh, { timeout: 1200 });
      } else {
        setTimeout(askServerToRefresh, 250);
      }
    });
    FOLLOW_UP_MS.forEach((ms) => later(ms, false));
  }

  function startPeriodic() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(() => {
      if (!document.hidden && navigator.onLine) syncAll(true);
    }, REFRESH_MS);
  }

  function start() {
    if (!index().byPair.size) return;
    queueRefreshCycle();
    startPeriodic();

    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && navigator.onLine) syncAll(false);
    }, { passive: true });
    window.addEventListener('online', () => queueRefreshCycle(), { passive: true });

    // The Add Produce page can change crop without navigation. Rebuild only the
    // lightweight live-price index, not the rest of the page.
    const cropSelect = document.getElementById('f-crop');
    if (cropSelect) {
      cropSelect.addEventListener('change', () => {
        document.querySelectorAll('[data-live-market-price]').forEach((el) => {
          if (el.closest('.fd-card')) el.dataset.liveMarketCrop = cropSelect.value;
        });
        buildIndex();
        queueRefreshCycle();
      }, { passive: true });
    }
  }

  window.FDMarketLive = {
    sync: () => syncAll(true),
    readCache: () => syncAll(false),
    rebuild: buildIndex
  };

  // The listing form already has a live AI-price fetch. Re-run it after the
  // official mandi cache changes so its derived recommendation stays aligned.
  window.addEventListener('farmdirect:market-updated', (event) => {
    const cropEl = document.getElementById('f-crop');
    if (cropEl && cropEl.value === event.detail?.crop && typeof window.refreshSuggestedPrice === 'function') {
      window.refreshSuggestedPrice();
    }
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
