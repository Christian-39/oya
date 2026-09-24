/**
 * OYA Search & Filter Module
 * Advanced search, filters, and data grid functionality
 */

(function() {
  'use strict';

  // ─── Debounce Utility ───
  function debounce(fn, delay) {
    let timeout;
    return function(...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  // ─── Table Search with Highlight ───
  class TableSearch {
    constructor(input, table) {
      this.input = input;
      this.table = table;
      this.rows = table.querySelectorAll('tbody tr');
      this.init();
    }

    init() {
      this.input.addEventListener('input', debounce(() => this.search(), 200));
    }

    search() {
      const query = this.input.value.toLowerCase().trim();
      let visibleCount = 0;

      this.rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const match = !query || text.includes(query);
        row.style.display = match ? '' : 'none';
        if (match) visibleCount++;

        // Highlight matches
        if (query && match) {
          this.highlightCells(row, query);
        } else {
          this.clearHighlight(row);
        }
      });

      // Show empty state if no results
      this.toggleEmptyState(visibleCount === 0);
    }

    highlightCells(row, query) {
      row.querySelectorAll('td').forEach(cell => {
        const text = cell.textContent;
        const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        if (regex.test(text) && !cell.querySelector('mark')) {
          cell.innerHTML = text.replace(regex, '<mark style="background:rgba(11,61,145,0.15);color:var(--oya-primary);padding:1px 2px;border-radius:3px;">$1</mark>');
        }
      });
    }

    clearHighlight(row) {
      row.querySelectorAll('td').forEach(cell => {
        const mark = cell.querySelector('mark');
        if (mark) {
          cell.textContent = cell.textContent;
        }
      });
    }

    toggleEmptyState(show) {
      let emptyRow = this.table.querySelector('.search-empty-row');
      if (show) {
        if (!emptyRow) {
          const colCount = this.table.querySelector('thead tr')?.children.length || 1;
          emptyRow = document.createElement('tr');
          emptyRow.className = 'search-empty-row';
          emptyRow.innerHTML = `
            <td colspan="${colCount}" style="text-align:center;padding:3rem 1rem;">
              <div style="color:var(--oya-text-muted);">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom:0.75rem;opacity:0.5;">
                  <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
                </svg>
                <p style="font-weight:500;">No results found</p>
                <p style="font-size:0.8125rem;margin-top:0.25rem;">Try adjusting your search terms</p>
              </div>
            </td>
          `;
          this.table.querySelector('tbody').appendChild(emptyRow);
        }
        emptyRow.style.display = '';
      } else if (emptyRow) {
        emptyRow.style.display = 'none';
      }
    }
  }

  // ─── Column Filter ───
  class ColumnFilter {
    constructor(select, table, columnIndex) {
      this.select = select;
      this.table = table;
      this.columnIndex = columnIndex;
      this.init();
    }

    init() {
      this.select.addEventListener('change', () => this.filter());
    }

    filter() {
      const value = this.select.value.toLowerCase();
      const rows = this.table.querySelectorAll('tbody tr:not(.search-empty-row)');

      rows.forEach(row => {
        const cell = row.children[this.columnIndex];
        if (!cell) return;

        const cellText = cell.textContent.toLowerCase().trim();
        const match = !value || cellText === value;

        // Check if row already hidden by other filters
        const currentDisplay = row.style.display;
        if (!match) {
          row.style.display = 'none';
        } else if (currentDisplay === 'none') {
          // Only show if no other filters are hiding it
          row.style.display = '';
        }
      });
    }
  }

  // ─── Sortable Table ───
  class SortableTable {
    constructor(table) {
      this.table = table;
      this.tbody = table.querySelector('tbody');
      this.headers = table.querySelectorAll('thead th[data-sort]');
      this.init();
    }

    init() {
      this.headers.forEach((header, index) => {
        header.style.cursor = 'pointer';
        header.style.userSelect = 'none';

        // Add sort icon
        const icon = document.createElement('span');
        icon.className = 'sort-icon';
        icon.innerHTML = ' \u2195';
        icon.style.color = 'var(--oya-text-muted)';
        icon.style.fontSize = '0.75rem';
        header.appendChild(icon);

        header.addEventListener('click', () => this.sort(index, header.dataset.sort));
      });
    }

    sort(columnIndex, type) {
      const rows = Array.from(this.tbody.querySelectorAll('tr:not(.search-empty-row)'));
      const isAsc = !this.tbody.classList.contains('sorted-asc');

      rows.sort((a, b) => {
        const aVal = this.getValue(a.children[columnIndex], type);
        const bVal = this.getValue(b.children[columnIndex], type);

        if (aVal < bVal) return isAsc ? -1 : 1;
        if (aVal > bVal) return isAsc ? 1 : -1;
        return 0;
      });

      // Update sort indicators
      this.headers.forEach(h => {
        const icon = h.querySelector('.sort-icon');
        if (icon) icon.innerHTML = ' \u2195';
      });

      const currentIcon = this.headers[columnIndex]?.querySelector('.sort-icon');
      if (currentIcon) {
        currentIcon.innerHTML = isAsc ? ' \u2191' : ' \u2193';
      }

      this.tbody.classList.toggle('sorted-asc', isAsc);
      rows.forEach(row => this.tbody.appendChild(row));
    }

    getValue(cell, type) {
      const text = cell.textContent.trim();

      if (type === 'number') {
        return parseFloat(text.replace(/[^\d.-]/g, '')) || 0;
      }
      if (type === 'date') {
        return new Date(text).getTime() || 0;
      }
      return text.toLowerCase();
    }
  }

  // ─── Initialize Search Inputs ───
  function initSearchInputs() {
    document.querySelectorAll('[data-search-table]').forEach(input => {
      const tableId = input.dataset.searchTable;
      const table = document.getElementById(tableId);
      if (table) {
        new TableSearch(input, table);
      }
    });
  }

  // ─── Initialize Column Filters ───
  function initColumnFilters() {
    document.querySelectorAll('[data-filter-table]').forEach(select => {
      const tableId = select.dataset.filterTable;
      const column = parseInt(select.dataset.filterColumn, 10);
      const table = document.getElementById(tableId);
      if (table && !isNaN(column)) {
        new ColumnFilter(select, table, column);
      }
    });
  }

  // ─── Initialize Sortable Tables ───
  function initSortableTables() {
    document.querySelectorAll('table[data-sortable]').forEach(table => {
      new SortableTable(table);
    });
  }

  // ─── Global Search (Topbar) ───
  function initGlobalSearch() {
    const searchInput = document.getElementById('globalSearch');
    if (!searchInput) return;

    // Read the resolved URL from the HTML data attribute
    const API_URL = searchInput.dataset.searchUrl;
    if (!API_URL) {
      console.error('Global search: no data-search-url found on #globalSearch');
      return;
    }

    const resultsContainer = document.getElementById('searchResults');
    let abortController = null;

    searchInput.addEventListener('input', debounce(() => {
      const query = searchInput.value.trim();
      if (query.length < 2) {
        if (resultsContainer) resultsContainer.classList.add('hidden');
        return;
      }

      if (abortController) abortController.abort();
      abortController = new AbortController();

      if (resultsContainer) {
        resultsContainer.classList.remove('hidden');
        resultsContainer.innerHTML = `
          <div class="dropdown-item" style="justify-content:center;color:var(--oya-text-muted);">
            <span>Searching...</span>
          </div>
        `;
      }

      fetch(`${API_URL}?q=${encodeURIComponent(query)}`, {
        signal: abortController.signal,
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      })
      .then(async r => {
        if (!r.ok) {
          const text = await r.text();
          throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`);
        }
        return r.json();
      })
      .then(data => {
        if (!resultsContainer) return;
        resultsContainer.innerHTML = '';

        const items = Array.isArray(data.results) ? data.results : [];
        if (items.length === 0) {
          resultsContainer.innerHTML = `
            <div class="dropdown-item" style="color:var(--oya-text-muted);cursor:default;">
              <span>No results found for "${escapeHtml(query)}"</span>
            </div>
          `;
          return;
        }

        items.forEach(item => {
          const el = document.createElement('a');
          el.className = 'dropdown-item';
          el.href = item.url || '#';
          el.style.display = 'flex';
          el.style.alignItems = 'center';
          el.style.gap = '0.5rem';
          el.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              ${getIconForType(item.type)}
            </svg>
            <span>${escapeHtml(item.name || 'Untitled')}</span>
          `;
          el.addEventListener('click', () => {
            resultsContainer.classList.add('hidden');
            searchInput.value = '';
          });
          resultsContainer.appendChild(el);
        });
      })
      .catch(err => {
        if (err.name === 'AbortError') return;
        console.error('Global search fetch failed:', err);
        if (!resultsContainer) return;
        resultsContainer.innerHTML = `
          <div class="dropdown-item" style="color:var(--oya-danger);cursor:default;">
            <span>Search unavailable. Please try again.</span>
          </div>
        `;
      });
    }, 300));

    // ... keep the rest of the function (keydown, outside click, focus) exactly as is ...
  }

  // ─── Helpers ───
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  function getIconForType(type) {
    const icons = {
      member: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>',
      user: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
      case: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
      project: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/>',
      election: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
      executive: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
      motorcycle: '<circle cx="5.5" cy="17.5" r="3.5"/><circle cx="18.5" cy="17.5" r="3.5"/><path d="M15 6a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm-3 11.5V14l-3-3 4-3 2 3h2"/>',
      default: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>'
    };
    return icons[type] || icons.default;
  }

  // ─── Initialize ───
  function init() {
    initSearchInputs();
    initColumnFilters();
    initSortableTables();
    initGlobalSearch();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose classes for manual initialization
  window.OYASearch = {
    TableSearch,
    ColumnFilter,
    SortableTable
  };
})();
