document.addEventListener("DOMContentLoaded", function () {
    // Mặc định tải Dashboard
    loadContent("assets/dashboard.html");

    document.querySelectorAll(".nav-button").forEach(button => {
        button.addEventListener("click", function (e) {
            e.preventDefault();
            document.querySelectorAll(".nav-button").forEach(b => b.classList.remove("active"));
            this.classList.add("active");

            if (this.id === "logout-button") {
                // Xử lý đăng xuất
                window.location.href = "login.html"; // Thay bằng trang đăng nhập của bạn
            } else {
                let page = this.getAttribute("data-page");
                if (page) {
                    loadContent(`assets/${page}`);
                }
            }
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
            // Gọi fetchData() để cập nhật dữ liệu từ API sau khi tải nội dung
            fetchData();
        })
        .catch(error => console.error("Lỗi tải nội dung:", error));
}

// Lấy dữ liệu từ API
async function fetchData() {
    try {
        let response = await fetch("http://127.0.0.1:8000/auth");
        let data = await response.json();

        // Cập nhật dữ liệu cho các mục
        const userCount = document.getElementById("userCount");
        const groupCount = document.getElementById("groupCount");
        const reportCount = document.getElementById("reportCount");
        const processStatus = document.getElementById("processStatus");

        if (userCount) userCount.textContent = data.users ?? 0;
        if (groupCount) groupCount.textContent = data.groups ?? 0;
        if (reportCount) reportCount.textContent = data.reports ?? 0;
        if (processStatus) processStatus.textContent = data.process ?? "Unknown";

        // Nếu bạn muốn giữ biểu đồ (tùy chọn)
        if (document.getElementById("myChart")) {
            updateChart(data.users ?? 0, data.groups ?? 0, data.reports ?? 0);
        }
    } catch (error) {
        console.error("Lỗi tải dữ liệu:", error);
    }
}

// Vẽ biểu đồ (tùy chọn, nếu bạn muốn giữ)
let chartInstance;
function updateChart(users, groups, reports) {
    let chartCanvas = document.getElementById("myChart");
    if (!chartCanvas) return;

    const ctx = chartCanvas.getContext("2d");

    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Người dùng", "Nhóm", "Báo cáo"],
            datasets: [{
                label: "Số lượng",
                data: [users, groups, reports],
                backgroundColor: ["#f39c12", "#3498db", "#e74c3c"]
            }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
    });
}