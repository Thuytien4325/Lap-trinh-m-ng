import { toast } from './toast.js';

document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form');
  const passwordInput = document.getElementById('password');
  const confirmPasswordInput = document.getElementById('comfirmpassword');
  const passwordError = document.getElementById('passwordError');

  const urlParams = new URLSearchParams(window.location.search);
  const reset_uuid = urlParams.get('uuid');

  function validatePassword(password) {
    const regex =
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
    return regex.test(password);
  }

  function checkPasswordMatch() {
    passwordError.innerHTML = '';
    if (!validatePassword(passwordInput.value)) {
      passwordError.textContent =
        'Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường, số và ký tự đặc biệt.';
    } else if (
      passwordInput.value !== confirmPasswordInput.value &&
      confirmPasswordInput.value.length > 0
    ) {
      passwordError.textContent = 'Mật khẩu nhập lại không khớp.';
    }
  }

  // Kiểm tra UUID từ URL
  if (!reset_uuid) {
    toast({
      title: 'Lỗi',
      message: 'Không tìm thấy mã xác nhận. Vui lòng thử lại.',
      type: 'error',
    });
    return;
  }

  const togglePassword1 = document.getElementById('togglePassword1');
  const togglePassword2 = document.getElementById('togglePassword2');

  togglePassword1.addEventListener('click', () => {
    const type = passwordInput.type === 'password' ? 'text' : 'password';
    passwordInput.type = type;
    togglePassword1.querySelector('i').classList.toggle('fa-eye-slash');
  });

  togglePassword2.addEventListener('click', () => {
    const type = confirmPasswordInput.type === 'password' ? 'text' : 'password';
    confirmPasswordInput.type = type;
    togglePassword2.querySelector('i').classList.toggle('fa-eye-slash');
  });

  passwordInput.addEventListener('input', checkPasswordMatch);
  confirmPasswordInput.addEventListener('input', checkPasswordMatch);

  let canSubmit = true;
  let submitAttempts = 0;
  const maxSubmitAttempts = 2;
  const attemptTimeFrame = 5000;

  // Xử lý submit form
  form.addEventListener('submit', async (e) => {
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

    const password = passwordInput.value.trim();
    const confirmPassword = confirmPasswordInput.value.trim();

    checkPasswordMatch();

    if (!password || !confirmPassword) {
      passwordError.textContent = 'Vui lòng nhập đầy đủ thông tin!';
      return;
    }

    if (password !== confirmPassword) {
      passwordError.textContent = 'Mật khẩu không khớp!';
      return;
    }

    try {
      const response = await fetch(
        'http://127.0.0.1:8000/auth/password/reset-confirm',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            reset_uuid,
            new_password: password,
          }),
        }
      );

      const result = await response.json();

      if (response.ok) {
        toast({
          title: 'Thành công',
          message: result.message || 'Mật khẩu đã được thay đổi thành công.',
          type: 'success',
        });
        setTimeout(() => {
          window.location.href = 'login.html';
        }, 1500);
      } else {
        toast({
          title: 'Lỗi',
          message: result.detail || 'Có lỗi xảy ra. Thử lại sau.',
          type: 'error',
        });
      }
    } catch (err) {
      toast({
        title: 'Lỗi',
        message: 'Không thể kết nối đến máy chủ. Thử lại sau.',
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
});
