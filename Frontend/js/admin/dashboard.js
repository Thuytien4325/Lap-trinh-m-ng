document.addEventListener('DOMContentLoaded', function () {
  // Mặc định tải Dashboard
  // loadContent('../../html/admin/dashboard.html'); PH comment

  document.querySelectorAll('.nav-link').forEach((link) => {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      let page = this.getAttribute('data-page');
      loadContent(`assets/${page}`);

      // Xóa active khỏi tất cả mục
      document.querySelectorAll('.nav-link').forEach((l) => l.classList.remove('active'));
      // Thêm active vào mục đang chọn
      this.classList.add('active');
    });
  });
});

// Hàm tải nội dung trang
function loadContent(page) {
  fetch(page)
    .then((response) => {
      if (!response.ok) throw new Error('Trang không tồn tại');
      return response.text();
    })
    .then((html) => {
      document.getElementById('main-content').innerHTML = html;
      if (page.includes('dashboard')) fetchData();
    })
    .catch((error) => console.error('Lỗi tải nội dung:', error));
}

// Lấy dữ liệu từ API
async function fetchData() {
  try {
    let response = await fetch('http://127.0.0.1:8000/auth');
    let data = await response.json();

    document.getElementById('userCount').textContent = data.users ?? 0;
    document.getElementById('messageCount').textContent = data.messages ?? 0;
    document.getElementById('settingsCount').textContent = data.settings ?? 0;

    updateChart(data.users, data.messages, data.settings);
  } catch (error) {
    console.error('Lỗi tải dữ liệu:', error);
  }
}

// Vẽ biểu đồ
let chartInstance;
function updateChart(users, messages, settings) {
  let chartCanvas = document.getElementById('myChart');
  if (!chartCanvas) return; // Kiểm tra nếu chưa có phần tử

  const ctx = chartCanvas.getContext('2d');

  if (chartInstance) chartInstance.destroy();

  chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Người dùng', 'Tin nhắn', 'Cài đặt'],
      datasets: [
        {
          label: 'Số lượng',
          data: [users, messages, settings],
          backgroundColor: ['#f39c12', '#3498db', '#e74c3c'],
        },
      ],
    },
    options: { responsive: true, scales: { y: { beginAtZero: true } } },
  });
}



  // Xử lý tố cáo
  function initReportHandling() {
    const reportType = document.getElementById('reportType');
    const filterBtn = document.getElementById('filterBtn');

    const userSection = document.getElementById('userSection');
    const groupSection = document.getElementById('groupSection');

    const searchUserInput = document.getElementById('searchUserInput');
    const userTable = document.getElementById('userTable');

    // Thêm sự kiện click cho nút lọc
    filterBtn?.addEventListener('click', handleFilter);

    // Thêm sự kiện input cho ô tìm kiếm người dùng
    searchUserInput?.addEventListener('input', handleSearchUser);

    // Xử lý sự kiện click cho các nút Ban
    document.querySelectorAll('.ban-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const row = btn.closest('tr');
        const name = row.querySelector('td')?.textContent;
        showToast(`${name} đã bị ban.`);
        row.remove();
      });
    });
  }

  function handleFilter() {
    const value = document.getElementById("reportType").value;
    document.getElementById("userSection").style.display = value === "user" ? "block" : "none";
    document.getElementById("groupSection").style.display = value === "group" ? "block" : "none";
  }

  function handleSearchUser() {
    const filter = document.getElementById("searchUserInput").value.toLowerCase();
    document.querySelectorAll("#userTable tbody tr").forEach(row => {
      const username = row.children[0].textContent.toLowerCase();
      row.style.display = username.includes(filter) ? "" : "none";
    });
  }

  function showToast(message) {
    const toast = document.getElementById('toast');
    toast.innerHTML = `<div class="toast">${message}</div>`;
    setTimeout(() => {
      toast.innerHTML = '';
    }, 3000);
  }

  // Gọi hàm khởi tạo khi trang đã tải xong
  window.onload = initReportHandling;

