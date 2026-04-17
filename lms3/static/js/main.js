// ── Theme ──────────────────────────────────────────────────
const THEME_KEY = 'mr-lms-theme';

function applyTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  localStorage.setItem(THEME_KEY, t);
  document.querySelectorAll('.theme-icon').forEach(el => el.textContent = t === 'dark' ? '☀️' : '🌙');
  document.querySelectorAll('.theme-label').forEach(el => el.textContent = t === 'dark' ? 'Light' : 'Dark');
}

function toggleTheme() {
  const cur = document.documentElement.getAttribute('data-theme') || 'light';
  applyTheme(cur === 'dark' ? 'light' : 'dark');
}

(function() { applyTheme(localStorage.getItem(THEME_KEY) || 'light'); })();

// ── Sidebar ────────────────────────────────────────────────
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const ov = document.getElementById('sidebarOverlay');
  if (!sb) return;
  sb.classList.toggle('open');
  if (ov) ov.classList.toggle('show');
}

// ── Flash Dismiss ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Auto-dismiss flashes
  setTimeout(() => {
    document.querySelectorAll('.flash').forEach(el => {
      el.style.transition = 'opacity .5s,transform .5s';
      el.style.opacity = '0'; el.style.transform = 'translateX(20px)';
      setTimeout(() => el.remove(), 500);
    });
  }, 4500);

  // Delete confirms
  document.querySelectorAll('form[data-confirm]').forEach(f => {
    f.addEventListener('submit', e => { if (!confirm(f.dataset.confirm)) e.preventDefault(); });
  });

  // Animate stat numbers
  document.querySelectorAll('.stat-number[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count);
    let cur = 0;
    const step = Math.max(1, Math.ceil(target / 40));
    const iv = setInterval(() => {
      cur = Math.min(cur + step, target);
      el.textContent = cur;
      if (cur >= target) clearInterval(iv);
    }, 25);
  });

  // Progress bars animate in
  document.querySelectorAll('.progress-fill[data-pct]').forEach(el => {
    const pct = el.dataset.pct;
    el.style.width = '0%';
    requestAnimationFrame(() => setTimeout(() => { el.style.width = pct + '%'; }, 100));
  });

  // Quiz timer
  const timerEl = document.getElementById('quizTimer');
  if (timerEl) {
    let secs = parseInt(timerEl.dataset.secs);
    if (secs > 0) {
      const iv = setInterval(() => {
        secs--;
        const m = String(Math.floor(secs / 60)).padStart(2,'0');
        const s = String(secs % 60).padStart(2,'0');
        timerEl.textContent = `${m}:${s}`;
        if (secs <= 60) timerEl.style.color = 'var(--danger)';
        if (secs <= 0) { clearInterval(iv); document.getElementById('examForm')?.submit(); }
      }, 1000);
    }
  }
});

// ── Modal helpers ──────────────────────────────────────────
function openModal(id) { document.getElementById(id)?.classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id)?.classList.add('hidden'); }
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') document.querySelectorAll('.modal-overlay:not(.hidden)').forEach(m => m.classList.add('hidden'));
});
