import { toast } from '../untils.js';
import initContextMenu from '../context-menu.js';
import config from '../config.js';

// Đợi DOM load xong
document.addEventListener('DOMContentLoaded', () => {
  // Tìm các nút report
  const reportUserBtn = document.getElementById('report-user-btn');
  const reportConversationBtn = document.getElementById('report-conversation-btn');

  // Xử lý sự kiện click nút report user
  if (reportUserBtn) {
    reportUserBtn.addEventListener('click', () => {
      const userModal = document.getElementById('user-info-modal');

      if (!userModal) {
        console.error('User modal not found');
        return;
      }

      const userId = userModal.dataset.userId;
      const username = userModal.dataset.username;

      if (!userId) {
        console.error('User ID not found');
        toast({
          title: 'Lỗi',
          message: 'Không thể lấy thông tin người dùng',
          type: 'error',
        });
        return;
      }

      currentReportInfo = {
        type: 'user',
        targetId: userId,
      };

      document.getElementById('report-modal-title').textContent = `Báo cáo người dùng: ${username}`;
      document.getElementById('report-severity-group').style.display = 'none';
      openReportModal();
    });
  } else {
    console.error('Report user button not found');
  }

  // Xử lý sự kiện click nút report conversation
  if (reportConversationBtn) {
    reportConversationBtn.addEventListener('click', () => {
      // Lấy conversation ID từ chat header
      const chatHeader = document.getElementById('chat-header');
      const conversationId = chatHeader.dataset.id;

      if (!conversationId) {
        console.error('Conversation ID not found');
        toast({
          title: 'Lỗi',
          message: 'Không thể lấy thông tin cuộc trò chuyện',
          type: 'error',
        });
        return;
      }

      const titleElement = document.getElementById('conversation-title');
      const conversationTitle = titleElement ? titleElement.textContent : 'Cuộc trò chuyện';

      currentReportInfo = {
        type: 'group',
        targetId: conversationId,
      };

      document.getElementById('report-modal-title').textContent = `Báo cáo cuộc trò chuyện: ${conversationTitle}`;
      document.getElementById('report-severity-group').style.display = 'none';
      openReportModal();
    });
  } else {
    console.error('Report conversation button not found');
  }

  // Thiết lập bộ lọc báo cáo
  setupReportFilters();

  // Lấy danh sách báo cáo khi trang được tải
  fetchReports();
});

// Ngăn chặn menu chuột phải mặc định
document.addEventListener('contextmenu', (e) => {
  // Chỉ cho phép menu chuột phải mặc định trong các trường input và textarea
  if (!(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)) {
    e.preventDefault();
  }
});

// Khởi tạo context menu cho tin nhắn
initContextMenu({
  selector: '.message',
  items: [
    {
      label: 'Sao chép tin nhắn',
      action: 'copy',
    },
    {
      label: 'Tải file',
      action: 'download',
    },
  ],
  onAction: (action, fileUrl, target) => {
    // Kiểm tra nếu target là một phần tử DOM
    if (!(target instanceof Element)) {
      console.error('Target is not a DOM element');
      return;
    }

    const messageElement = target.closest('.message');
    if (!messageElement) {
      console.error('No message element found');
      return;
    }

    if (action === 'copy') {
      const messageText = messageElement.querySelector('.message-text');
      if (!messageText) {
        console.error('No message text found');
        return;
      }

      // Kiểm tra nếu tin nhắn chỉ có file đính kèm
      const attachments = messageElement.querySelector('.attachments');
      if (attachments && !messageText.textContent.trim()) {
        toast({
          title: 'Thông báo',
          message: 'Không thể sao chép tin nhắn chỉ có file đính kèm',
          type: 'info',
        });
        return;
      }

      // Tạo một textarea ẩn để sao chép
      const textarea = document.createElement('textarea');
      textarea.value = messageText.textContent.trim();
      textarea.style.position = 'fixed';
      textarea.style.opacity = 0;
      document.body.appendChild(textarea);
      textarea.select();

      try {
        const successful = document.execCommand('copy');
        if (successful) {
          toast({
            title: 'Thành công',
            message: 'Đã sao chép tin nhắn',
            type: 'success',
          });
        } else {
          throw new Error('Copy failed');
        }
      } catch (err) {
        toast({
          title: 'Lỗi',
          message: 'Không thể sao chép tin nhắn',
          type: 'error',
        });
      } finally {
        document.body.removeChild(textarea);
      }
    } else if (action === 'download') {
      const attachments = messageElement.querySelector('.attachments');
      if (attachments) {
        const fileElements = attachments.querySelectorAll('.file-wrapper, .attachment-img');
        if (fileElements.length > 0) {
          fileElements.forEach((fileEl) => {
            const url = fileEl.getAttribute('data-url');
            if (url) {
              // Lấy tên file từ URL
              const fileName = url.split('/').pop();
              // Tạo URL download từ server
              const downloadUrl = `${config.baseURL}/conversations/download/${messageElement.dataset.messageId}/${fileName}`;
              // Tạo thẻ a ẩn để tải file
              const a = document.createElement('a');
              a.href = downloadUrl;
              a.download = fileName;
              a.style.display = 'none';
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
            }
          });
        } else {
          toast({
            title: 'Thông báo',
            message: 'Tin nhắn này không có file đính kèm',
            type: 'info',
          });
        }
      }
    }
  },
});

// Biến lưu trữ thông tin report hiện tại
let currentReportInfo = {
  type: null, // 'user' hoặc 'group'
  targetId: null,
};

// Mở modal report
function openReportModal() {
  const modal = document.getElementById('report-modal');

  if (!modal) {
    console.error('Report modal not found');
    return;
  }

  modal.style.display = 'flex';
  document.getElementById('report-description').value = '';
  document.getElementById('report-severity').value = 'low';
}

// Đóng modal report
function closeReportModal() {
  const modal = document.getElementById('report-modal');

  if (!modal) {
    console.error('Report modal not found');
    return;
  }

  modal.style.display = 'none';
  currentReportInfo = {
    type: null,
    targetId: null,
  };
}

// Gửi báo cáo
async function submitReport() {
  const description = document.getElementById('report-description').value.trim();

  if (!description) {
    toast({
      title: 'Lỗi',
      message: 'Vui lòng nhập lý do báo cáo',
      type: 'error',
    });
    return;
  }

  try {
    // Lấy token từ localStorage
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Bạn chưa đăng nhập');
    }

    // Tạo URL với query parameters
    const queryParams = new URLSearchParams({
      report_type: currentReportInfo.type === 'user' ? 'user' : 'group',
      target_id: currentReportInfo.targetId,
      description: description,
      severity: document.getElementById('report-severity').value,
    });

    const url = `${config.baseURL}/users/report?${queryParams.toString()}`;
    console.log('Request URL:', url);

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        accept: 'application/json',
        Authorization: `Bearer ${token}`,
      },
    });

    if (response.ok) {
      toast({
        title: 'Thành công',
        message: 'Đã gửi báo cáo thành công',
        type: 'success',
      });
      closeReportModal();
    } else {
      const data = await response.json();
      throw new Error(data.detail || 'Có lỗi xảy ra');
    }
  } catch (error) {
    console.error('Error submitting report:', error);
    toast({
      title: 'Lỗi',
      message: error.message,
      type: 'error',
    });
  }
}

// Lấy danh sách báo cáo
async function fetchReports() {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      console.error('Không tìm thấy token');
      return;
    }

    const response = await fetch(`${config.baseURL}/users/reports`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Lỗi khi lấy danh sách báo cáo');
    }

    const reports = await response.json();
    renderReports(reports);
  } catch (error) {
    console.error('Lỗi:', error);
    toast({
      title: 'Lỗi',
      message: 'Không thể lấy danh sách báo cáo',
      type: 'error',
    });
  }
}

// Hiển thị danh sách báo cáo
function renderReports(reports) {
  const reportItems = document.getElementById('report-items');
  if (!reportItems) return;

  reportItems.innerHTML = '';

  reports.forEach((report) => {
    const reportItem = document.createElement('li');
    reportItem.className = `report-item ${report.status}`;

    const statusText = {
      pending: 'Đang chờ',
      in_progress: 'Đang xử lý',
      resolved: 'Đã xử lý',
    };

    reportItem.innerHTML = `
      <div class="report-item-header">
        <span class="report-item-type">${report.report_type === 'user' ? 'Báo cáo người dùng' : 'Báo cáo nhóm'}</span>
        <span class="report-item-status ${report.status}">${statusText[report.status]}</span>
      </div>
      <div class="report-item-content">
        <p><strong>Mục tiêu:</strong> ${report.target_id}</p>
        <p><strong>Mô tả:</strong> ${report.description}</p>
        <p><strong>Mức độ:</strong> ${report.severity}</p>
      </div>
      <div class="report-item-footer">
        <p>Ngày tạo: ${new Date(report.created_at).toLocaleString()}</p>
      </div>
    `;

    reportItems.appendChild(reportItem);
  });
}

// Xử lý sự kiện khi thay đổi bộ lọc
function setupReportFilters() {
  const filterCheckboxes = document.querySelectorAll('.report-filter');
  filterCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener('change', () => {
      const visibleStatuses = Array.from(filterCheckboxes)
        .filter((cb) => cb.checked)
        .map((cb) => cb.value);

      const reportItems = document.querySelectorAll('.report-item');
      reportItems.forEach((item) => {
        const status = item.classList[1];
        item.style.display = visibleStatuses.includes(status) ? 'block' : 'none';
      });
    });
  });
}

// Hiển thị/ẩn danh sách báo cáo
function toggleReportsList() {
  const friendList = document.getElementById('friend-list');
  const notiList = document.getElementById('noti-list');
  const chatList = document.getElementById('conversation-list');
  const requestList = document.getElementById('friend-request-list');
  const reportList = document.getElementById('reports-list');

  if (!reportList) {
    console.error('Report list not found');
    return;
  }

  const currentDisplay = window.getComputedStyle(reportList).display;

  if (currentDisplay === 'none') {
    // Ẩn các panel còn lại
    [notiList, chatList, requestList, friendList].forEach((el) => {
      if (el) {
        el.classList.add('hiding');
        setTimeout(() => (el.style.display = 'none'), 300);
      }
    });

    // Hiện report list
    reportList.style.display = 'flex';
    void reportList.offsetHeight;
    reportList.classList.remove('hiding');

    // Lấy danh sách báo cáo mới
    fetchReports();
  } else {
    reportList.classList.add('hiding');
    setTimeout(() => {
      reportList.style.display = 'none';
    }, 300);
  }
}

// Export các hàm cần thiết
window.closeReportModal = closeReportModal;
window.submitReport = submitReport;
window.toggleReportsList = toggleReportsList;
