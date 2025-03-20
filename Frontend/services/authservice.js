const API_BASE = "http://localhost:8000/api";

async function callAPI(endpoint, method = "GET", data = null) {
  const config = {
    method,
    headers: {
      "Content-Type": "application/json",
    },
  };
  if (data) config.body = JSON.stringify(data);

  const response = await fetch(`${API_BASE}${endpoint}`, config);
  return response.json();
}

document.addEventListener("DOMContentLoaded", () => {
  // 🔐 LOGIN
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = document.getElementById("loginUsername").value.trim();
      const password = document.getElementById("loginPassword").value.trim();
      const errorDiv = document.getElementById("loginError");

      if (!username || !password) return (errorDiv.textContent = "Nhập đủ thông tin đi má ơi 😤");
      errorDiv.textContent = "Đang kiểm tra... đừng run nhen 🤨";

      try {
        const data = await callAPI("/login", "POST", { username, password });
        if (data.success) {
          errorDiv.textContent = "Đăng nhập thành công! 🥳";
          setTimeout(() => (window.location.href = "chat.html"), 1000);
        } else {
          errorDiv.textContent = data.message || "Sai tài khoản hoặc mật khẩu 😢";
        }
      } catch (err) {
        console.error(err);
        errorDiv.textContent = "Lỗi server, thử lại sau!";
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

      if (!username || !email || !password || !confirm)
        return (errorDiv.textContent = "Điền đầy đủ thông tin nha má!");
      if (password !== confirm) return (errorDiv.textContent = "Mật khẩu xác nhận không khớp 😤");

      try {
        const data = await callAPI("/register", "POST", { username, email, password });
        if (data.success) {
          alert("Đăng ký thành công, đăng nhập liền nha!");
          window.location.href = "login.html";
        } else {
          errorDiv.textContent = data.message || "Đăng ký thất bại 😔";
        }
      } catch (err) {
        console.error(err);
        errorDiv.textContent = "Lỗi server, thử lại sau!";
      }
    });
  }

  // 🧠 FORGOT PASSWORD
  const forgotForm = document.getElementById("forgotForm");
  if (forgotForm) {
    forgotForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("emailInput").value.trim();
      const errorDiv = document.getElementById("forgotError");
      if (!email) return (errorDiv.textContent = "Nhập email trước cái đã nhen!");

      try {
        const data = await callAPI("/forgot-password", "POST", { email });
        if (data.success) {
          errorDiv.textContent = "Đã gửi mail! Kiểm tra hộp thư nha ✉️";
        } else {
          errorDiv.textContent = data.message || "Không tìm thấy email 😥";
        }
      } catch (err) {
        console.error(err);
        errorDiv.textContent = "Lỗi hệ thống rồi má ơi 😵";
      }
    });
  }

  // 🔁 RESET PASSWORD
  const resetForm = document.getElementById("resetForm");
  if (resetForm) {
    const errorDiv = document.getElementById("resetError");
    const token = new URLSearchParams(window.location.search).get("token");

    // ✅ Kiểm tra token ngay khi load trang
    if (!token) {
      errorDiv.textContent = "Link không hợp lệ hoặc thiếu token 😵";
      setTimeout(() => (window.location.href = "login.html"), 3000);
      return;
    }

    resetForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const password = document.getElementById("newPassword").value.trim();
      const confirm = document.getElementById("confirmPassword").value.trim();

      if (!password || !confirm) return (errorDiv.textContent = "Nhập mật khẩu đầy đủ nhen!");
      if (password !== confirm) return (errorDiv.textContent = "Mật khẩu không trùng 😤");

      try {
        const data = await callAPI("/reset-password", "POST", { token, new_password: password });
        if (data.success) {
          alert("Đặt lại mật khẩu thành công!");
          window.location.href = "login.html";
        } else {
          errorDiv.textContent = data.message || "Đặt lại thất bại 😢";
        }
      } catch (err) {
        console.error(err);
        errorDiv.textContent = "Lỗi server, thử lại sau!";
      }
    });
  }

  // ❌ NÚT ĐÓNG FORM
  const closeBtn = document.getElementById("closeLogin");
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      window.close();
      setTimeout(() => {
        window.location.href = "about:blank";
      }, 100);
    });
  }
});
