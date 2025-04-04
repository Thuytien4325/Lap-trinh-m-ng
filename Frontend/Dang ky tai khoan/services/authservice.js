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

    function validatePassword(password) {
        const regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
        return regex.test(password);
    }

    function checkPasswordMatch() {
        passwordError.innerHTML = "";
        if (!validatePassword(passwordField.value)) {
            passwordError.textContent = "Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường, số và ký tự đặc biệt.";
        } else if (passwordField.value !== confirmPasswordField.value && confirmPasswordField.value.length > 0) {
            passwordError.textContent = "Mật khẩu nhập lại không khớp.";
        }
    }

    passwordField.addEventListener("input", checkPasswordMatch);
    confirmPasswordField.addEventListener("input", checkPasswordMatch);

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
            if (result.success) {
                localStorage.setItem("userToken", result.token);
                window.location.href = "../Tin nhan/chat.html";
            } else {
                loginError.textContent = "Sai tài khoản hoặc mật khẩu!";
            }
        });
    }
});
