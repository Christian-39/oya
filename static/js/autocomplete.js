(function () {
  'use strict';

  function debounce(fn, delay) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text == null ? '' : String(text);
    return div.innerHTML;
  }

  class MemberAutocomplete {
    constructor(wrapper) {
      this.wrapper = wrapper;
      this.input = wrapper.querySelector('[data-autocomplete-input]');
      this.hidden = wrapper.querySelector('[data-autocomplete-value]');
      this.resultsBox = wrapper.querySelector('[data-autocomplete-results]');
      this.clearBtn = wrapper.querySelector('[data-autocomplete-clear]');
      
      if (!this.input || !this.hidden || !this.resultsBox) return;

      this.searchUrl = this.input.dataset.searchUrl;
      this.minChars = parseInt(this.input.dataset.minChars || '1', 10);
      
      // DEBUG: show URL on load
      if (!this.searchUrl) {
        this.resultsBox.innerHTML = '<div style="color:red;font-size:12px;">ERROR: searchUrl is empty!</div>';
        this.resultsBox.classList.remove('hidden');
      }

      this.items = [];
      this.activeIndex = -1;
      this.abortController = null;

      this.init();
    }

    init() {
      this.input.addEventListener('input', debounce(() => this.onType(), 250));
      this.input.addEventListener('keydown', (e) => this.onKeydown(e));
      this.input.addEventListener('focus', () => {
        if (this.items.length) this.showResults();
      });
      document.addEventListener('click', (e) => {
        if (!this.wrapper.contains(e.target)) this.hideResults();
      });
      if (this.clearBtn) {
        this.clearBtn.addEventListener('click', () => this.clear());
      }
      this.input.addEventListener('input', () => {
        if (!this.input.value) this.hidden.value = '';
      });
    }

    onType() {
      const q = this.input.value.trim();
      this.hidden.value = '';
      if (q.length < this.minChars) {
        this.hideResults();
        return;
      }
      this.search(q);
    }

    search(q) {
      if (!this.searchUrl) {
        this.resultsBox.innerHTML = '<div style="color:red;">No search URL configured</div>';
        this.showResults();
        return;
      }

      if (this.abortController) this.abortController.abort();
      this.abortController = new AbortController();

      const url = `${this.searchUrl}?q=${encodeURIComponent(q)}`;
      this.resultsBox.innerHTML = '<div class="autocomplete-item autocomplete-loading">Searching…</div>';
      this.showResults();

      fetch(url, {
        signal: this.abortController.signal,
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      })
        .then((r) => {
          if (!r.ok) throw new Error(`Server error ${r.status}`);
          return r.json();
        })
        .then((data) => {
          this.items = Array.isArray(data.results) ? data.results : [];
          this.render(q);
        })
        .catch((err) => {
          if (err.name === 'AbortError') return;
          this.resultsBox.innerHTML = `<div class="autocomplete-item autocomplete-empty" style="color:red;">${err.message}</div>`;
        });
    }

    render(q) {
      this.activeIndex = -1;
      if (!this.items.length) {
        this.resultsBox.innerHTML = `<div class="autocomplete-item autocomplete-empty">No matches for "${escapeHtml(q)}"</div>`;
        this.showResults();
        return;
      }
      this.resultsBox.innerHTML = '';
      this.items.forEach((item, idx) => {
        const el = document.createElement('div');
        el.className = 'autocomplete-item';
        el.setAttribute('role', 'option');
        el.dataset.index = idx;
        const subtitleParts = [item.serial_number, item.phone].filter(Boolean);
        el.innerHTML = `
          <span class="autocomplete-item-name">${escapeHtml(item.full_name)}</span>
          <span class="autocomplete-item-sub">${escapeHtml(subtitleParts.join(' · '))}</span>
        `;
        el.addEventListener('mousedown', (e) => {
          e.preventDefault();
          this.select(item);
        });
        this.resultsBox.appendChild(el);
      });
      this.showResults();
    }

    onKeydown(e) {
      if (this.resultsBox.classList.contains('hidden')) return;
      const rows = this.resultsBox.querySelectorAll('.autocomplete-item[data-index]');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        this.activeIndex = Math.min(this.activeIndex + 1, rows.length - 1);
        this.highlight(rows);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        this.activeIndex = Math.max(this.activeIndex - 1, 0);
        this.highlight(rows);
      } else if (e.key === 'Enter') {
        if (this.activeIndex >= 0 && this.items[this.activeIndex]) {
          e.preventDefault();
          this.select(this.items[this.activeIndex]);
        }
      } else if (e.key === 'Escape') {
        this.hideResults();
      }
    }

    highlight(rows) {
      rows.forEach((r, i) => r.classList.toggle('active', i === this.activeIndex));
      const active = rows[this.activeIndex];
      if (active) active.scrollIntoView({ block: 'nearest' });
    }

    select(item) {
      this.hidden.value = item.id;
      this.input.value = item.full_name;
      this.hideResults();
      this.wrapper.dispatchEvent(new CustomEvent('autocomplete:select', { detail: item, bubbles: true }));
    }

    clear() {
      this.hidden.value = '';
      this.input.value = '';
      this.items = [];
      this.hideResults();
      this.input.focus();
      this.wrapper.dispatchEvent(new CustomEvent('autocomplete:clear', { bubbles: true }));
    }

    showResults() {
      this.resultsBox.classList.remove('hidden');
    }

    hideResults() {
      this.resultsBox.classList.add('hidden');
    }
  }

  function initAll(root) {
    (root || document).querySelectorAll('[data-autocomplete-wrapper]').forEach((wrapper) => {
      if (wrapper.dataset.autocompleteInit) return;
      wrapper.dataset.autocompleteInit = '1';
      new MemberAutocomplete(wrapper);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => initAll());
  } else {
    initAll();
  }

  window.OYAAutocomplete = { init: initAll, MemberAutocomplete };
})();
