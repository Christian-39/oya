
    const sidebar = document.getElementById('sidebar');
    const notifyDrop = document.getElementById('notifyDrop');
    const profileDrop = document.getElementById('profileDrop');

    function toggleSidebar() {
      sidebar.classList.toggle('show');
    }
    function toggleDark() {
      document.body.classList.toggle('dark');
    }
    function toggleNotify() {
      notifyDrop.classList.toggle('show');
      profileDrop.classList.remove('show');
    }
    function toggleProfile() {
      profileDrop.classList.toggle('show');
      notifyDrop.classList.remove('show');
    }

    const ctx = document.getElementById('contribChart');
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
        datasets: [{
          label: '₦ Contributions',
          data: [12000, 18000, 15000, 22000, 30000, 26000, 28000, 35000, 40000, 38000, 42000, 50000],
          borderWidth: 2,
          fill: true,
          tension: .35
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } }
      }
    });
