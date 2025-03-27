const API_BASE = "http://localhost:8000/api"; // Nếu có API, thay đổi URL tại đây

// 🛠 Hàm gọi API hoặc lấy dữ liệu từ JSON
async function callAPI(endpoint, method = "GET", data = null, isJSON = false) {
  const config = {
    method,
    headers: {
      "Content-Type": "application/json",
    },
  };
  if (data) config.body = JSON.stringify(data);

  try {
    if (isJSON) {
      const response = await fetch(endpoint);
      return await response.json();
    } else {
      const response = await fetch(`${API_BASE}${endpoint}`, config);
      return await response.json();
    }
  } catch (error) {
    console.error("Lỗi API:", error);
    return { success: false, message: "Lỗi kết nối server!" };
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  // 🔐 LOGIN
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = document.getElementById("loginUsername").value.trim();
      const password = document.getElementById("loginPassword").value.trim();
      const errorDiv = document.getElementById("loginError");

      if (!username || !password) {
        errorDiv.textContent = "Vui lòng điền đầy đủ thông tin!";
        return;
      }

      const users = await callAPI("users.json", "GET", null, true);
      const user = users.find((u) => u.username === username && u.password === password);

      if (user) {
        errorDiv.textContent = "Đăng nhập thành công!";
        setTimeout(() => (window.location.href = "chat.html"), 1000);
      } else {
        errorDiv.textContent = "Sai tài khoản hoặc mật khẩu!";
      }
    });
  }

  // 📝 REGISTER
  const registerForm = document.getElementById("registerForm");
  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = document.getElementById("registerUsername").value.trim();
      const email = document.getElementById("registerEmail").value.trim();
      const password = document.getElementById("registerPassword").value.trim();
      const confirm = document.getElementById("registerConfirm").value.trim();
      const errorDiv = document.getElementById("registerError");

      if (!username || !email || !password || !confirm) {
        errorDiv.textContent = "Vui lòng điền đầy đủ thông tin!";
        return;
      }
      if (password !== confirm) {
        errorDiv.textContent = "Mật khẩu không khớp!";
        return;
      }

      alert("Đăng ký thành công!");
      window.location.href = "login.html";
    });
  }

  // 🧠 FORGOT PASSWORD
  const forgotForm = document.getElementById("forgotForm");
  if (forgotForm) {
    forgotForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("emailInput").value.trim();
      const errorDiv = document.getElementById("forgotError");

      if (!email) {
        errorDiv.textContent = "Vui lòng nhập email!";
        return;
      }

      const resetTokens = await callAPI("reset_tokens.json", "GET", null, true);
      const token = resetTokens.find((t) => t.email === email);

      if (token) {
        errorDiv.textContent = "Đã gửi mail! Kiểm tra hộp thư.";
      } else {
        errorDiv.textContent = "Không tìm thấy email!";
      }
    });
  }

  // 🔁 RESET PASSWORD
  const resetForm = document.getElementById("resetForm");
  if (resetForm) {
    const errorDiv = document.getElementById("resetError");
    const token = new URLSearchParams(window.location.search).get("token");

    if (!token) {
      errorDiv.textContent = "Liên kết không hợp lệ!";
      setTimeout(() => (window.location.href = "login.html"), 3000);
      return;
    }

    resetForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const password = document.getElementById("newPassword").value.trim();
      const confirm = document.getElementById("confirmPassword").value.trim();

      if (!password || !confirm) {
        errorDiv.textContent = "Vui lòng nhập mật khẩu!";
        return;
      }
      if (password !== confirm) {
        errorDiv.textContent = "Mật khẩu không khớp!";
        return;
      }

      alert("Đặt lại mật khẩu thành công!");
      window.location.href = "login.html";
    });
  }

  // 📨 HIỂN THỊ TIN NHẮN
  async function loadMessages() {
    const messages = await callAPI("message.json", "GET", null, true);
    console.log("📨 Tin nhắn nhận được:", messages);
  }
  loadMessages();


  
  // ❌ NÚT ĐÓNG FORM VỚI HỘP THOẠI XÁC NHẬN
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
  
  // 🛠 KIỂM TRA MẬT KHẨU HỢP LỆ
  function setupPasswordValidation(formId, passwordId, confirmPasswordId, errorId) {
    const form = document.getElementById(formId);
    if (!form) return;

    const passwordField = document.getElementById(passwordId);
    const confirmPasswordField = document.getElementById(confirmPasswordId);
    const errorDiv = document.getElementById(errorId);
    const submitButton = form.querySelector("button[type='submit']");

    if (!passwordField || !confirmPasswordField || !errorDiv || !submitButton) {
      console.error("Lỗi: Không tìm thấy một trong các phần tử trong form", formId);
      return;
    }

    function validatePasswordMatch() {
      if (passwordField.value.trim() === "" || confirmPasswordField.value.trim() === "") {
        errorDiv.textContent = "";
        submitButton.disabled = true;
        return;
      }

      if (passwordField.value !== confirmPasswordField.value) {
        errorDiv.textContent = "Mật khẩu không khớp!";
        submitButton.disabled = true;
      } else {
        errorDiv.textContent = " ";
        submitButton.disabled = false;
      }
    }

    passwordField.addEventListener("input", validatePasswordMatch);
    confirmPasswordField.addEventListener("input", validatePasswordMatch);
  }

  setupPasswordValidation("registerForm", "registerPassword", "registerConfirm", "registerError");
  setupPasswordValidation("resetForm", "newPassword", "confirmPassword", "resetError");
});



