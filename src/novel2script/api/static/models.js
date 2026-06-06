/** Model catalog loader (V2) */

const MODELS = {
  catalog: [],
  defaultId: 'openai-gpt-4o-mini',
  selectedId: null,

  accentClass(provider) {
    const map = {
      openai: '',
      dashscope: 'model-card--qwen',
      zai: 'model-card--zhipu',
      moonshot: 'model-card--kimi',
      deepseek: 'model-card--deepseek',
    };
    return map[provider] || '';
  },

  async init() {
    await this.load();
    this.render();
    window.addEventListener('auth:changed', () => this.render());
  },

  async load() {
    try {
      const resp = await fetch('/api/models');
      const data = await resp.json();
      this.catalog = data.models || [];
      this.defaultId = data.default_model_id || this.defaultId;
      const saved = localStorage.getItem('novel2script_model_id');
      if (saved && this.catalog.some((m) => m.id === saved && m.available)) {
        this.selectedId = saved;
      } else {
        const fallback = this.catalog.find((m) => m.id === this.defaultId && m.available)
          || this.catalog.find((m) => m.available);
        this.selectedId = fallback?.id || null;
      }
    } catch {
      this.catalog = [];
    }
  },

  render() {
    const grid = document.getElementById('model-grid');
    if (!grid) return;

    grid.innerHTML = this.catalog.map((m) => {
      const unavailable = !m.available;
      const checked = m.id === this.selectedId && !unavailable;
      const cls = [
        'model-card',
        this.accentClass(m.provider),
        unavailable ? 'model-card--unavailable' : '',
      ].filter(Boolean).join(' ');
      const title = unavailable ? `${m.name}（未配置 Key）` : m.name;
      return `
        <label class="${cls}" title="${unavailable ? '管理员未配置此模型' : ''}">
          <input type="radio" name="model_id" value="${m.id}" class="model-card__input"
            ${checked ? 'checked' : ''} ${unavailable ? 'disabled' : ''}>
          <span class="model-card__accent"></span>
          <span class="model-card__name">${title}</span>
          <span class="model-card__id">${m.id}</span>
          <span class="model-card__desc">${m.description || ''}</span>
        </label>`;
    }).join('');

    grid.querySelectorAll('input[name="model_id"]').forEach((input) => {
      input.addEventListener('change', () => {
        if (input.checked) {
          this.selectedId = input.value;
          localStorage.setItem('novel2script_model_id', input.value);
          this.updateFooter();
        }
      });
    });

    this.updateFooter();
  },

  updateFooter() {
    const el = document.getElementById('footer-model');
    const model = this.catalog.find((m) => m.id === this.selectedId);
    if (el) {
      el.textContent = model ? model.name : '—';
    }
  },

  getSelectedId() {
    const checked = document.querySelector('input[name="model_id"]:checked');
    return checked?.value || this.selectedId;
  },
};

document.addEventListener('DOMContentLoaded', () => MODELS.init());
