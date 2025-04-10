// login.js
import { toast } from '../untils.js';
import config from '../config.js';
console.log('BASE URL:', config.baseURL);

document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.getElementById('loginForm');

  document.querySelectorAll('.toggle-password').forEach((btn) => {
    btn.addEventListener('click', () => {
      const input = btn.previousElementSibling;
      if (!input) return;

      const icon = btn.querySelector('i');
      const isPassword = input.getAttribute('type') === 'password';

      input.setAttribute('type', isPassword ? 'text' : 'password');
      icon.classList.toggle('fa-eye');
      icon.classList.toggle('fa-eye-slash');
    });
  });

  if (loginForm) {
    let canSubmit = true;
    let submitAttempts = 0;
    const maxSubmitAttempts = 2;
    const attemptTimeFrame = 5000;

    loginForm.addEventListener('submit', async function (event) {
      event.preventDefault();

      const submitButton = document.querySelector('.submit-btn');
      if (submitAttempts >= maxSubmitAttempts) {
        toast({
          title: 'Quá tải',
          message: 'Bạn đã nhấn quá nhiều lần. Vui lòng thử lại sau.',
          type: 'warning',
        });
        return;
      }

      if (!canSubmit) return;
      canSubmit = false;
      submitAttempts++;
      submitButton.disabled = true;

      const username = document.getElementById('username').value.trim();
      const password = document.getElementById('password').value;

      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      formData.append('grant_type', 'password');

      try {
        const response = await fetch(`${config.baseURL}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formData,
        });

        const result = await response.json();
        if (response.ok && result.user.username === 'admin') {
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
            message: 'Xin chào Admin!',
            type: 'success',
          });
          setTimeout(() => {
            window.location.href = '../../html/admin/admin.html';
          }, 1500);
        } else {
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
              window.location.href = '../../html/users/chat.html';
            }, 1500);
          } else {
            toast({
              title: 'Đăng nhập thất bại',
              message: result.detail || 'Sai tài khoản hoặc mật khẩu!',
              type: 'error',
            });
          }
        }
      } catch (error) {
        console.error('Lỗi:', error);
        toast({
          title: 'Lỗi mạng',
          message: 'Không thể kết nối đến máy chủ. Vui lòng thử lại.',
          type: 'error',
        });
      }

      setTimeout(() => {
        canSubmit = true;
        submitButton.disabled = false;
      }, 1000);
      setTimeout(() => {
        submitAttempts = 0;
      }, attemptTimeFrame);
    });
  }
});
