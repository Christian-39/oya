/**
 * OYA Theme Manager - Dark Mode / Light Mode / System
 */

(function() {
  'use strict';

  const STORAGE_KEY = 'oya_theme';

  // ─── Get Preferred Theme ───
  function getTheme() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'dark' || stored === 'light') {
      return stored;
    }
    // Treat null, undefined, 'auto', or 'system' as system
    return 'system';
  }

  // ─── Apply Theme ───
  function applyTheme(theme) {
    const root = document.documentElement;
    const effectiveTheme = (theme === 'system' || theme === 'auto')
      ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
      : theme;
    root.setAttribute('data-theme', effectiveTheme);
  }

  // ─── Save Theme ───
  function saveTheme(theme) {
    localStorage.setItem(STORAGE_KEY, theme);
  }

  // ─── Set Theme ───
  function setTheme(theme) {
    saveTheme(theme);
    applyTheme(theme);
    updateThemeUI(theme);
    // Notify all components (topbar, mobile header, settings, etc.)
    window.dispatchEvent(new CustomEvent('oyathemechange', { detail: { theme } }));
  }

  // ─── Update UI ───
  function updateThemeUI(theme) {
    const stored = theme || getTheme();
    document.querySelectorAll('[data-theme-option]').forEach(el => {
      const isActive = el.dataset.themeOption === stored;
      el.classList.toggle('active', isActive);
      // Sync checkmarks inside dropdown items
      const check = el.querySelector('.dropdown-check');
      if (check) {
        check.style.opacity = isActive ? '1' : '0';
      }
    });
  }

  // ─── Resolve Theme to concrete light/dark ───
  function resolveTheme(theme) {
    const t = theme || getTheme();
    if (t === 'system' || t === 'auto') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return (t === 'dark' || t === 'light') ? t : 'light';
  }

  // ─── Toggle Sidebar ───
  function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebarToggle');
    const mainContent = document.getElementById('mainContent');
    const overlay = document.getElementById('sidebarOverlay');

    if (!sidebar || !toggleBtn) return;

    // Desktop collapse / Mobile show
    toggleBtn.addEventListener('click', () => {
      if (window.innerWidth > 1024) {
        sidebar.classList.toggle('collapsed');
        if (mainContent) {
          mainContent.classList.toggle('expanded');
        }
      } else {
        sidebar.classList.toggle('show');
        if (overlay) overlay.classList.toggle('show');
      }
    });

    // Overlay click to close
    if (overlay) {
      overlay.addEventListener('click', () => {
        sidebar.classList.remove('show');
        overlay.classList.remove('show');
      });
    }

    // Submenu toggles
    document.querySelectorAll('.nav-item[data-submenu]').forEach(item => {
      item.addEventListener('click', (e) => {
        if (sidebar.classList.contains('collapsed') && window.innerWidth > 1024) {
          sidebar.classList.remove('collapsed');
          if (mainContent) mainContent.classList.remove('expanded');
        }
        const submenu = document.getElementById(item.dataset.submenu);
        if (submenu) {
          submenu.classList.toggle('open');
          item.classList.toggle('expanded');
        }
      });
    });
  }

  // ─── Dropdowns ───
  function initDropdowns() {
    document.querySelectorAll('.dropdown-toggle').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const dropdown = btn.closest('.dropdown');
        document.querySelectorAll('.dropdown.open').forEach(d => {
          if (d !== dropdown) d.classList.remove('open');
        });
        dropdown.classList.toggle('open');
      });
    });

    document.addEventListener('click', () => {
      document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
    });
  }

  // ─── Mobile Navigation ───
  function initMobileNav() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('.mobile-nav-item').forEach(item => {
      if (item.getAttribute('href') && currentPath.startsWith(item.getAttribute('href'))) {
        item.classList.add('active');
      }
    });
  }

  // ─── Tabs ───
  function initTabs() {
    document.querySelectorAll('.tabs').forEach(tabContainer => {
      tabContainer.addEventListener('click', (e) => {
        const btn = e.target.closest('.tab-btn');
        if (!btn) return;

        const tabs = tabContainer.closest('.tabs-wrapper') || tabContainer.parentElement;
        const tabId = btn.dataset.tab;

        // Update buttons
        tabContainer.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Update content
        tabs.querySelectorAll('.tab-content').forEach(content => {
          content.classList.toggle('active', content.id === tabId);
        });
      });
    });
  }

  // ─── Toasts ───
  function showToast(message, type = 'success', duration = 4000) {
    const container = document.getElementById('toastContainer') || createToastContainer();

    const icons = {
      success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
      error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
      warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
      info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || icons.info}</span>
      <span class="toast-message">${message}</span>
    `;

    container.appendChild(toast);

    // Trigger reflow
    void toast.offsetWidth;
    toast.classList.add('show');

    setTimeout(() => {
      toast.classList.remove('show');
      toast.addEventListener('transitionend', () => {
        if (toast.parentNode) toast.remove();
      }, { once: true });
    }, duration);
  }

  function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
  }

  // ─── Modal ───
  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('show');
      document.body.style.overflow = 'hidden';
    }
  }

  function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('show');
      document.body.style.overflow = '';
    }
  }

  // ─── DOM-Dependent Initialization ───
  function initDOM() {
    // Apply theme without transition on initial load
    document.documentElement.classList.add('no-transition');
    applyTheme(getTheme());
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        document.documentElement.classList.remove('no-transition');
      });
    });

    initSidebar();
    initDropdowns();
    initMobileNav();
    initTabs();

    // Theme switcher buttons (desktop dropdown, settings cards, mobile, etc.)
    document.querySelectorAll('[data-theme-option]').forEach(btn => {
      btn.addEventListener('click', () => setTheme(btn.dataset.themeOption));
    });

    // System preference change listener
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (getTheme() === 'system') {
        applyTheme('system');
      }
    });

    // Modal close on overlay click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          const modal = overlay.closest('.modal');
          if (modal) modal.classList.remove('show');
          document.body.style.overflow = '';
        }
      });
    });

    // Close modal on ESC
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal.show').forEach(m => {
          m.classList.remove('show');
        });
        document.body.style.overflow = '';
      }
    });
  }

  // ─── Expose API immediately so inline template scripts can use it ───
  window.OYA = {
    setTheme,
    getTheme,
    showToast,
    openModal,
    closeModal,
    // Backward-compatible namespace for topbar.html and legacy code
    theme: {
      set: setTheme,
      getStored: getTheme,
      resolve: resolveTheme
    }
  };

  // Also expose showToast globally for inline templates that expect it
  if (typeof window.showToast !== 'function') {
    window.showToast = showToast;
  }

  // Run DOM init when ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDOM);
  } else {
    initDOM();
  }
})();