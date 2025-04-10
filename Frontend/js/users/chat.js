import { toast, createModal } from '../untils.js';
import config from '../config.js';

// Các biến toàn cục
let selectedFiles = [];
let currentConversationId = null;
let messageOffset = 0;
let isLoadingMessages = false;
const messageLimit = 20;

// Thêm biến để quản lý WebSocket
let socket = null;

// Thêm biến để kiểm soát việc reload
let isReloadConfirmed = false;

// Hàm lấy người dùng trong localstorage
function getCurrentUser() {
  const userStr = localStorage.getItem('user');
  if (!userStr) return null;

  try {
    return JSON.parse(userStr);
  } catch (e) {
    console.error('Lỗi khi parse user từ localStorage:', e);
    return null;
  }
}

// Load cuộc trò chuyện
async function loadConversations() {
  const token = localStorage.getItem('access_token');
  if (!token) {
    console.error('Không có token đăng nhập');
    return;
  }

  try {
    const response = await fetch(`${config.baseURL}/conversations/`, {
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

    conversations.sort((a, b) => {
      const timeA = a.last_message_time ? new Date(a.last_message_time) : new Date(0);
      const timeB = b.last_message_time ? new Date(b.last_message_time) : new Date(0);
      return timeB - timeA;
    });

    const chatList = document.querySelector('.chat-list');
    chatList.innerHTML = '';

    if (conversations.length > 0) {
      conversations.forEach((conv) => {
        const li = document.createElement('li');
        li.className = 'chat-item';

        li.dataset.conversationId = conv.conversation_id;
        li.dataset.conversationName = conv.name || `Cuộc trò chuyện ${conv.conversation_id}`;

        li.onclick = () => {
          const id = li.dataset.conversationId;
          const name = li.dataset.conversationName;
          currentConversationId = id;
          loadMessages(id, name, true);
        };

        const avatar = document.createElement('img');
        avatar.className = 'avatar';

        const fixedAvatarUrl = conv.avatar_url
          ? conv.avatar_url.startsWith('http')
            ? conv.avatar_url
            : `${config.baseURL}${conv.avatar_url.replace(/^\/+/, '')}`
          : conv.type === 'group'
          ? '../../assets/image/group-chat-default.jpg'
          : '../../assets/image/private-chat-default.jpg';

        avatar.src = fixedAvatarUrl;
        avatar.alt = 'avatar';

        const nameContainer = document.createElement('span');
        nameContainer.className = 'chat-name';

        const typeIcon = document.createElement('i');
        typeIcon.className = 'type-icon fas ' + (conv.type === 'group' ? 'fa-users' : 'fa-user');

        const nameText = document.createTextNode(' ' + (conv.name || `Cuộc trò chuyện ${conv.conversation_id}`));

        nameContainer.appendChild(typeIcon);
        nameContainer.appendChild(nameText);

        li.appendChild(avatar);
        li.appendChild(nameContainer);
        chatList.appendChild(li);
      });

      const latestConversation = conversations[0];
      currentConversationId = latestConversation.conversation_id;
      loadMessages(latestConversation.conversation_id, latestConversation.name || `Cuộc trò chuyện ${latestConversation.conversation_id}`, true);
    }
  } catch (error) {
    console.error('Lỗi khi fetch:', error);
  }
}

// Load tin nhắn
async function loadMessages(conversationId, conversationName, isInitial = true) {
  const token = localStorage.getItem('access_token');
  if (!token) return;

  const currentUser = getCurrentUser();
  const chatContent = document.getElementById('chat-content');

  if (isInitial) {
    document.getElementById('chat-header').textContent = conversationName;
    chatContent.innerHTML = '';
    messageOffset = 0;
  }

  if (isLoadingMessages) return;
  isLoadingMessages = true;

  try {
    const response = await fetch(`${config.baseURL}/messages/${conversationId}/messages?limit=${messageLimit}&offset=${messageOffset}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      console.error('Lỗi khi gọi API lấy tin nhắn:', response.status);
      return;
    }

    const data = await response.json();
    const messages = data.messages || [];

    if (messages.length === 0) return;

    const oldScrollHeight = chatContent.scrollHeight;

    messages.forEach((msg) => {
      appendMessageToTop(msg, currentUser);
    });

    if (!isInitial) {
      const newScrollHeight = chatContent.scrollHeight;
      chatContent.scrollTop = newScrollHeight - oldScrollHeight;
    } else {
      chatContent.scrollTop = chatContent.scrollHeight;
    }

    messageOffset += messages.length;
  } catch (error) {
    console.error('Lỗi khi fetch tin nhắn:', error);
  } finally {
    isLoadingMessages = false;
  }
}

// 🆕 Thêm hàm này để hiển thị tin nhắn mới từ WebSocket
function appendMessageToUI(msg) {
  const currentUser = getCurrentUser();
  const chatContent = document.getElementById('chat-content');

  const isCurrentUser = msg.sender_id === currentUser.user_id;
  const messageDiv = document.createElement('div');
  messageDiv.classList.add('message', isCurrentUser ? 'sent' : 'received');

  if (!isCurrentUser) {
    const senderName = document.createElement('div');
    senderName.className = 'sender-name';
    senderName.textContent = msg.sender_nickname;
    senderName.dataset.username = msg.sender_username;
    senderName.style.cursor = 'pointer';
    senderName.onclick = () => showUserInfo(msg.sender_username);
    messageDiv.appendChild(senderName);
  }

  const textDiv = document.createElement('div');
  textDiv.className = 'message-text';
  textDiv.innerHTML = msg.content;
  messageDiv.appendChild(textDiv);

  if (msg.attachments && msg.attachments.length > 0) {
    const attContainer = document.createElement('div');
    attContainer.className = 'attachments';

    msg.attachments.forEach((att) => {
      const fixedFileUrl = att.file_url.startsWith('http') ? att.file_url : `${config.baseURL}/${att.file_url.replace(/^\/+/, '')}`;

      if (/\.(jpg|jpeg|png|gif)$/i.test(fixedFileUrl)) {
        const img = document.createElement('img');
        img.src = fixedFileUrl;
        img.className = 'attachment-img';
        img.alt = 'Ảnh đính kèm';
        attContainer.appendChild(img);
      } else {
        const fileLink = document.createElement('a');
        fileLink.href = fixedFileUrl;
        fileLink.textContent = 'Tải file';
        fileLink.target = '_blank';
        fileLink.className = 'attachment-file';
        attContainer.appendChild(fileLink);
      }
    });

    messageDiv.appendChild(attContainer);
  }

  const time = document.createElement('span');
  time.className = 'timestamp';
  time.textContent = new Date(msg.timestamp).toLocaleString();
  messageDiv.appendChild(time);

  chatContent.appendChild(messageDiv);
  chatContent.scrollTop = chatContent.scrollHeight;
}

// 🧩 Phục vụ loadMessages: thêm tin nhắn lên đầu khi cuộn
function appendMessageToTop(msg, currentUser) {
  const chatContent = document.getElementById('chat-content');

  const isCurrentUser = msg.sender_id === currentUser.user_id;
  const messageDiv = document.createElement('div');
  messageDiv.classList.add('message', isCurrentUser ? 'sent' : 'received');

  if (!isCurrentUser) {
    const senderName = document.createElement('div');
    senderName.className = 'sender-name';
    senderName.textContent = msg.sender_nickname;
    senderName.dataset.username = msg.sender_username;
    senderName.style.cursor = 'pointer';
    senderName.onclick = () => showUserInfo(msg.sender_username);
    messageDiv.appendChild(senderName);
  }

  const textDiv = document.createElement('div');
  textDiv.className = 'message-text';
  textDiv.innerHTML = msg.content;
  messageDiv.appendChild(textDiv);

  if (msg.attachments && msg.attachments.length > 0) {
    const attContainer = document.createElement('div');
    attContainer.className = 'attachments';

    msg.attachments.forEach((att) => {
      const fixedFileUrl = att.file_url.startsWith('http') ? att.file_url : `${config.baseURL}/${att.file_url.replace(/^\/+/, '')}`;

      if (/\.(jpg|jpeg|png|gif)$/i.test(fixedFileUrl)) {
        const img = document.createElement('img');
        img.src = fixedFileUrl;
        img.className = 'attachment-img';
        img.alt = 'Ảnh đính kèm';
        attContainer.appendChild(img);
      } else {
        const fileLink = document.createElement('a');
        fileLink.href = fixedFileUrl;
        fileLink.textContent = 'Tải file';
        fileLink.target = '_blank';
        fileLink.className = 'attachment-file';
        attContainer.appendChild(fileLink);
      }
    });

    messageDiv.appendChild(attContainer);
  }

  const time = document.createElement('span');
  time.className = 'timestamp';
  time.textContent = new Date(msg.timestamp).toLocaleString();
  messageDiv.appendChild(time);

  chatContent.insertBefore(messageDiv, chatContent.firstChild);
}

function logout() {
  createModal({
    title: 'Xác nhận đăng xuất',
    message: 'Bạn có chắc chắn muốn đăng xuất không?',
    primaryButtonText: 'Đăng xuất',
    secondaryButtonText: 'Hủy',
    showSecondaryButton: true,
    onPrimary: () => {
      localStorage.clear();
      toast({
        title: 'Đăng xuất thành công!',
        message: 'Đang đăng xuất...',
        type: 'success',
      });
      setTimeout(() => {
        window.location.href = '../auth/login.html';
      }, 1500);
    },
  });
}

document.addEventListener('click', function (e) {
  if (e.target.classList.contains('attachment-img')) {
    const modal = document.getElementById('image-modal');
    const modalImg = document.getElementById('modal-image');
    modal.style.display = 'flex';
    modalImg.src = e.target.src;
  }

  if (e.target.classList.contains('close-btn') || e.target.id === 'image-modal') {
    document.getElementById('image-modal').style.display = 'none';
  }

  const modal = document.getElementById('user-info-modal');
  if (e.target === modal) {
    closeUserInfoModal();
  }
});

async function sendMessage() {
  const token = localStorage.getItem('access_token');
  if (!token || !currentConversationId) {
    console.error('Thiếu token hoặc chưa chọn cuộc trò chuyện');
    return;
  }

  const input = document.querySelector('.chat-input');
  const content = input.value.trim();

  if (!content && selectedFiles.length === 0) {
    return;
  }

  const formData = new FormData();
  selectedFiles.forEach((file) => formData.append('files', file));

  const query = new URLSearchParams({ conversation_id: currentConversationId });
  if (content) {
    query.append('content', content);
  }

  try {
    const response = await fetch(`${config.baseURL}/messages/?${query.toString()}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
      },
      body: formData,
    });

    if (!response.ok) {
      console.error('Gửi tin nhắn thất bại:', response.status);
      return;
    }
    const sentMessage = await response.json(); // <- giả sử API trả về tin nhắn đã lưu
    appendMessageToUI(sentMessage);
    input.value = '';
    selectedFiles = [];
  } catch (error) {
    console.error('Lỗi khi gửi tin nhắn:', error);
  }
}

function sendImage(event) {
  const file = event.target.files[0];
  if (file) {
    selectedFiles.push(file);
    sendMessage();
  }
}

function sendFile(event) {
  const file = event.target.files[0];
  if (file) {
    selectedFiles.push(file);
    sendMessage();
  }
}

document.getElementById('chat-content').addEventListener('scroll', function () {
  if (this.scrollTop === 0 && currentConversationId) {
    loadMessages(currentConversationId, '', false);
  }
});

// Thêm hàm kết nối WebSocket
function connectWebSocket() {
  const user = getCurrentUser();
  if (!user) return;

  socket = new WebSocket(`${config.wsUrl}/ws/user/${user.username}`);

  socket.onopen = () => {
    console.log('✅ WebSocket đã kết nối');
  };

  socket.onmessage = async (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log('Tin nhắn từ WebSocket:', data);
      if (data.type === 'url_update') {
        const updateEvent = new CustomEvent('url-update', {
          detail: data.data,
        });
        window.dispatchEvent(updateEvent);
      }

      // Bỏ qua tin nhắn từ Live Server
      if (typeof data === 'string' && (data === 'reload' || data === 'refreshcss')) {
        return;
      }

      // Xử lý tin nhắn mới
      if (data.type === 'new_message') {
        const msg = {
          ...data.message,
          sender_nickname: data.message.sender_nickname || 'Người gửi',
          sender_username: data.message.sender_username || 'unknown',
        };
        console.log('msg', msg);
        // Nếu tin nhắn thuộc cuộc trò chuyện hiện tại
        if (String(currentConversationId) === String(data.conversation_id)) {
          if (msg.attachments && msg.attachments.length > 0) {
            alert(`Bạn vừa nhận được tin nhắn có ${msg.attachments.length} file đính kèm.\nTrang sẽ tự động tải lại để hiển thị file.`);

            isReloadConfirmed = true;
            localStorage.setItem('lastConversationId', currentConversationId);
            window.location.href = window.location.href;
          } else {
            appendMessageToUI(msg);
          }
        } else {
          loadConversations();
        }
      }
    } catch (error) {
      console.error('Lỗi xử lý tin nhắn WebSocket:', error);
    }
  };

  socket.onclose = () => {
    console.log('❌ WebSocket đã đóng, đang kết nối lại...');
    setTimeout(connectWebSocket, 2000);
  };

  socket.onerror = (error) => {
    console.error('⚠️ Lỗi WebSocket:', error);
  };
}

// Thêm event listener để ngăn reload tự động
window.addEventListener('beforeunload', (e) => {
  if (!isReloadConfirmed) {
    e.preventDefault();
    e.returnValue = '';
  }
});

// Sửa lại phần khởi tạo khi trang load
document.addEventListener('DOMContentLoaded', () => {
  // Kiểm tra xem có conversationId được lưu từ lần reload trước không
  const lastConversationId = localStorage.getItem('lastConversationId');
  if (lastConversationId) {
    currentConversationId = lastConversationId;
    localStorage.removeItem('lastConversationId'); // Xóa sau khi đã lấy
  }

  loadConversations();
  connectWebSocket();
});

window.logout = logout;
window.sendMessage = sendMessage;
window.sendImage = sendImage;
window.sendFile = sendFile;

// Thêm hàm đóng modal thông tin người dùng
function closeUserInfoModal() {
  document.getElementById('user-info-modal').style.display = 'none';
}

// Thêm hàm lấy và hiển thị thông tin người dùng
async function showUserInfo(username) {
  try {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${config.baseURL}/users/search?query=${username}&search_by_nickname=false`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (response.ok) {
      const users = await response.json();
      const userData = users[0];
      if (userData) {
        document.getElementById('user-avatar').src = userData.avatar
          ? userData.avatar.startsWith('http')
            ? userData.avatar
            : `${config.baseURL}/${userData.avatar.replace(/^\/+/, '')}`
          : '../../assets/image/private-chat-default.jpg';
        document.getElementById('user-username').textContent = `${userData.username}`;
        document.getElementById('user-nickname').textContent = userData.nickname || 'string';
        document.getElementById('user-email').textContent = userData.email || 'user@example.com';

        // Sử dụng flex để căn giữa modal
        document.getElementById('user-info-modal').style.display = 'flex';
      }
    }
  } catch (error) {
    console.error('Lỗi khi lấy thông tin người dùng:', error);
  }
}

// Thêm vào window để có thể gọi từ HTML
window.closeUserInfoModal = closeUserInfoModal;
