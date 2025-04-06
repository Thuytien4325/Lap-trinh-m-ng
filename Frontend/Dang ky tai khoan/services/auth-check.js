// auth-check.js
const API_BASE = 'http://127.0.0.1:8000/auth/';
function parseTimeString(str) {
  if (!str) return 0;
  if (str.includes('phút')) return parseInt(str) * 60 * 1000;
  if (str.includes('giờ')) return parseInt(str) * 60 * 60 * 1000;
  if (str.includes('ngày')) return parseInt(str) * 24 * 60 * 60 * 1000;
  return 0;
}

function checkTokenExpiration() {
  const loginTime = parseInt(localStorage.getItem('login_time'));
  const accessTokenTime = parseTimeString(
    localStorage.getItem('access_token_time')
  );
  const refreshTokenTime = parseTimeString(
    localStorage.getItem('refresh_token_time')
  );
  const refreshToken = localStorage.getItem('refresh_token');
  const now = Date.now();

  // Nếu không có token thì chuyển về trang đăng nhập
  if (!refreshToken || !loginTime) {
    alert('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
    localStorage.clear();
    window.location.href = 'login.html';
    return;
  }

  // Hết hạn refresh_token → đăng xuất
  if (now - loginTime >= refreshTokenTime) {
    alert('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
    localStorage.clear();
    window.location.href = 'login.html';
    return;
  }

  // Hết hạn access_token → refresh
  if (now - loginTime >= accessTokenTime) {
    fetch(`${API_BASE}/refresh-token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then((res) => res.json())
      .then((result) => {
        if (result.access_token) {
          localStorage.setItem('access_token', result.access_token);
          localStorage.setItem('login_time', Date.now().toString()); // cập nhật lại thời gian đăng nhập
        } else {
          throw new Error('Không thể làm mới token');
        }
      })
      .catch((err) => {
        console.error('Lỗi làm mới token:', err);
        alert('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
        localStorage.clear();
        window.location.href = 'login.html';
      });
  }
}

// Gọi kiểm tra ngay và lặp lại mỗi phút
checkTokenExpiration();
setInterval(checkTokenExpiration, 60 * 1000);
