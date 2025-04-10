import { toast, createModal } from '../untils.js';
import config from '../config.js';

function parseTimeString(str) {
  if (!str) return 0;
  if (str.includes('phút')) return parseInt(str) * 60 * 1000;
  if (str.includes('giờ')) return parseInt(str) * 60 * 60 * 1000;
  if (str.includes('ngày')) return parseInt(str) * 24 * 60 * 60 * 1000;
  return 0;
}

function redirectToLogin() {
  localStorage.clear();
  window.location.href = '../../html/auth/login.html';
}

function checkTokenExpiration() {
  const loginTime = parseInt(localStorage.getItem('login_time'));
  const accessTokenTime = parseTimeString(localStorage.getItem('access_token_time'));
  const refreshTokenTime = parseTimeString(localStorage.getItem('refresh_token_time'));
  const refreshToken = localStorage.getItem('refresh_token');
  const now = Date.now();

  // Nếu không có token thì chuyển về trang đăng nhập
  if (!refreshToken || !loginTime) {
    createModal({
      title: 'Phiên đăng nhập đã hết hạn',
      message: 'Vui lòng đăng nhập lại.',
      primaryButtonText: 'Đăng nhập lại',
      onPrimary: redirectToLogin,
      onClose: redirectToLogin,
    });
    return;
  }

  // Hết hạn refresh_token => đăng xuất
  if (now - loginTime >= refreshTokenTime) {
    createModal({
      title: 'Phiên đăng nhập đã hết hạn',
      message: 'Vui lòng đăng nhập lại.',
      primaryButtonText: 'Đăng nhập lại',
      onPrimary: redirectToLogin,
      onClose: redirectToLogin,
    });
    return;
  }

  // Hết hạn access_token => hỏi có muốn gia hạn không
  if (now - loginTime >= accessTokenTime) {
    createModal({
      title: 'Phiên đăng nhập sắp hết hạn',
      message: 'Bạn có muốn gia hạn phiên làm việc không?',
      primaryButtonText: 'Kéo dài phiên làm việc',
      onPrimary: () => {
        fetch(`${config.baseURL}/auth/refresh-token?refresh_token=${encodeURIComponent(refreshToken)}`, {
          method: 'POST',
        })
          .then(async (res) => {
            if (!res.ok) {
              const errorData = await res.json();
              throw new Error(errorData.detail || 'Lỗi không xác định');
            }

            const result = await res.json();
            if (result.access_token) {
              toast({
                title: 'Thành công',
                message: 'Phiên làm việc đã được gia hạn thành công.',
                type: 'success',
              });

              localStorage.setItem('access_token', result.access_token);
              localStorage.setItem('refresh_token', result.refresh_token);
              localStorage.setItem('access_token_time', result.access_token_time);
              localStorage.setItem('refresh_token_time', result.refresh_token_time);
              localStorage.setItem('login_time', Date.now().toString());
            } else {
              throw new Error('Không thể làm mới token');
            }
          })
          .catch((err) => {
            let message = 'Không thể kết nối đến máy chủ. Vui lòng thử lại sau.';
            if (err.message.includes('Token không hợp lệ')) {
              message = 'Phiên đăng nhập đã hết hạn.';
            }

            toast({
              title: 'Lỗi',
              message,
              type: 'error',
            });

            localStorage.clear();
            setTimeout(redirectToLogin, 1200);
          });
      },
      onClose: redirectToLogin,
    });
  }
}

window.addEventListener('DOMContentLoaded', () => {
  checkTokenExpiration();
  setInterval(checkTokenExpiration, 60 * 1000);
});
