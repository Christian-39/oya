/**
 * OYA Charts - Chart.js Configurations
 * Financial trends, member distribution, clan distribution
 */

(function() {
  'use strict';

  const COLORS = {
    primary: '#0B3D91',
    primaryLight: '#1a56c7',
    primary50: 'rgba(11, 61, 145, 0.08)',
    accent: '#D4AF37',
    accent50: 'rgba(212, 175, 55, 0.15)',
    success: '#10B981',
    warning: '#F59E0B',
    danger: '#EF4444',
    info: '#3B82F6',
    grid: '#E2E8F0',
    gridDark: '#334155',
    text: '#475569',
    textDark: '#94A3B8'
  };

  function isDark() {
    return document.documentElement.getAttribute('data-theme') === 'dark';
  }

  function getGridColor() {
    return isDark() ? COLORS.gridDark : COLORS.grid;
  }

  function getTextColor() {
    return isDark() ? COLORS.textDark : COLORS.text;
  }

  // ─── Financial Trend Chart ───
  function initFinancialChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const chartData = data || {
      labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
      income: [150000, 180000, 165000, 200000, 175000, 220000, 195000, 210000, 230000, 205000, 240000, 260000],
      expenses: [80000, 95000, 85000, 110000, 90000, 100000, 105000, 115000, 95000, 120000, 110000, 130000]
    };

    return new Chart(ctx, {
      type: 'line',
      data: {
        labels: chartData.labels,
        datasets: [
          {
            label: 'Income',
            data: chartData.income,
            borderColor: COLORS.primary,
            backgroundColor: 'rgba(11, 61, 145, 0.08)',
            fill: true,
            tension: 0.4,
            borderWidth: 2.5,
            pointRadius: 3,
            pointHoverRadius: 6,
            pointBackgroundColor: COLORS.primary,
            pointBorderColor: '#fff',
            pointBorderWidth: 2
          },
          {
            label: 'Expenses',
            data: chartData.expenses,
            borderColor: COLORS.danger,
            backgroundColor: 'rgba(239, 68, 68, 0.06)',
            fill: true,
            tension: 0.4,
            borderWidth: 2.5,
            pointRadius: 3,
            pointHoverRadius: 6,
            pointBackgroundColor: COLORS.danger,
            pointBorderColor: '#fff',
            pointBorderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            align: 'end',
            labels: {
              usePointStyle: true,
              pointStyle: 'circle',
              padding: 20,
              font: { size: 12, family: 'Inter' },
              color: getTextColor()
            }
          },
          tooltip: {
            backgroundColor: isDark() ? '#1E293B' : '#fff',
            titleColor: isDark() ? '#F1F5F9' : '#0F172A',
            bodyColor: isDark() ? '#CBD5E1' : '#475569',
            borderColor: isDark() ? '#334155' : '#E2E8F0',
            borderWidth: 1,
            padding: 12,
            cornerRadius: 10,
            displayColors: true,
            callbacks: {
              label: function(context) {
                return context.dataset.label + ': \u20A6' + context.parsed.y.toLocaleString();
              }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              font: { size: 11, family: 'Inter' },
              color: getTextColor()
            }
          },
          y: {
            grid: { color: getGridColor(), drawBorder: false },
            ticks: {
              font: { size: 11, family: 'Inter' },
              color: getTextColor(),
              callback: function(value) {
                return '\u20A6' + (value / 1000) + 'k';
              }
            }
          }
        }
      }
    });
  }

  // ─── Member Distribution (Doughnut) ───
  function initMemberDistributionChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const chartData = data || {
      labels: ['Active Members', 'Inactive', 'New', 'Suspended'],
      values: [342, 28, 45, 12]
    };

    return new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: chartData.labels,
        datasets: [{
          data: chartData.values,
          backgroundColor: [COLORS.primary, COLORS.danger, COLORS.success, COLORS.warning],
          borderWidth: 0,
          hoverOffset: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '68%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              usePointStyle: true,
              pointStyle: 'circle',
              padding: 16,
              font: { size: 12, family: 'Inter' },
              color: getTextColor()
            }
          },
          tooltip: {
            backgroundColor: isDark() ? '#1E293B' : '#fff',
            titleColor: isDark() ? '#F1F5F9' : '#0F172A',
            bodyColor: isDark() ? '#CBD5E1' : '#475569',
            borderColor: isDark() ? '#334155' : '#E2E8F0',
            borderWidth: 1,
            padding: 10,
            cornerRadius: 8,
            callbacks: {
              label: function(context) {
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const pct = ((context.parsed / total) * 100).toFixed(1);
                return context.label + ': ' + context.parsed + ' (' + pct + '%)';
              }
            }
          }
        }
      }
    });
  }

  // ─── Clan Distribution (Bar) ───
  function initClanDistributionChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const chartData = data || {
      labels: ['Eze', 'Nweke', 'Okafor', 'Onu', 'Agu', 'Ibe', 'Udo', 'Nnaji'],
      values: [78, 65, 92, 54, 43, 38, 51, 60]
    };

    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: chartData.labels,
        datasets: [{
          label: 'Members',
          data: chartData.values,
          backgroundColor: COLORS.primary50,
          hoverBackgroundColor: COLORS.primary,
          borderRadius: 6,
          borderSkipped: false,
          barThickness: 28
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: isDark() ? '#1E293B' : '#fff',
            titleColor: isDark() ? '#F1F5F9' : '#0F172A',
            bodyColor: isDark() ? '#CBD5E1' : '#475569',
            borderColor: isDark() ? '#334155' : '#E2E8F0',
            borderWidth: 1,
            padding: 10,
            cornerRadius: 8
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              font: { size: 11, family: 'Inter' },
              color: getTextColor()
            }
          },
          y: {
            grid: { color: getGridColor(), drawBorder: false },
            ticks: {
              font: { size: 11, family: 'Inter' },
              color: getTextColor(),
              stepSize: 20
            }
          }
        }
      }
    });
  }

  // ─── Payment History (Line) ───
  function initPaymentChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const chartData = data || {
      labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
      values: [5000, 5000, 3000, 5000, 0, 5000]
    };

    return new Chart(ctx, {
      type: 'line',
      data: {
        labels: chartData.labels,
        datasets: [{
          label: 'Amount Paid',
          data: chartData.values,
          borderColor: COLORS.accent,
          backgroundColor: 'rgba(212, 175, 55, 0.08)',
          fill: true,
          tension: 0.4,
          borderWidth: 2.5,
          pointRadius: 4,
          pointHoverRadius: 7,
          pointBackgroundColor: COLORS.accent,
          pointBorderColor: '#fff',
          pointBorderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: isDark() ? '#1E293B' : '#fff',
            titleColor: isDark() ? '#F1F5F9' : '#0F172A',
            bodyColor: isDark() ? '#CBD5E1' : '#475569',
            borderColor: isDark() ? '#334155' : '#E2E8F0',
            borderWidth: 1,
            padding: 10,
            cornerRadius: 8,
            callbacks: {
              label: function(context) {
                return 'Amount: \u20A6' + context.parsed.y.toLocaleString();
              }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              font: { size: 11, family: 'Inter' },
              color: getTextColor()
            }
          },
          y: {
            grid: { color: getGridColor(), drawBorder: false },
            ticks: {
              font: { size: 11, family: 'Inter' },
              color: getTextColor(),
              callback: function(value) {
                return '\u20A6' + (value / 1000) + 'k';
              }
            }
          }
        }
      }
    });
  }

  // ─── Init All Charts ───
  function init() {
    // Wait for Chart.js to be available
    if (typeof Chart === 'undefined') {
      setTimeout(init, 100);
      return;
    }

    const charts = {};

    // Set global defaults
    Chart.defaults.font.family = 'Inter, Poppins, sans-serif';
    Chart.defaults.color = getTextColor();

    // Init each chart type
    charts.financial = initFinancialChart('financialChart');
    charts.members = initMemberDistributionChart('memberDistributionChart');
    charts.clans = initClanDistributionChart('clanDistributionChart');
    charts.payments = initPaymentChart('paymentChart');

    // Re-render on theme change
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === 'data-theme') {
          Object.values(charts).forEach(chart => {
            if (chart) {
              chart.options.scales.x.ticks.color = getTextColor();
              chart.options.scales.y.ticks.color = getTextColor();
              chart.options.scales.y.grid.color = getGridColor();
              if (chart.options.plugins.legend) {
                chart.options.plugins.legend.labels.color = getTextColor();
              }
              chart.update('none');
            }
          });
        }
      });
    });

    observer.observe(document.documentElement, { attributes: true });

    window.OYACharts = charts;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
