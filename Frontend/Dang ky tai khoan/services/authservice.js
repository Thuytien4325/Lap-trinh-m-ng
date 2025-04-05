<<<<<<< HEAD
document.addEventListener("DOMContentLoaded", () => {
    const togglePasswordButtons = document.querySelectorAll(".toggle-password");
    togglePasswordButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const passwordInput = button.previousElementSibling;
            const icon = button.querySelector("i");
            passwordInput.type = passwordInput.type === "password" ? "text" : "password";
            icon.classList.toggle("fa-eye");
            icon.classList.toggle("fa-eye-slash");
        });
    });

    const API_BASE = "http://localhost:8000/auth";
    const registerForm = document.getElementById("registerForm");
    const loginForm = document.getElementById("loginForm");
    const errorBox = document.getElementById("registerError");
    const passwordField = document.getElementById("password");
    const confirmPasswordField = document.getElementById("comfirmpassword");
    const passwordError = document.getElementById("passwordError");

    async function callAPI(endpoint, method = "POST", data = null) {
        const config = { method, headers: { "Content-Type": "application/json" } };
        if (data) config.body = JSON.stringify(data);

        try {
            const response = await fetch(`${API_BASE}${endpoint}`, config);
            const result = await response.json();
            return result;
        } catch (error) {
            return { success: false, message: "Lỗi kết nối server!" };
        }
    }


    if (registerForm) {
        registerForm.addEventListener("submit", async function (event) {
            event.preventDefault();
            errorBox.innerHTML = "";

            const username = document.getElementById("username").value.trim();
            const nickname = document.getElementById("nickname").value.trim();
            const email = document.getElementById("email").value.trim();
            const password = passwordField.value;

            if (!validatePassword(password)) {
                errorBox.textContent = "Mật khẩu không đủ mạnh!";
                return;
            }
            if (password !== confirmPasswordField.value) {
                errorBox.textContent = "Mật khẩu nhập lại không khớp.";
                return;
            }

            const result = await callAPI("/register", "POST", { username, nickname, email, password });
            if (result.success) {
                errorBox.textContent = "Đăng ký thành công! Đang tự động đăng nhập...";
                setTimeout(() => (window.location.href = "../Tin nhan/chat.html"), 1000);
            } else {
                errorBox.textContent = result.message.includes("username") ? "Tên đăng nhập đã tồn tại!" : 
                                       result.message.includes("email") ? "Email đã được sử dụng!" : 
                                       "Đăng ký thất bại.";
            }
        });
    }z

    if (loginForm) {
        loginForm.addEventListener("submit", async function (event) {
            event.preventDefault();
            const loginError = document.getElementById("loginError");
            loginError.innerHTML = "";

            const username = document.getElementById("username").value.trim();
            const password = document.getElementById("password").value;

            const result = await callAPI("/login", "POST", { username, password });
            if (result.acces_token) {
                localStorage.setItem("userToken", result.token);
                window.location.href = "../Tin nhan/chat.html";
            } else {
                loginError.textContent = "Sai tài khoản hoặc mật khẩu!";
            }
        });
    }
=======
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
  const errorBox = document.getElementById('registerError');
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

  // Add event listeners for password inputs
  passwordField.addEventListener('input', checkPasswordMatch);
  confirmPasswordField.addEventListener('input', checkPasswordMatch);

  // Register form submission handler
  if (registerForm) {
    registerForm.addEventListener('submit', async function (event) {
      event.preventDefault();
      errorBox.innerHTML = '';

      const username = document.getElementById('username').value.trim();
      const nickname = document.getElementById('nickname').value.trim();
      const email = document.getElementById('email').value.trim();
      const password = passwordField.value;

      // Validate password
      if (!validatePassword(password)) {
        errorBox.textContent = 'Mật khẩu không đủ mạnh!';
        return;
      }
      if (password !== confirmPasswordField.value) {
        errorBox.textContent = 'Mật khẩu nhập lại không khớp.';
        return;
      }

      // Call the API to register user
      const result = await callAPI('/register', 'POST', {
        username,
        nickname,
        email,
        password,
      });
      if (result.access_token) {
        errorBox.textContent = 'Đăng ký thành công! Đang tự động đăng nhập...';
        // setTimeout(
        //   () => (window.location.href = '../Tin nhan/chat.html'),
        //   1000
        // );
        errorBox.style.display = 'block';
      } else {
        errorBox.textContent = result.detail.includes('Tên đăng nhập')
          ? 'Tên đăng nhập đã tồn tại!'
          : result.detail.includes('Email')
          ? 'Email đã được sử dụng!'
          : 'Email không tồn tại.';
        errorBox.style.display = 'block';
      }
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
>>>>>>> 59a3c6e1e68ef0e5606404c737c7dc7d285bbeb3
});
