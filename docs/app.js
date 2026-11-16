const menuButton = document.querySelector('.menu-toggle');
const mainNav = document.querySelector('#main-nav');

menuButton.addEventListener('click', () => {
  const isOpen = menuButton.getAttribute('aria-expanded') === 'true';
  menuButton.setAttribute('aria-expanded', String(!isOpen));
  mainNav.classList.toggle('is-open', !isOpen);
});

mainNav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
  menuButton.setAttribute('aria-expanded', 'false');
  mainNav.classList.remove('is-open');
}));

const revealObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('is-visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });
document.querySelectorAll('.reveal').forEach(element => revealObserver.observe(element));

const tiltCard = document.querySelector('[data-tilt]');
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
if (tiltCard && window.matchMedia('(pointer: fine)').matches && !motionPreference.matches) {
  const resetTilt = () => {
    tiltCard.style.setProperty('--tilt-x', '0deg');
    tiltCard.style.setProperty('--tilt-y', '0deg');
  };
  tiltCard.addEventListener('pointermove', event => {
    const bounds = tiltCard.getBoundingClientRect();
    const x = (event.clientX - bounds.left) / bounds.width - 0.5;
    const y = (event.clientY - bounds.top) / bounds.height - 0.5;
    tiltCard.style.setProperty('--tilt-x', `${-y * 2}deg`);
    tiltCard.style.setProperty('--tilt-y', `${x * 3}deg`);
  });
  tiltCard.addEventListener('pointerleave', resetTilt);
  motionPreference.addEventListener('change', event => {
    if (event.matches) resetTilt();
  });
}

document.querySelector('#year').textContent = new Date().getFullYear();
