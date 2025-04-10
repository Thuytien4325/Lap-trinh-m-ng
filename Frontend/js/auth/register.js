// register.js
import { toast } from '../untils.js';
import config from '../config.js';

document.addEventListener('DOMContentLoaded', () => {
  const registerForm = document.getElementById('registerForm');
  const API_BASE = 'http://localhost:8000/auth';

  const passwordField = document.getElementById('password');
  const confirmPasswordField = document.getElementById('comfirmpassword');
  const passwordError = document.getElementById('passwordError');

  function validatePassword(password) {
    const regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
    return regex.test(password);
  }

  function checkPasswordMatch() {
    passwordError.innerHTML = '';
    if (!validatePassword(passwordField.value)) {
      passwordError.textContent = 'Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường, số và ký tự đặc biệt.';
    } else if (passwordField.value !== confirmPasswordField.value && confirmPasswordField.value.length > 0) {
      passwordError.textContent = 'Mật khẩu nhập lại không khớp.';
    }
  }

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

  if (registerForm && passwordField && confirmPasswordField && passwordError) {
    passwordField.addEventListener('input', checkPasswordMatch);
    confirmPasswordField.addEventListener('input', checkPasswordMatch);

    let canSubmit = true;
    let submitAttempts = 0;
    const maxSubmitAttempts = 2;
    const attemptTimeFrame = 5000;

    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
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
      const nickname = document.getElementById('nickname').value.trim();
      const email = document.getElementById('email').value.trim();
      const password = passwordField.value;

      try {
        const res = await fetch(`${config.baseURL}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, nickname, email, password }),
        });
        const result = await res.json();

        if (result.access_token) {
          const now = Date.now();

          // Lưu token và thời gian
          localStorage.setItem('access_token', result.access_token);
          localStorage.setItem('refresh_token', result.refresh_token);
          localStorage.setItem('user', JSON.stringify(result.user));

          localStorage.setItem('login_time', now.toString());
          localStorage.setItem('access_token_time', result.access_token_time);
          localStorage.setItem('refresh_token_time', result.refresh_token_time);
          toast({
            title: 'Đăng ký thành công',
            message: 'Bạn đã đăng ký tài khoản thành công!',
            type: 'success',
          });
          setTimeout(() => {
            window.location.href = '../users/chat.html';
          }, 1500);
        } else {
          toast({
            title: 'Đăng ký thất bại',
            message: result.detail.includes('Tên đăng nhập')
              ? 'Tên đăng nhập đã tồn tại!'
              : result.detail.includes('Email')
              ? 'Email đã được sử dụng!'
              : 'Email không tồn tại.',
            type: 'error',
          });
        }
      } catch (error) {
        toast({
          title: 'Lỗi máy chủ',
          message: 'Không thể kết nối đến server. Thử lại sau.',
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
