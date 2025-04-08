import { toast } from '../toast.js';
const API_BASE = 'http://127.0.0.1:8000/auth';

function parseTimeString(str) {
  if (!str) return 0;
  if (str.includes('phút')) return parseInt(str) * 60 * 1000;
  if (str.includes('giờ')) return parseInt(str) * 60 * 60 * 1000;
  if (str.includes('ngày')) return parseInt(str) * 24 * 60 * 60 * 1000;
  return 0;
}

function showModal({ title, message, showExtendButton = false, onExtend = null }) {
  const existing = document.querySelector('.modal-overlay');
  if (existing) existing.remove();

  const modalHTML = `
            <div class="modal-overlay show">
              <div class="modal">
                <div class="close-btn"><i class="fa-solid fa-xmark"></i></div>
                <div class="modal-header">
                  <h3>${title}</h3>
                </div>
                <div class="modal-content">
                  <p>${message}</p>
                </div>
                <div class="modal-buttons">
                  ${
                    showExtendButton
                      ? '<button class="btn btn-extend">Kéo dài phiên làm việc</button>'
                      : '<button class="btn btn-login">Đăng nhập lại</button>'
                  }
                </div>
              </div>
            </div>
          `;

  const wrapper = document.createElement('div');
  wrapper.innerHTML = modalHTML.trim();
  const modalEl = wrapper.firstElementChild;
  document.body.appendChild(modalEl);

  // Khi nhấn nút đóng (X) => luôn chuyển sang login
  modalEl.querySelector('.close-btn').onclick = () => {
    modalEl.remove();
    localStorage.clear();
    window.location.href = '../../html/auth/login.html';
  };

  // Nếu có nút "Kéo dài phiên" thì xử lý khác
  if (showExtendButton && onExtend) {
    modalEl.querySelector('.btn-extend').onclick = () => {
      onExtend();
      modalEl.remove();
    };
  }

  // Nếu không có nút "Kéo dài", thì là nút "Đăng nhập lại" => chuyển login
  if (!showExtendButton) {
    modalEl.querySelector('.btn-login').onclick = () => {
      modalEl.remove();
      localStorage.clear();
      window.location.href = '../../html/auth/login.html';
    };
  }
}

function checkTokenExpiration() {
  const loginTime = parseInt(localStorage.getItem('login_time'));
  const accessTokenTime = parseTimeString(localStorage.getItem('access_token_time'));
  const refreshTokenTime = parseTimeString(localStorage.getItem('refresh_token_time'));
  const refreshToken = localStorage.getItem('refresh_token');
  const now = Date.now();

  // Nếu không có token thì chuyển về trang đăng nhập
  if (!refreshToken || !loginTime) {
    localStorage.clear();
    showModal({
      title: 'Phiên đăng nhập đã hết hạn',
      message: 'Vui lòng đăng nhập lại.',
      onClose: () => (window.location.href = '../../html/auth/login.html'),
    });
    return;
  }

  // Hết hạn refresh_token => đăng xuất
  if (now - loginTime >= refreshTokenTime) {
    localStorage.clear();
    showModal({
      title: 'Phiên đăng nhập đã hết hạn',
      message: 'Vui lòng đăng nhập lại.',
      onClose: () => (window.location.href = '../../html/auth/login.html'),
    });
    return;
  }

  // Hết hạn access_token => refresh
  if (now - loginTime >= accessTokenTime) {
    showModal({
      title: 'Phiên đăng nhập của bạn sắp hết hạn',
      message: 'Bạn có muốn gia hạn phiên hiện tại không?',
      showExtendButton: true,
      onExtend: () => {
        fetch(`${API_BASE}/refresh-token?refresh_token=${encodeURIComponent(refreshToken)}`, {
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
            setTimeout(() => {
              window.location.href = '../../html/auth/login.html';
            }, 1200);
          });
      },
    });
  }
}

window.addEventListener('DOMContentLoaded', () => {
  checkTokenExpiration();
  setInterval(checkTokenExpiration, 60 * 1000);
});
