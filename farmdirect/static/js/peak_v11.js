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
    card.addEventListener('pointermove', (ev) => {
      const rect = card.getBoundingClientRect();
      const x = ev.clientX - rect.left;
      const y = ev.clientY - rect.top;
      const px = `${(x / rect.width) * 100}%`;
      const py = `${(y / rect.height) * 100}%`;
      card.style.setProperty('--fd-px', px);
      card.style.setProperty('--fd-py', py);
      const rx = ((y / rect.height) - 0.5) * -6;
      const ry = ((x / rect.width) - 0.5) * 8;
      card.style.transform = `translateY(-9px) perspective(1000px) rotateX(${rx}deg) rotateY(${ry}deg) scale(1.012)`;
      if (media) media.style.transform = `translate3d(${ry * -0.5}px, ${rx * 0.5}px, 0)`;
      if (mark) mark.style.transform = `translate3d(${ry * 0.35}px, ${rx * -0.25}px, 0)`;
    });
    card.addEventListener('pointerleave', () => {
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
