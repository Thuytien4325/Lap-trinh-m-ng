import { toast, createModal, formatVNTime } from '../untils.js';
import config from '../config.js';

let avatarFile = null;

document.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem('access_token');
  if (!token) {
    toast({
      title: 'Lỗi',
      message: 'Vui lòng đăng nhập để tiếp tục.',
      type: 'error',
      duration: 3000,
    });
    window.location.href = '/login.html';
    return;
  }

  fetchUserInfo(token);

  document.querySelector('.edit-btn').addEventListener('click', () => openUpdateModal(token));
  document.getElementById('avatar-upload').addEventListener('change', handleAvatarChange);
});

function fetchUserInfo(token) {
  fetch(`${config.baseURL}/users/`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
    .then((res) => res.json())
    .then((user) => {
      document.querySelector('.name').textContent = user.nickname || user.username;
      document.querySelector('.username').textContent = `@${user.username}`;
      document.querySelector('.info').innerHTML = `
        <p><strong>Email:</strong> ${user.email}</p>
        <p><strong>Tham gia:</strong> ${new Date(user.created_at_UTC).toLocaleDateString()}</p>
        <p><strong>Hoạt động gần nhất:</strong> ${formatVNTime(user.last_active_UTC)}</p>
      `;

      const avatar = document.querySelector('.avatar');
      avatar.src = user.avatar_url ? `${config.baseURL}/${user.avatar_url.replace(/^\/+/, '')}` : '../../assets/image/private-chat-default.jpg';
      avatar.onerror = () => {
        avatar.src = '../../assets/image/private-chat-default.jpg';
      };
    })
    .catch((err) => {
      toast({
        title: 'Lỗi',
        message: 'Không thể tải thông tin người dùng.',
        type: 'error',
        duration: 3000,
      });
      console.error(err);
    });
}

function handleAvatarChange(e) {
  avatarFile = e.target.files[0];
}

function openUpdateModal(token) {
  createModal({
    title: 'Cập nhật thông tin',
    message: `
      <form id="update-form" enctype="multipart/form-data">
        <label>Nickname:</label>
        <input type="text" id="nickname-input" placeholder="Nhập nickname mới"/><br><br>
        <label>Email:</label>
        <input type="email" id="email-input" placeholder="Nhập email mới"/><br><br>
        <label>Chọn ảnh đại diện:</label>
        <input type="file" id="avatar-modal-upload"/><br><br>
      </form>
    `,
    primaryButtonText: 'Lưu',
    onPrimary: () => handleUpdate(token),
    showSecondaryButton: true,
    secondaryButtonText: 'Hủy',
  });

  // Gắn sự kiện chọn avatar
  setTimeout(() => {
    document.getElementById('avatar-modal-upload').addEventListener('change', (e) => {
      avatarFile = e.target.files[0];
    });
  }, 0);
}

function handleUpdate(token) {
  const nickname = document.getElementById('nickname-input').value;
  const email = document.getElementById('email-input').value;

  const formData = new FormData();
  if (avatarFile) formData.append('avatar_file', avatarFile);

  const query = [];
  if (nickname) query.push(`nickname=${encodeURIComponent(nickname)}`);
  if (email) query.push(`email=${encodeURIComponent(email)}`);
  const queryString = query.length ? '?' + query.join('&') : '';

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
      fetchUserInfo(token); // reload lại avatar và info
    })
    .catch((err) => {
      toast({
        title: 'Lỗi',
        message: err.message,
        type: 'error',
        duration: 3000,
      });
    });
}
