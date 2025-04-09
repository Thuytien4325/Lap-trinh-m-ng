import { toast, createModal } from '../untils.js';
async function loadConversations() {
  const token = localStorage.getItem('access_token');
  if (!token) {
    console.error('Không có token đăng nhập');
    return;
  }

  try {
    const response = await fetch('http://127.0.0.1:8000/conversations/', {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      console.error('Lỗi khi gọi API:', response.status);
      return;
    }

    const conversations = await response.json();

    // Sắp xếp theo thời gian tin nhắn gần nhất
    conversations.sort((a, b) => {
      const timeA = a.last_message_time ? new Date(a.last_message_time) : new Date(0);
      const timeB = b.last_message_time ? new Date(b.last_message_time) : new Date(0);
      return timeB - timeA;
    });

    const chatList = document.querySelector('.chat-list');
    chatList.innerHTML = ''; // Xoá danh sách cũ

    conversations.forEach((conv) => {
      const li = document.createElement('li');
      li.className = 'chat-item';
      li.onclick = () => selectChat(conv.name || `Cuộc trò chuyện ${conv.conversation_id}`);

      // Avatar
      const avatar = document.createElement('img');
      avatar.className = 'avatar';
      avatar.src =
        conv.avatar_url || (conv.type === 'group' ? '../../assets/image/group-chat-default.jpg' : '../../assets/image/private-chat-default.jpg');
      avatar.alt = 'avatar';

      // Tên + icon loại
      const nameContainer = document.createElement('span');
      nameContainer.className = 'chat-name';

      const typeIcon = document.createElement('i');
      typeIcon.className = 'type-icon fas ' + (conv.type === 'group' ? 'fa-users' : 'fa-user');

      const nameText = document.createTextNode(' ' + (conv.name || `Cuộc trò chuyện ${conv.conversation_id}`));

      nameContainer.appendChild(typeIcon);
      nameContainer.appendChild(nameText);

      // Gắn vào item
      li.appendChild(avatar);
      li.appendChild(nameContainer);
      chatList.appendChild(li);
    });
  } catch (error) {
    console.error('Lỗi khi fetch:', error);
  }
}
function logout() {
  createModal({
    title: 'Xác nhận đăng xuất',
    message: 'Bạn có chắc chắn muốn đăng xuất không?',
    primaryButtonText: 'Đăng xuất',
    secondaryButtonText: 'Hủy',
    showSecondaryButton: true,
    onPrimary: () => {
      // Xoá dữ liệu trong localStorage
      localStorage.clear();

      // Hiển thị thông báo
      toast({
        title: 'Đăng xuất thành công!',
        message: 'Đang đăng xuất...',
        type: 'success',
      });

      // Chuyển hướng đến trang đăng nhập
      setTimeout(() => {
        window.location.href = '../auth/login.html';
      }, 1500);
    },
  });
}

window.logout = logout;
// Gọi khi trang đã load xong
document.addEventListener('DOMContentLoaded', loadConversations);
