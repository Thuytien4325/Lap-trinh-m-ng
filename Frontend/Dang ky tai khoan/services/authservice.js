//  ĐÓNG FORM 
const closeBtn = document.getElementById("closeLogin");
if (closeBtn) {
  closeBtn.addEventListener("click", () => {
    const confirmClose = confirm("Bạn có chắc muốn rời khỏi trang không?");
    if (confirmClose) {
      if (window.location.pathname.endsWith("index.html")) {
        window.close(); // Đóng trình duyệt nếu đang ở index.html
      } else {
        window.location.href = "http://127.0.0.1:5500/Frontend/Dang%20ky%20tai%20khoan/index.html"; // Quay về index.html nếu không phải
      }
    }
  });   
}

// Xử lý API 
const API_BASE = "http://localhost:8000/auth";

async function callAPI(endpoint, method = "GET", data = null) {
    const config = { method, headers: { "Content-Type": "application/json" } };
    if (data) config.body = JSON.stringify(data);

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, config);
        if (!response.ok) throw new Error("Lỗi server!");
        return await response.json();
    } catch (error) {
        console.error("Lỗi API:", error);
        return { success: false, message: "Lỗi kết nối server!" };
    }
}

async function loginAPI(username, password) {
    return await callAPI("/login", "POST", { username, password });
}

async function registerAPI(username, nickname, email, password) {
    return await callAPI("/register", "POST", { username, nickname, email, password });
}

async function loginJSON(username, password) {
    try {
        const response = await fetch('../../assets/data/users.json');
        const users = await response.json();

        return users.find(u => u.username === username && u.password === password) || null;
    } catch (error) {
        console.error("Lỗi đọc file JSON:", error);
        return null;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");

    function clearError(id) {
        const errorDiv = document.getElementById(id);
        if (errorDiv) errorDiv.textContent = "";
    }

    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const usernameInput = document.getElementById("loginUsername");
            const passwordInput = document.getElementById("loginPassword");
            const errorDiv = document.getElementById("loginError");
            clearError("loginError");

            usernameInput.addEventListener("input", () => clearError("loginError"));
            passwordInput.addEventListener("input", () => clearError("loginError"));

            const username = usernameInput.value.trim();
            const password = passwordInput.value.trim();

            if (!username || !password) {
                errorDiv.textContent = "Vui lòng nhập đầy đủ thông tin!";
                return;
            }

            let userData = await loginAPI(username, password);
            if (!userData) {
                userData = await loginJSON(username, password);
            }

            if (userData) {
                errorDiv.textContent = "Đăng nhập thành công!";
                setTimeout(() => (window.location.href = "chat.html"), 1000);
            } else {
                errorDiv.textContent = "Sai tài khoản hoặc mật khẩu!";
            }
        });
    }

    function validatePassword(password) {
        const strongPassword = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
        return strongPassword.test(password);
    }

    function setupPasswordValidation(formId, passwordId, confirmPasswordId, errorId) {
        const form = document.getElementById(formId);
        if (!form) return;

        const passwordField = document.getElementById(passwordId);
        const confirmPasswordField = document.getElementById(confirmPasswordId);
        const errorDiv = document.getElementById(errorId);
        const submitButton = form.querySelector("button[type='submit']");

        function validateInputs() {
            errorDiv.textContent = "";
            submitButton.disabled = false;

            if (passwordField.value.length > 0 && !validatePassword(passwordField.value)) {
                errorDiv.textContent = "Mật khẩu yếu!";
                submitButton.disabled = true;
                return;
            }

            if (passwordField.value !== confirmPasswordField.value) {
                errorDiv.textContent = "Mật khẩu không khớp!";
                submitButton.disabled = true;
            }
        }

        passwordField.addEventListener("input", validateInputs);
        confirmPasswordField.addEventListener("input", validateInputs);
    }

    setupPasswordValidation("registerForm", "registerPassword", "registerConfirm", "registerError");
    setupPasswordValidation("resetForm", "newPassword", "confirmPassword", "resetError");

    if (registerForm) {
        registerForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = document.getElementById("registerUsername").value.trim();
            const nickname = document.getElementById("registerNickname").value.trim();
            const email = document.getElementById("registerEmail").value.trim();
            const password = document.getElementById("registerPassword").value.trim();
            const errorDiv = document.getElementById("registerError");

            if (!validatePassword(password)) {
                errorDiv.textContent = "Mật khẩu không đủ mạnh!";
                return;
            }
            const result = await registerAPI(username, nickname, email, password);
            if (result.success) {
                errorDiv.textContent = "Đăng ký thành công! Đang tự động đăng nhập...";
                
                // Tự đăng nhập và chuyển qua chat 
                const loginResult = await loginAPI(username, password);
                if (loginResult.success) {
                    setTimeout(() => (window.location.href = "../Tin nhan/chat.html"), 1000);
                } else {
                    errorDiv.textContent = "Đăng ký thành công, nhưng lỗi khi tự động đăng nhập!";
                    setTimeout(() => (window.location.href = "../../assets/HTML/login.html" ), 1000);
                }
            } else {
                errorDiv.textContent = result.message;
            }
        });
    }
    
});
