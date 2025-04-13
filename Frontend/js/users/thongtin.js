import { toast, createModal } from '../untils.js';
import config from '../config.js';

let avatarFile = null;

export function formatVNTime(timestamp) {
  const date = new Date(timestamp);
  const formatter = new Intl.DateTimeFormat('vi-VN', {
    timeZone: 'Asia/Ho_Chi_Minh',
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
  });

  return formatter.format(date);
}
document.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem('access_token');
  if (!token) {
    toast({
      title: 'Lỗi',
      message: 'Vui lòng đăng nhập để tiếp tục.',
      type: 'error',
      duration: 3000,
    });
    window.location.href = '/';
    return;
  }

  fetchUserInfo(token);

  document.querySelector('.edit-btn').addEventListener('click', () => openUpdatePopup(token));
});

async function fetchUserInfo(token) {
  try {
    const response = await fetch(`${config.baseURL}/users/`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (response.ok) {
      const userData = await response.json();

      const avatarUrl = userData.avatar
        ? userData.avatar.startsWith('http')
          ? userData.avatar
          : `${config.baseURL}/${userData.avatar.replace(/^\/+/, '')}`
        : '../../assets/image/private-chat-default.jpg';

      const avatarImg = document.querySelector('.avatar');
      if (avatarImg) {
        avatarImg.src = avatarUrl;
        avatarImg.onerror = () => {
          avatarImg.src = '../../assets/image/private-chat-default.jpg';
        };
      }

      document.getElementById('user-username').textContent = userData.username || '';
      document.getElementById('user-nickname').textContent = userData.nickname || 'Chưa có';
      document.getElementById('user-email').textContent = userData.email || 'user@example.com';
    }
  } catch (error) {
    console.error('Lỗi khi lấy thông tin người dùng:', error);
  }
}

function openUpdatePopup(token) {
  const popupHTML = `
    <div class="popup-overlay">
      <div class="popup-container">
        <h2>Cập nhật thông tin</h2>
        <form id="update-form" enctype="multipart/form-data">
          <label>Nickname:</label>
          <input type="text" id="nickname-input" placeholder="Nhập nickname mới"/><br><br>
          <label>Email:</label>
          <input type="email" id="email-input" autocomplete="email" placeholder="Nhập email mới"/><br><br>
          <label>Chọn ảnh đại diện:</label>
          <input type="file" id="avatar-modal-upload" accept=".jpg,.jpeg,.png"/><br><br>
        </form>
        <button id="save-btn">Lưu</button>
        <button id="cancel-btn">Hủy</button>
      </div>
    </div>
  `;

  // Thêm popup vào body
  document.body.insertAdjacentHTML('beforeend', popupHTML);

  // Bắt sự kiện chọn avatar
  setTimeout(() => {
    const fileInput = document.getElementById('avatar-modal-upload');
    fileInput?.addEventListener('change', (e) => {
      avatarFile = e.target.files[0];
    });
  }, 0);

  // Lắng nghe sự kiện cho các nút
  document.getElementById('save-btn').addEventListener('click', () => handleUpdate(token));
  document.getElementById('cancel-btn').addEventListener('click', closePopup);
}

function handleUpdate(token) {
  setTimeout(() => {
    const nicknameInput = document.getElementById('nickname-input');
    const emailInput = document.getElementById('email-input');

    if (!nicknameInput || !emailInput) {
      toast({
        title: 'Lỗi',
        message: 'Không tìm thấy form cập nhật. Vui lòng thử lại!',
        type: 'error',
        duration: 3000,
      });
      return;
    }

    const nickname = nicknameInput.value.trim();
    const email = emailInput.value.trim();

    // Kiểm tra định dạng email nếu có nhập
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      toast({
        title: 'Lỗi',
        message: 'Email không hợp lệ. Vui lòng nhập đúng định dạng!',
        type: 'error',
        duration: 3000,
      });
      return;
    }

    // Nếu không có gì để cập nhật
    if (!nickname && !email && !avatarFile) {
      toast({
        title: 'Cảnh báo',
        message: 'Vui lòng nhập ít nhất một thông tin để cập nhật!',
        type: 'warning',
        duration: 3000,
      });
      return;
    }

    const formData = new FormData();
    if (avatarFile) formData.append('avatar_file', avatarFile);

    const query = [];
    if (nickname) query.push(`nickname=${encodeURIComponent(nickname)}`);
    if (email) query.push(`email=${encodeURIComponent(email)}`);
    const queryString = query.length ? `?${query.join('&')}` : '';

    fetch(`${config.baseURL}/users/${queryString}`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    })
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Cập nhật thất bại.');

        toast({
          title: 'Thành công',
          message: data.message || 'Cập nhật thông tin thành công!',
          type: 'success',
          duration: 3000,
        });

        avatarFile = null;
        fetchUserInfo(token);
        closePopup(); // Đóng popup khi thành công
      })
      .catch((err) => {
        toast({
          title: 'Lỗi',
          message: err.message || 'Đã xảy ra lỗi khi cập nhật.',
          type: 'error',
          duration: 3000,
        });
      });
  }, 50); // Đợi DOM cập nhật popup
}

function closePopup() {
  const popupOverlay = document.querySelector('.popup-overlay');
  if (popupOverlay) {
    popupOverlay.remove();
  }
}

function logout() {
  createModal({
    title: 'Xác nhận đăng xuất',
    message: 'Bạn có chắc chắn muốn đăng xuất không?',
    primaryButtonText: 'Đăng xuất',
    secondaryButtonText: 'Hủy',
    showSecondaryButton: true,
    onPrimary: () => {
      localStorage.clear();
      toast({
        title: 'Đăng xuất thành công!',
        message: 'Đang đăng xuất...',
        type: 'success',
      });
      setTimeout(() => {
        window.location.href = '../auth/login.html';
      }, 1500);
    },
  });
}

window.logout = logout;
