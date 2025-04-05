document.addEventListener('DOMContentLoaded', () => {
  const togglePasswordButtons = document.querySelectorAll('.toggle-password');
  togglePasswordButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const passwordInput = button.previousElementSibling;
      const icon = button.querySelector('i');
      passwordInput.type =
        passwordInput.type === 'password' ? 'text' : 'password';
      icon.classList.toggle('fa-eye');
      icon.classList.toggle('fa-eye-slash');
    });
  });

  const API_BASE = 'http://localhost:8000/auth';
  const registerForm = document.getElementById('registerForm');
  const loginForm = document.getElementById('loginForm');
  const passwordField = document.getElementById('password');
  const confirmPasswordField = document.getElementById('comfirmpassword');
  const passwordError = document.getElementById('passwordError');

  // Call API helper function
  async function callAPI(endpoint, method = 'POST', data = null) {
    const config = { method, headers: { 'Content-Type': 'application/json' } };
    if (data) config.body = JSON.stringify(data);

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, config);
      const result = await response.json();
      return result;
    } catch (error) {
      return { success: false, message: 'Lỗi kết nối server!' };
    }
  }

  // Password validation function (regex for strong password)
  function validatePassword(password) {
    const regex =
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
    return regex.test(password);
  }

  // Check password strength and matching
  function checkPasswordMatch() {
    passwordError.innerHTML = ''; // Clear previous errors
    if (passwordField && confirmPasswordField) {
      if (!validatePassword(passwordField.value)) {
        passwordError.textContent =
          'Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường, số và ký tự đặc biệt.';
      } else if (
        passwordField.value !== confirmPasswordField.value &&
        confirmPasswordField.value.length > 0
      ) {
        passwordError.textContent = 'Mật khẩu nhập lại không khớp.';
      }
    }
  }

  function toast({ title = '', message = '', type = 'info', duration = 3000 }) {
    const main = document.getElementById('toast');
    if (main) {
      const toast = document.createElement('div');
      const autoRemoteID = setTimeout(function () {
        main.removeChild(toast);
      }, duration + 1000);

      toast.onclick = function (e) {
        if (e.target.closest('.toast__close')) {
          main.removeChild(toast);
          clearTimeout(autoRemoteID);
        }
      };

      const icons = {
        info: 'fa-solid fa-circle-info',
        success: 'fa-solid fa-circle-check',
        warning: 'fa-solid fa-triangle-exclamation',
        error: 'fa-solid fa-circle-xmark',
      };

      const icon = icons[type];
      const delay = (duration / 1000).toFixed(2);
      toast.classList.add('toast', `toast--${type}`);
      toast.style.animation = `slideInLeft ease 0.3s, fadeOut linear 1s ${delay}s forwards`;
      toast.innerHTML = `
                        <div class="toast__icon">
                            <i class="${icon}"></i>
                        </div>
                        <div class="toast__body">
                            <h3 class="toast__title">${title}</h3>
                            <p class="toast__msg">${message}</p>
                        </div>
                        <div class="toast__close">
                            <i class="fa-solid fa-xmark"></i>
                        </div>
                    `;
      main.appendChild(toast);
    }
  }

  // Add event listeners for password inputs
  passwordField.addEventListener('input', checkPasswordMatch);
  confirmPasswordField.addEventListener('input', checkPasswordMatch);

  let canSubmit = true;
  let submitAttempts = 0;
  const maxSubmitAttempts = 2;
  const attemptTimeFrame = 5000;

  // Register form submission handler
  if (registerForm) {
    registerForm.addEventListener('submit', async function (event) {
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
      const nickname = document.getElementById('nickname').value.trim();
      const email = document.getElementById('email').value.trim();
      const password = passwordField.value;

      // Call the API to register user
      const result = await callAPI('/register', 'POST', {
        username,
        nickname,
        email,
        password,
      });
      if (result.access_token) {
        toast({
          title: 'Đăng ký thành công',
          message: 'Bạn đã đăng ký tài khoản thành công!',
          type: 'success',
        });
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

      setTimeout(function () {
        canSubmit = true;
        submitButton.disabled = false;
      }, 1000);

      setTimeout(function () {
        submitAttempts = 0;
      }, attemptTimeFrame);
    });
  }

  // Login form submission handler
  if (loginForm) {
    loginForm.addEventListener('submit', async function (event) {
      event.preventDefault();
      const loginError = document.getElementById('loginError');
      loginError.innerHTML = '';

      const username = document.getElementById('username').value.trim();
      const password = document.getElementById('password').value;

      // Call the API to log in
      const result = await callAPI('/login', 'POST', { username, password });
      if (result.access_token) {
        localStorage.setItem('userToken', result.token);
        window.location.href = '../Tin nhan/chat.html';
      } else {
        loginError.textContent = 'Sai tài khoản hoặc mật khẩu!';
      }
    });
  }
});
