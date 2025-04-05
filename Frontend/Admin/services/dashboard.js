document.addEventListener("DOMContentLoaded", function () {
    // Mặc định tải Dashboard
    loadContent("assets/dashboard.html");

    document.querySelectorAll(".nav-link").forEach(link => {
        link.addEventListener("click", function (e) {
            e.preventDefault();
            let page = this.getAttribute("data-page");
            loadContent(`assets/${page}`);

            // Xóa active khỏi tất cả mục
            document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
            // Thêm active vào mục đang chọn
            this.classList.add("active");
        });
    });
});

// Hàm tải nội dung trang
function loadContent(page) {
    fetch(page)
        .then(response => {
            if (!response.ok) throw new Error("Trang không tồn tại");
            return response.text();
        })
        .then(html => {
            document.getElementById("main-content").innerHTML = html;
            if (page.includes("dashboard")) fetchData();
        })
        .catch(error => console.error("Lỗi tải nội dung:", error));
}

// Lấy dữ liệu từ API
async function fetchData() {
    try {
        let response = await fetch("http://127.0.0.1:8000/auth");
        let data = await response.json();

        document.getElementById("userCount").textContent = data.users ?? 0;
        document.getElementById("messageCount").textContent = data.messages ?? 0;
        document.getElementById("settingsCount").textContent = data.settings ?? 0;

        updateChart(data.users, data.messages, data.settings);
    } catch (error) {
        console.error("Lỗi tải dữ liệu:", error);
    }
}

// Vẽ biểu đồ
let chartInstance;
function updateChart(users, messages, settings) {
    let chartCanvas = document.getElementById("myChart");
    if (!chartCanvas) return; // Kiểm tra nếu chưa có phần tử

    const ctx = chartCanvas.getContext("2d");

    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Người dùng", "Tin nhắn", "Cài đặt"],
            datasets: [{
                label: "Số lượng",
                data: [users, messages, settings],
                backgroundColor: ["#f39c12", "#3498db", "#e74c3c"]
            }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
    });
}
