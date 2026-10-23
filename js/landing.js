/**
 * GOODWARE — Landing page
 * Removido o código de uma versão anterior (abas de instalação e botões
 * de copiar) que apontava para elementos que não existem mais.
 */

(function () {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---------- Revelar seções ao rolar ----------
  const revealItems = document.querySelectorAll('.reveal');

  if (prefersReducedMotion || !('IntersectionObserver' in window)) {
    revealItems.forEach((el) => el.classList.add('visible'));
  } else {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });

    revealItems.forEach((el) => observer.observe(el));
  }

  // ---------- Animação sutil do console do hero ----------
  // Sugere "sistema ativo" sem distrair: leve deslocamento vertical a cada ciclo.
  const codeRows = document.querySelectorAll('.hero-console .code-row code');

  if (!prefersReducedMotion && codeRows.length) {
    setInterval(() => {
      codeRows.forEach((row, i) => {
        row.animate(
          [
            { transform: 'translateY(0)', opacity: 0.7 },
            { transform: 'translateY(-4px)', opacity: 0.95 },
            { transform: 'translateY(0)', opacity: 1 },
          ],
          { duration: 700, delay: i * 40, easing: 'ease-out' }
        );
      });
    }, 4200);
  }

  // ---------- Menu mobile ----------
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.getElementById('primary-nav');

  if (toggle && nav) {
    function setMenu(open) {
      nav.classList.toggle('is-open', open);
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
    }

    toggle.addEventListener('click', () => {
      setMenu(toggle.getAttribute('aria-expanded') !== 'true');
    });

    // Fecha ao escolher um link ou apertar Esc
    nav.addEventListener('click', (event) => {
      if (event.target.closest('a')) setMenu(false);
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') setMenu(false);
    });
  }
})();
