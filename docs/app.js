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

const previewData = {
  dashboard: {
    heading: '¡Hola, administrador!',
    description: 'Todo listo para tu próxima aventura.',
    label: 'ACTIVIDAD RECIENTE',
    cpu: '18',
    ram: '4.2',
    players: '06',
    lines: ['Servidor iniciado en 4.82s', 'Alex se ha unido al servidor', 'Preparando el mundo «Nexoria»...'],
  },
  console: {
    heading: 'El pulso de tu servidor.',
    description: 'Una consola local, directa y en tiempo real.',
    label: 'CONSOLA DEL SERVIDOR',
    cpu: '23',
    ram: '4.7',
    players: '08',
    lines: ['Done (4.82s)! Type "help" for help.', 'Steve se ha unido al servidor', 'Tiempo de respuesta: 42 ms'],
  },
  files: {
    heading: 'Tu mundo, bien organizado.',
    description: 'Archivos y configuraciones a tu alcance.',
    label: 'ARCHIVOS RECIENTES',
    cpu: '12',
    ram: '3.9',
    players: '04',
    lines: ['plugins / LuckPerms / config.yml', 'server.properties guardado', 'Backup nexoria-world.zip creado'],
  },
};

document.querySelectorAll('.preview-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const data = previewData[tab.dataset.preview];
    document.querySelectorAll('.preview-tab').forEach(item => {
      const active = item === tab;
      item.classList.toggle('is-active', active);
      item.setAttribute('aria-selected', String(active));
    });
    document.querySelector('#preview-heading').textContent = data.heading;
    document.querySelector('#preview-description').textContent = data.description;
    document.querySelector('#preview-tab-label').textContent = data.label;
    document.querySelector('#preview-cpu').innerHTML = `${data.cpu}<span>%</span>`;
    document.querySelector('#preview-ram').innerHTML = `${data.ram}<span> GB</span>`;
    document.querySelector('#preview-players').innerHTML = `${data.players}<span> / 20</span>`;
    ['one', 'two', 'three'].forEach((number, index) => {
      document.querySelector(`#preview-line-${number}`).textContent = data.lines[index];
    });
  });
});

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
if (window.matchMedia('(pointer: fine)').matches && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  tiltCard.addEventListener('pointermove', event => {
    const bounds = tiltCard.getBoundingClientRect();
    const x = (event.clientX - bounds.left) / bounds.width - 0.5;
    const y = (event.clientY - bounds.top) / bounds.height - 0.5;
    tiltCard.style.setProperty('--tilt-x', `${-y * 3}deg`);
    tiltCard.style.setProperty('--tilt-y', `${x * 4}deg`);
  });
  tiltCard.addEventListener('pointerleave', () => {
    tiltCard.style.setProperty('--tilt-x', '0deg');
    tiltCard.style.setProperty('--tilt-y', '0deg');
  });
}

document.querySelector('#year').textContent = new Date().getFullYear();
