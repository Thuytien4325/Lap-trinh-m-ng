// login.js
import { toast } from './toast.js';

document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.getElementById('loginForm');
  const API_BASE = 'http://localhost:8000/auth';

  if (loginForm) {
    loginForm.addEventListener('submit', async function (event) {
      event.preventDefault();

      const username = document.getElementById('username').value.trim();
      const password = document.getElementById('password').value;

      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      formData.append('grant_type', 'password');

      try {
        const response = await fetch(`${API_BASE}/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formData,
        });

        const result = await response.json();

        if (response.ok && result.access_token) {
          localStorage.setItem('userToken', result.access_token);
          toast({
            title: 'Đăng nhập thành công',
            message: 'Chào mừng bạn quay trở lại!',
            type: 'success',
          });
          setTimeout(() => {
            window.location.href = '../HTML/chat.html';
          }, 1500);
        } else {
          toast({
            title: 'Đăng nhập thất bại',
            message: result.detail || 'Sai tài khoản hoặc mật khẩu!',
            type: 'error',
          });
        }
      } catch (error) {
        toast({
          title: 'Lỗi mạng',
          message: 'Không thể kết nối đến máy chủ. Vui lòng thử lại.',
          type: 'error',
        });
      }
    });
  }
});
