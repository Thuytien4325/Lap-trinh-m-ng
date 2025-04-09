import { toast, createModal } from '../untils.js';

const baseURL = 'http://127.0.0.1:8000';
let selectedFiles = [];
let currentConversationId = null;
let messageOffset = 0;
let isLoadingMessages = false;
const messageLimit = 20;

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

async function loadConversations() {
  const token = localStorage.getItem('access_token');
  if (!token) {
    console.error('Không có token đăng nhập');
    return;
  }

  try {
    const response = await fetch(`${baseURL}/conversations/`, {
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
        ? `${baseURL}${conv.avatar_url.replace(/\\/g, '/')}`
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
  } catch (error) {
    console.error('Lỗi khi fetch:', error);
  }
}

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
    const response = await fetch(`${baseURL}/messages/${conversationId}/messages?limit=${messageLimit}&offset=${messageOffset}`, {
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
      const fixedFileUrl = `${baseURL}/${att.file_url.replace(/\\/g, '/')}`;

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
      const fixedFileUrl = `${baseURL}/${att.file_url.replace(/\\/g, '/')}`;

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
    const response = await fetch(`${baseURL}/messages/?${query.toString()}`, {
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

let socket = null;

function connectWebSocket() {
  const user = getCurrentUser();
  if (!user) return;

  socket = new WebSocket(`ws://127.0.0.1:8000/ws/user/${user.username}`);

  socket.onopen = () => {
    console.log('✅ WebSocket connected');
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('📩 Dữ liệu WebSocket nhận được:', data); // <-- thêm dòng này

    if (data.type === 'new_message') {
      if (String(currentConversationId) === String(data.conversation_id)) {
        const currentUser = getCurrentUser();
        const msg = data.message;
        const chatContent = document.getElementById('chat-content');

        const isCurrentUser = msg.sender_id === currentUser.user_id;
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', isCurrentUser ? 'sent' : 'received');

        if (!isCurrentUser) {
          const senderName = document.createElement('div');
          senderName.className = 'sender-name';
          senderName.textContent = msg.sender_nickname || 'Người dùng';
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
            const fixedFileUrl = `${baseURL}/${att.file_url.replace(/\\/g, '/')}`;

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
        chatContent.scrollTop = chatContent.scrollHeight; // Auto scroll to bottom
      } else {
        loadConversations();
      }
    }
  };

  socket.onclose = () => {
    console.log('❌ WebSocket closed, reconnecting...');
    setTimeout(connectWebSocket, 2000);
  };

  socket.onerror = (error) => {
    console.error('⚠️ WebSocket error:', error);
  };
}

document.addEventListener('DOMContentLoaded', () => {
  loadConversations();
  connectWebSocket();
});

window.logout = logout;
window.sendMessage = sendMessage;
window.sendImage = sendImage;
window.sendFile = sendFile;
