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
          const now = Date.now();

          // Lưu token và thời gian
          localStorage.setItem('access_token', result.access_token);
          localStorage.setItem('refresh_token', result.refresh_token);
          localStorage.setItem('user', JSON.stringify(result.user));

          localStorage.setItem('login_time', now.toString());
          localStorage.setItem('access_token_time', result.access_token_time);
          localStorage.setItem('refresh_token_time', result.refresh_token_time);
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
