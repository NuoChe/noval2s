/** Auth session + modal (V2 demo) */

const AUTH = {
  user: null,

  async init() {
    this.bindModal();
    await this.refresh();
  },

  bindModal() {
    const overlay = document.getElementById('auth-modal');
    const form = document.getElementById('auth-form');
    const closeBtn = overlay?.querySelector('.modal__close');
    const tabs = overlay?.querySelectorAll('.modal__tab');

    document.getElementById('login-open-btn')?.addEventListener('click', () => this.openModal('login'));
    document.getElementById('logout-btn')?.addEventListener('click', () => this.logout());

    closeBtn?.addEventListener('click', () => this.closeModal());
    overlay?.addEventListener('click', (e) => {
      if (e.target === overlay) this.closeModal();
    });

    tabs?.forEach((tab) => {
      tab.addEventListener('click', () => this.setTab(tab.dataset.tab));
    });

    form?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.submit();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !overlay.hidden) this.closeModal();
    });
  },

  setTab(mode) {
    this.mode = mode || 'login';
    document.querySelectorAll('.modal__tab').forEach((t) => {
      t.classList.toggle('modal__tab--active', t.dataset.tab === this.mode);
    });
    document.getElementById('auth-submit-btn').textContent =
      this.mode === 'register' ? '注册' : '登录';
    this.hideError();
  },

  openModal(mode) {
    this.setTab(mode || 'login');
    document.getElementById('auth-modal').hidden = false;
    document.getElementById('auth-email')?.focus();
  },

  closeModal() {
    document.getElementById('auth-modal').hidden = true;
    this.hideError();
  },

  hideError() {
    const el = document.getElementById('auth-error');
    el.hidden = true;
    el.textContent = '';
  },

  showError(msg) {
    const el = document.getElementById('auth-error');
    el.hidden = false;
    el.textContent = msg;
  },

  async refresh() {
    try {
      const resp = await fetch('/api/auth/me', { credentials: 'include' });
      if (resp.ok) {
        this.user = await resp.json();
      } else {
        this.user = null;
      }
    } catch {
      this.user = null;
    }
    this.render();
    window.dispatchEvent(new CustomEvent('auth:changed', { detail: { user: this.user } }));
  },

  render() {
    const loggedOut = document.getElementById('auth-logged-out');
    const loggedIn = document.getElementById('auth-logged-in');
    const convertPanel = document.getElementById('convert-panel');

    if (this.user) {
      loggedOut.hidden = true;
      loggedIn.hidden = false;
      document.getElementById('user-email').textContent = this.user.email;
      convertPanel?.classList.remove('panel--locked');
    } else {
      loggedOut.hidden = false;
      loggedIn.hidden = true;
      convertPanel?.classList.add('panel--locked');
    }

    const footerUser = document.getElementById('footer-user');
    if (footerUser) {
      footerUser.textContent = this.user ? this.user.email : '未登录';
    }
  },

  async submit() {
    const email = document.getElementById('auth-email').value.trim();
    const password = document.getElementById('auth-password').value;
    const path = this.mode === 'register' ? '/api/auth/register' : '/api/auth/login';

    try {
      const resp = await fetch(path, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        this.showError(typeof data.detail === 'string' ? data.detail : '认证失败');
        return;
      }
      this.user = data;
      this.closeModal();
      this.render();
      window.dispatchEvent(new CustomEvent('auth:changed', { detail: { user: this.user } }));
    } catch {
      this.showError('网络错误，请重试');
    }
  },

  async logout() {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
    this.user = null;
    this.render();
    window.dispatchEvent(new CustomEvent('auth:changed', { detail: { user: null } }));
  },

  requireAuth() {
    if (!this.user) {
      this.openModal('login');
      return false;
    }
    return true;
  },
};

document.addEventListener('DOMContentLoaded', () => AUTH.init());
