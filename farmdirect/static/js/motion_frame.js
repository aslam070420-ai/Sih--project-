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
