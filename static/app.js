const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];

// theme toggle
$('#theme')?.addEventListener('click', () => {
  const d = document.documentElement, n = d.dataset.theme === 'dark' ? 'light' : 'dark';
  d.dataset.theme = n; try { localStorage.setItem('theme', n); } catch (e) {}
});

// navbar
const nav = $('#nav');
const onScroll = () => nav.classList.toggle('scrolled', scrollY > 8);
addEventListener('scroll', onScroll, { passive: true }); onScroll();
$('#burger')?.addEventListener('click', e => e.currentTarget.setAttribute('aria-expanded', $('#links').classList.toggle('open')));
$('#avatar')?.addEventListener('click', e => { e.stopPropagation(); $('#menu').classList.toggle('open'); });
document.addEventListener('click', () => $('#menu')?.classList.remove('open'));

// reveal on scroll
const io = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
}), { threshold: .12 });
$$('.reveal, .meter').forEach(el => io.observe(el));

// count-up numbers
$$('[data-count]').forEach(el => {
  const end = +el.dataset.count, suf = el.dataset.suffix || '', t0 = performance.now();
  const tick = t => { const p = Math.min((t - t0) / 900, 1); el.textContent = Math.round(end * (1 - Math.pow(1 - p, 3))) + suf; if (p < 1) requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
});

// toasts
window.toast = (msg, type = 'info') => {
  let box = $('.toasts'); if (!box) { box = document.createElement('div'); box.className = 'toasts'; document.body.append(box); }
  const t = document.createElement('div'); t.className = 'toast ' + type; t.textContent = msg; box.append(t);
  setTimeout(() => t.classList.add('hide'), 4500); setTimeout(() => t.remove(), 5000);
};
$$('.toast').forEach(t => setTimeout(() => t.classList.add('hide'), 4500));
$$('[data-google-off]').forEach(b => b.addEventListener('click', () =>
  toast('Google sign-in is not set up yet. Add your Firebase keys to .env (see README).', 'warn')));

// loading overlay while the AI builds the plan
const msgs = ['Reading your skills...', 'Matching roles with TensorFlow...', 'Writing your learning path...', 'Almost there...'];
$$('form[data-loading]').forEach(f => f.addEventListener('submit', () => {
  const l = $('#loader'); if (!l) return; l.classList.add('show'); let i = 0;
  setInterval(() => { i = (i + 1) % msgs.length; $('#loader p').textContent = msgs[i]; }, 1800);
}));

// skill chips
$$('.chip[data-target]').forEach(c => c.addEventListener('click', () => {
  const t = $(c.dataset.target), v = c.dataset.v;
  let list = t.value.split(',').map(s => s.trim()).filter(Boolean);
  const i = list.findIndex(x => x.toLowerCase() === v.toLowerCase());
  if (i > -1) { list.splice(i, 1); c.classList.remove('on'); } else { list.push(v); c.classList.add('on'); }
  t.value = list.join(', ');
}));

// plan page: tick steps
function confetti() {
  const cols = ['#0f766e', '#14b8a6', '#f59e0b', '#fb7185', '#6366f1'];
  for (let i = 0; i < 70; i++) {
    const s = document.createElement('span'); s.className = 'confetti';
    s.style.left = Math.random() * 100 + 'vw'; s.style.background = cols[i % cols.length];
    s.style.animationDuration = 2 + Math.random() * 2.2 + 's'; s.style.animationDelay = Math.random() * .6 + 's';
    document.body.append(s); setTimeout(() => s.remove(), 5500);
  }
}
$$('.step-box').forEach(box => box.addEventListener('change', async () => {
  const r = await fetch('/step/' + box.dataset.id + '/toggle', { method: 'POST' });
  if (!r.ok) { box.checked = !box.checked; return toast('Could not save. Please log in again.', 'error'); }
  const d = await r.json(), li = box.closest('.tl-item');
  li.classList.toggle('done', !!d.done);
  $('.when', li).textContent = d.done ? ' · done ' + d.done_at : '';
  $('#ring')?.style.setProperty('--pct', d.progress);
  if ($('#pct')) $('#pct').textContent = d.progress + '%';
  if (d.progress === 100 && d.done) { confetti(); toast('Amazing! You completed your whole path!', 'success'); }
}));
