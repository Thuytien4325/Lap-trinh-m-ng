document.addEventListener('DOMContentLoaded', function () {
  // Mặc định tải Dashboard
  loadContent('../../html/admin/dashboard.html');

  document.querySelectorAll('.nav-button').forEach((button) => {
    button.addEventListener('click', function () {
      document.querySelectorAll('.nav-button').forEach((btn) => btn.classList.remove('active'));
      this.classList.add('active');
      const page = this.getAttribute('data-page');
      if (page) {
        loadContent(`../../html/admin/${page}`);
      }
    });
  });

  // Xử lý nút đóng
  document.getElementById('closeLogin').addEventListener('click', function () {
    if (confirm('Bạn có muốn đăng xuất không?')) {
      window.location.href = '/login.html'; // Điều hướng về trang đăng nhập
    }
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
      if (page.includes('dashboard.html')) fetchDashboardData();
      if (page.includes('users.html')) fetchUsers();
      if (page.includes('groups.html')) fetchGroups();
      if (page.includes('reports.html')) fetchReports();
      if (page.includes('settings.html')) fetchSettings();
      if (page.includes('banned_users.html')) fetchBannedUsers();
    })
    .catch((error) => console.error('Lỗi tải nội dung:', error));
}

// Lấy dữ liệu Dashboard
async function fetchDashboardData() {
  try {
    let response = await fetch('http://127.0.0.1:8000/auth');
    let data = await response.json();

    document.getElementById('userCount').textContent = data.users ?? 0;
    document.getElementById('messageCount').textContent = data.messages ?? 0;
    document.getElementById('settingsCount').textContent = data.settings ?? 0;

    updateChart(data.users, data.messages, data.settings);
  } catch (error) {
    console.error('Lỗi tải dữ liệu dashboard:', error);
  }
}

// Lấy danh sách người dùng
async function fetchUsers() {
  try {
    let response = await fetch('http://127.0.0.1:8000/users');
    let users = await response.json();
    const tableBody = document.getElementById('usersTableBody');
    tableBody.innerHTML = '';
    users.forEach(user => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td data-label="ID">${user.id}</td>
        <td data-label="Tên người dùng">${user.username}</td>
        <td data-label="Email">${user.email}</td>
        <td data-label="Trạng thái">${user.is_banned ? 'Bị cấm' : 'Hoạt động'}</td>
        <td data-label="Hành động">
          ${!user.is_banned ? `<button class="ban-button" onclick="banUser(${user.id})">Cấm</button>` : ''}
        </td>
      `;
      tableBody.appendChild(row);
    });
  } catch (error) {
    console.error('Lỗi tải danh sách người dùng:', error);
  }
}

// Cấm người dùng
async function banUser(userId) {
  if (confirm('Bạn có chắc chắn muốn cấm người dùng này?')) {
    try {
      await fetch('http://127.0.0.1:8000/users-ban', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
      });
      fetchUsers(); // Làm mới danh sách
    } catch (error) {
      console.error('Lỗi cấm người dùng:', error);
    }
  }
}

// Lấy danh sách nhóm
async function fetchGroups() {
  try {
    let response = await fetch('http://127.0.0.1:8000/groups');
    let groups = await response.json();
    const tableBody = document.getElementById('groupsTableBody');
    tableBody.innerHTML = '';
    groups.forEach(group => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td data-label="ID">${group.id}</td>
        <td data-label="Tên nhóm">${group.name}</td>
        <td data-label="Mô tả">${group.description}</td>
      `;
      tableBody.appendChild(row);
    });
  } catch (error) {
    console.error('Lỗi tải danh sách nhóm:', error);
  }
}

// Lấy danh sách báo cáo vi phạm
async function fetchReports() {
  try {
    let response = await fetch('http://127.0.0.1:8000/processes-reports');
    let reports = await response.json();
    const tableBody = document.getElementById('reportsTableBody');
    tableBody.innerHTML = '';
    reports.forEach(report => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td data-label="ID">${report.id}</td>
        <td data-label="Người dùng">${report.user_id}</td>
        <td data-label="Nội dung">${report.content}</td>
        <td data-label="Trạng thái">${report.status}</td>
      `;
      tableBody.appendChild(row);
    });
  } catch (error) {
    console.error('Lỗi tải danh sách báo cáo:', error);
  }
}

// Lấy danh sách cài đặt
async function fetchSettings() {
  try {
    let response = await fetch('http://127.0.0.1:8000/settings');
    let settings = await response.json();
    const tableBody = document.getElementById('settingsTableBody');
    tableBody.innerHTML = '';
    settings.forEach(setting => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td data-label="ID">${setting.id}</td>
        <td data-label="Key">${setting.key}</td>
        <td data-label="Value">${setting.value}</td>
      `;
      tableBody.appendChild(row);
    });
  } catch (error) {
    console.error('Lỗi tải danh sách cài đặt:', error);
  }
}

// Thêm cài đặt mới
async function addSetting() {
  const key = document.getElementById('settingKey').value;
  const value = document.getElementById('settingValue').value;
  if (key && value) {
    try {
      await fetch('http://127.0.0.1:8000/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value })
      });
      fetchSettings(); // Làm mới danh sách
      document.getElementById('settingKey').value = '';
      document.getElementById('settingValue').value = '';
    } catch (error) {
      console.error('Lỗi thêm cài đặt:', error);
    }
  } else {
    alert('Vui lòng nhập đầy đủ Key và Value!');
  }
}

// Lấy danh sách người dùng bị cấm
async function fetchBannedUsers() {
  try {
    let response = await fetch('http://127.0.0.1:8000/users-ban');
    let users = await response.json();
    const tableBody = document.getElementById('bannedUsersTableBody');
    tableBody.innerHTML = '';
    users.forEach(user => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td data-label="ID">${user.id}</td>
        <td data-label="Tên người dùng">${user.username}</td>
        <td data-label="Email">${user.email}</td>
      `;
      tableBody.appendChild(row);
    });
  } catch (error) {
    console.error('Lỗi tải danh sách người dùng bị cấm:', error);
  }
}

// Vẽ biểu đồ
let chartInstance;
function updateChart(users, messages, settings) {
  let chartCanvas = document.getElementById('myChart');
  if (!chartCanvas) return;

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