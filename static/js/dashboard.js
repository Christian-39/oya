/**
 * OYA Dashboard - Interactive Features
 * Real-time updates, bulk actions, dynamic content
 */

(function() {
  'use strict';

  // ─── Bulk Actions ───
  function initBulkActions() {
    const selectAll = document.getElementById('selectAll');
    const bulkBar = document.getElementById('bulkActionBar');
    const selectedCount = document.getElementById('selectedCount');

    if (!selectAll) return;

    const rowCheckboxes = document.querySelectorAll('.row-checkbox');

    selectAll.addEventListener('change', () => {
      rowCheckboxes.forEach(cb => {
        cb.checked = selectAll.checked;
      });
      updateBulkBar();
    });

    rowCheckboxes.forEach(cb => {
      cb.addEventListener('change', () => {
        updateBulkBar();
        const allChecked = Array.from(rowCheckboxes).every(c => c.checked);
        const someChecked = Array.from(rowCheckboxes).some(c => c.checked);
        selectAll.checked = allChecked;
        selectAll.indeterminate = someChecked && !allChecked;
      });
    });

    function updateBulkBar() {
      const checked = document.querySelectorAll('.row-checkbox:checked').length;
      if (checked > 0) {
        bulkBar.classList.remove('hidden');
        selectedCount.textContent = checked;
      } else {
        bulkBar.classList.add('hidden');
      }
    }

    // Bulk action buttons
    document.querySelectorAll('[data-bulk-action]').forEach(btn => {
      btn.addEventListener('click', () => {
        const action = btn.dataset.bulkAction;
        const checked = document.querySelectorAll('.row-checkbox:checked');
        const ids = Array.from(checked).map(cb => cb.value);

        if (window.OYA && window.OYA.showToast) {
          window.OYA.showToast(`${action} action applied to ${ids.length} item(s)`, 'success');
        }
      });
    });
  }

  // ─── Search/Filter Tables ───
  function initTableSearch() {
    document.querySelectorAll('[data-table-search]').forEach(input => {
      const tableId = input.dataset.tableSearch;
      const table = document.getElementById(tableId);
      if (!table) return;

      const rows = table.querySelectorAll('tbody tr');

      input.addEventListener('input', () => {
        const query = input.value.toLowerCase().trim();
        rows.forEach(row => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(query) ? '' : 'none';
        });
      });
    });
  }

  // ─── Confirm Delete ───
  function initConfirmDelete() {
    document.querySelectorAll('[data-confirm-delete]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
          e.preventDefault();
        }
      });
    });
  }

  // ─── Animated Counters ───
  function animateCounters() {
    document.querySelectorAll('[data-counter]').forEach(el => {
      const target = parseInt(el.dataset.counter, 10);
      const duration = 1500;
      const start = performance.now();

      function update(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.floor(target * eased).toLocaleString();

        if (progress < 1) {
          requestAnimationFrame(update);
        }
      }

      // Use IntersectionObserver to start animation when visible
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            requestAnimationFrame(update);
            observer.unobserve(el);
          }
        });
      }, { threshold: 0.5 });

      observer.observe(el);
    });
  }

  // ─── Mark Notifications Read ───
  function initNotificationActions() {
    document.querySelectorAll('[data-mark-read]').forEach(btn => {
      btn.addEventListener('click', () => {
        const item = btn.closest('.notification-item');
        if (item) {
          item.classList.remove('unread');
          updateNotificationBadge(-1);
        }
      });
    });

    const markAllBtn = document.getElementById('markAllRead');
    if (markAllBtn) {
      markAllBtn.addEventListener('click', () => {
        document.querySelectorAll('.notification-item.unread').forEach(item => {
          item.classList.remove('unread');
        });
        updateNotificationBadge(0, true);
        if (window.OYA && window.OYA.showToast) {
          window.OYA.showToast('All notifications marked as read', 'success');
        }
      });
    }
  }

  function updateNotificationBadge(change, reset) {
    const badge = document.getElementById('notificationBadge');
    if (!badge) return;

    if (reset) {
      badge.style.display = 'none';
      return;
    }

    let count = parseInt(badge.textContent, 10) || 0;
    count = Math.max(0, count + change);
    badge.textContent = count;

    if (count === 0) {
      badge.style.display = 'none';
    }
  }

  // ─── Export Table to CSV ───
  function initExportButtons() {
    document.querySelectorAll('[data-export]').forEach(btn => {
      btn.addEventListener('click', () => {
        const tableId = btn.dataset.export;
        const table = document.getElementById(tableId);
        if (!table) return;

        const rows = table.querySelectorAll('tr');
        let csv = [];

        rows.forEach(row => {
          const cells = row.querySelectorAll('th, td');
          const rowData = Array.from(cells).map(cell => {
            let text = cell.textContent.trim().replace(/"/g, '""');
            return `"${text}"`;
          });
          csv.push(rowData.join(','));
        });

        const blob = new Blob([csv.join('\n')], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `oya-export-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);

        if (window.OYA && window.OYA.showToast) {
          window.OYA.showToast('Data exported successfully', 'success');
        }
      });
    });
  }

  // ─── Form Validation ───
  function initFormValidation() {
    document.querySelectorAll('form[data-validate]').forEach(form => {
      form.addEventListener('submit', (e) => {
        let isValid = true;

        form.querySelectorAll('[required]').forEach(field => {
          const group = field.closest('.form-group');
          const existingError = group?.querySelector('.form-error');
          if (existingError) existingError.remove();

          if (!field.value.trim()) {
            isValid = false;
            field.style.borderColor = '#EF4444';

            const error = document.createElement('div');
            error.className = 'form-error';
            error.textContent = 'This field is required';
            group.appendChild(error);
          } else {
            field.style.borderColor = '';
          }
        });

        if (!isValid) {
          e.preventDefault();
          if (window.OYA && window.OYA.showToast) {
            window.OYA.showToast('Please fill in all required fields', 'error');
          }
        }
      });

      // Clear error on input
      form.querySelectorAll('[required]').forEach(field => {
        field.addEventListener('input', () => {
          const group = field.closest('.form-group');
          const error = group?.querySelector('.form-error');
          if (error && field.value.trim()) {
            error.remove();
            field.style.borderColor = '';
          }
        });
      });
    });
  }

  // ─── Auto-hide Alerts ───
  function initAutoHideAlerts() {
    document.querySelectorAll('.alert[data-auto-hide]').forEach(alert => {
      const delay = parseInt(alert.dataset.autoHide, 10) || 5000;
      setTimeout(() => {
        alert.style.transition = 'opacity 0.3s ease';
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 300);
      }, delay);
    });
  }

  // ─── Initialize ───
  function init() {
    initBulkActions();
    initTableSearch();
    initConfirmDelete();
    animateCounters();
    initNotificationActions();
    initExportButtons();
    initFormValidation();
    initAutoHideAlerts();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
