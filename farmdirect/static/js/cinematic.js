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
