/**
 * GOODWARE — Menu do usuário (compartilhado por painel.html e analisar.html)
 */

(function () {
  const userMenu = document.getElementById('userMenu');
  const trigger = document.getElementById('userMenuTrigger');
  if (!userMenu || !trigger) return;

  function setOpen(open) {
    userMenu.classList.toggle('is-open', open);
    trigger.setAttribute('aria-expanded', String(open));
  }

  trigger.addEventListener('click', () => {
    setOpen(!userMenu.classList.contains('is-open'));
  });

  document.addEventListener('click', (event) => {
    if (!userMenu.contains(event.target)) setOpen(false);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') setOpen(false);
  });
})();
