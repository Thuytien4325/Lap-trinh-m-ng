import { toast, createModal, formatDateToMessage } from '../untils.js';
import config from '../config.js';
import initContextMenu from '../context-menu.js';
import toggleReportsList from './report.js';
// Các biến toàn cục
let selectedFiles = [];
let currentConversationId = null;
let messageOffset = 0;
let isLoadingMessages = false;
const messageLimit = 20;
let isReloadConfirmed = true;
// Thêm biến để quản lý WebSocket
let socket = null;

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

function createUnreadIndicator() {
  const dot = document.createElement('span');
  dot.className = 'unread-dot';
  dot.title = 'Bạn có tin nhắn chưa đọc';
  return dot;
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
    const noResultItem = chatList.querySelector('.no-results');
    chatList.innerHTML = '';
    if (noResultItem) {
      chatList.appendChild(noResultItem);
    }

    if (conversations.length > 0) {
      conversations.forEach((conv) => {
        const li = document.createElement('li');
        li.className = 'chat-item';

        li.dataset.id = conv.conversation_id; // dùng cho onclick hoặc các thao tác DOM khác
        li.dataset.conversationId = conv.conversation_id;
        li.dataset.conversationName = conv.name || `Cuộc trò chuyện ${conv.conversation_id}`;

        if (conv.is_read === false) {
          const unreadDot = createUnreadIndicator();
          li.appendChild(unreadDot);
        }

        li.onclick = async () => {
          const id = li.dataset.conversationId;
          const name = li.dataset.conversationName;

          currentConversationId = id;

          try {
            await fetch(`${config.baseURL}/conversations/conversations/${id}/mark-read`, {
              method: 'PUT',
              headers: {
                Authorization: `Bearer ${localStorage.getItem('access_token')}`,
              },
            });

            const dot = li.querySelector('.unread-dot');
            if (dot) dot.remove();
          } catch (err) {
            console.warn('Không thể mark-read conversation:', err);
          }

          loadMessages(id, name, true);

          // Kiểm tra xem sidebar có đang mở không
          const sidebar = document.getElementById('conversation-info-sidebar');
          if (sidebar.style.display === 'flex') {
            loadConversationInfo(); // Gọi hàm để cập nhật thông tin
          }
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

async function loadConversationsForWebSocket() {
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
    const noResultItem = chatList.querySelector('.no-results');
    chatList.innerHTML = '';
    if (noResultItem) {
      chatList.appendChild(noResultItem);
    }

    if (conversations.length > 0) {
      conversations.forEach((conv) => {
        const li = document.createElement('li');
        li.className = 'chat-item';
        li.dataset.id = conv.conversation_id;
        li.dataset.conversationId = conv.conversation_id;
        li.dataset.conversationName = conv.name || `Cuộc trò chuyện ${conv.conversation_id}`;

        if (conv.is_read === false) {
          const unreadDot = createUnreadIndicator();
          li.appendChild(unreadDot);
        }

        li.onclick = async () => {
          const id = li.dataset.conversationId;
          const name = li.dataset.conversationName;
          currentConversationId = id;

          try {
            await fetch(`${config.baseURL}/conversations/conversations/${id}/mark-read`, {
              method: 'PUT',
              headers: {
                Authorization: `Bearer ${token}`,
              },
            });

            const dot = li.querySelector('.unread-dot');
            if (dot) dot.remove();
          } catch (err) {
            console.warn('Không thể mark-read conversation:', err);
          }

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
    const chatHeader = document.getElementById('chat-header');
    chatHeader.dataset.id = conversationId;
    document.getElementById('conversation-name').textContent = conversationName;
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
      setTimeout(() => {
        chatContent.scrollTop = chatContent.scrollHeight;
      }, 0);
    }

    messageOffset += messages.length;

    // Cập nhật thông tin cuộc trò chuyện nếu sidebar đang mở
    const sidebar = document.getElementById('conversation-info-sidebar');
    if (sidebar.style.display === 'flex') {
      loadConversationInfo(); // Gọi hàm để cập nhật thông tin
    }
  } catch (error) {
    console.error('Lỗi khi fetch tin nhắn:', error);
  } finally {
    isLoadingMessages = false;
  }
}

function createAttachmentElement(att) {
  const fixedFileUrl = att.file_url.startsWith('http') ? att.file_url : `${config.baseURL}/${att.file_url.replace(/^\/+/, '')}`;

  const isImage = /\.(jpg|jpeg|png|gif)$/i.test(fixedFileUrl);

  // Nếu là ảnh
  if (isImage) {
    const img = document.createElement('img');
    img.src = fixedFileUrl;
    img.className = 'attachment-img has-context';
    img.alt = 'Ảnh đính kèm';
    img.setAttribute('data-url', fixedFileUrl);

    img.onerror = () => {
      const fileWrapper = document.createElement('div');
      fileWrapper.className = 'file-wrapper';
      fileWrapper.setAttribute('data-url', fixedFileUrl);

      const fallbackIcon = document.createElement('i');
      fallbackIcon.className = 'fas fa-exclamation-circle file-icon';

      const fallbackText = document.createElement('span');
      fallbackText.className = 'file-fallback-text';
      fallbackText.textContent = 'Ảnh không còn tồn tại!';

      fileWrapper.appendChild(fallbackIcon);
      fileWrapper.appendChild(fallbackText);

      img.replaceWith(fileWrapper);
    };

    return img;
  }

  // Nếu là file khác
  const fileWrapper = document.createElement('div');
  fileWrapper.className = 'file-wrapper';
  fileWrapper.setAttribute('data-url', fixedFileUrl);
  fileWrapper.classList.add('has-context');

  const fileIcon = document.createElement('i');
  let iconClass = 'fa-file-alt';

  if (/\.(pdf)$/i.test(fixedFileUrl)) {
    iconClass = 'fa-file-pdf';
  } else if (/\.(mp4)$/i.test(fixedFileUrl)) {
    iconClass = 'fa-file-video';
  } else if (/\.(mp3)$/i.test(fixedFileUrl)) {
    iconClass = 'fa-file-audio';
  }

  fileIcon.className = `fas ${iconClass} file-icon`;
  fileWrapper.appendChild(fileIcon);

  const fileLink = document.createElement('a');
  fileLink.href = fixedFileUrl;
  fileLink.target = '_blank';
  fileLink.className = 'attachment-file';
  fileLink.textContent = '';

  fileWrapper.appendChild(fileLink);

  // Gửi HEAD request để kiểm tra file tồn tại
  fetch(fixedFileUrl, { method: 'HEAD' })
    .then((res) => {
      if (!res.ok) throw new Error('File not found');
    })
    .catch(() => {
      fileWrapper.classList.remove('has-context');
      fileWrapper.innerHTML = '';

      const errorIcon = document.createElement('i');
      errorIcon.className = 'fas fa-exclamation-circle file-icon';

      const errorText = document.createElement('span');
      errorText.className = 'file-fallback-text';
      errorText.textContent = 'File không còn tồn tại!';

      fileWrapper.appendChild(errorIcon);
      fileWrapper.appendChild(errorText);
    });

  return fileWrapper;
}

// Thêm hàm này để hiển thị tin nhắn mới từ WebSocket
function appendMessageToUI(msg) {
  const currentUser = getCurrentUser();
  const chatContent = document.getElementById('chat-content');

  const isCurrentUser = msg.sender_id === currentUser.user_id;
  const messageDiv = document.createElement('div');
  messageDiv.classList.add('message', isCurrentUser ? 'sent' : 'received');
  messageDiv.dataset.messageId = msg.message_id;

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
      const attachmentEl = createAttachmentElement(att);
      attContainer.appendChild(attachmentEl);
    });

    messageDiv.appendChild(attContainer);
  }

  if (!msg.is_read && !isCurrentUser) {
    const unreadLabel = document.createElement('div');
    unreadLabel.className = 'unread-label';
    unreadLabel.textContent = 'Chưa đọc';
    messageDiv.appendChild(unreadLabel);
  }

  const time = document.createElement('span');
  time.className = 'timestamp';
  const date = new Date(msg.timestamp);
  date.setHours(date.getHours() + 7); // Chuyển sang múi giờ Việt Nam
  time.innerHTML = formatDateToMessage(date);
  messageDiv.appendChild(time);

  chatContent.appendChild(messageDiv);
  chatContent.scrollTop = chatContent.scrollHeight;
}

// Phục vụ loadMessages: thêm tin nhắn lên đầu khi cuộn
function appendMessageToTop(msg, currentUser) {
  const chatContent = document.getElementById('chat-content');

  const isCurrentUser = msg.sender_id === currentUser.user_id;
  const messageDiv = document.createElement('div');
  messageDiv.classList.add('message', isCurrentUser ? 'sent' : 'received');
  messageDiv.dataset.messageId = msg.message_id;
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
      const attachmentEl = createAttachmentElement(att);
      attContainer.appendChild(attachmentEl);
    });

    messageDiv.appendChild(attContainer);
  }

  if (!msg.is_read && !isCurrentUser) {
    const unreadLabel = document.createElement('div');
    unreadLabel.className = 'unread-label';
    unreadLabel.textContent = 'Chưa đọc';
    messageDiv.appendChild(unreadLabel);
  }

  const time = document.createElement('span');
  time.className = 'timestamp';
  const date = new Date(msg.timestamp);
  date.setHours(date.getHours() + 7); // Chuyển sang múi giờ Việt Nam
  time.innerHTML = formatDateToMessage(date);
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
  if (selectedFiles.length > 0) {
    isReloadConfirmed = false;
  }
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
    isReloadConfirmed = false;

    const shouldReload = confirm('Bạn vừa gửi tệp đính kèm.\nTải lại trang để cập nhật?');
    if (shouldReload) {
      localStorage.setItem('lastConversationId', currentConversationId);
      window.location.reload();
    } else {
      localStorage.setItem('lastConversationId', currentConversationId);
    }
  }
}

function sendFile(event) {
  const file = event.target.files[0];
  if (file) {
    selectedFiles.push(file);
    sendMessage();
    isReloadConfirmed = false;

    const shouldReload = confirm('Bạn vừa gửi tệp đính kèm.\nTải lại trang để cập nhật?');
    if (shouldReload) {
      localStorage.setItem('lastConversationId', currentConversationId);
      window.location.reload();
    } else {
      localStorage.setItem('lastConversationId', currentConversationId);
    }
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
      console.log('Dữ liệu nhận được từ WebSocket:', data);

      if (data.type_socket === 'url_update') {
        const updateEvent = new CustomEvent('url-update', {
          detail: data.data,
        });
        window.dispatchEvent(updateEvent);
      }

      // Xử lý thông báo hệ thống
      if (data.type_socket === 'new_notification') {
        // Hiển thị toast thông báo
        toast({
          title: data.title || 'Thông báo',
          message: data.message,
          type: 'info',
        });

        // Thêm thông báo mới vào đầu danh sách
        const notiItems = document.getElementById('noti-items');
        if (notiItems) {
          const newNoti = document.createElement('li');
          newNoti.className = 'noti-item unread';
          newNoti.dataset.notiId = data.id;

          const checkbox = document.createElement('input');
          checkbox.type = 'checkbox';
          checkbox.className = 'noti-checkbox';

          const message = document.createElement('div');
          message.className = 'noti-message';
          message.style.cursor = 'pointer';
          message.textContent = data.message;

          // Thêm sự kiện click để xử lý thông báo
          message.onclick = () =>
            onClickNotification({
              id: data.id,
              type: data.type,
              related_id: data.related_id,
              related_table: data.related_table,
            });

          newNoti.appendChild(checkbox);
          newNoti.appendChild(message);

          // Thêm vào đầu danh sách
          if (notiItems.firstChild) {
            notiItems.insertBefore(newNoti, notiItems.firstChild);
          } else {
            notiItems.appendChild(newNoti);
          }

          // Cập nhật số thông báo chưa đọc
          checkUnreadNotifications();
        }
      }

      // Xử lý tin nhắn mới
      if (data.type_socket === 'new_message') {
        const msg = {
          ...data.message,
          sender_nickname: data.message.sender_nickname || 'Người gửi',
          sender_username: data.message.sender_username || 'unknown',
        };
        console.log('Tin nhắn mới:', msg);
        // Nếu tin nhắn thuộc cuộc trò chuyện hiện tại
        if (String(currentConversationId) === String(data.conversation_id)) {
          if (msg.attachments && msg.attachments.length > 0) {
            isReloadConfirmed = false;

            const shouldReload = confirm('Bạn vừa nhận được tệp đính kèm.\nTải lại trang để cập nhật?');
            if (shouldReload) {
              localStorage.setItem('lastConversationId', currentConversationId);
              window.location.reload();
            } else {
              localStorage.setItem('lastConversationId', currentConversationId);
            }
          } else {
            appendMessageToUI(msg);
            loadConversationsForWebSocket();
          }
        } else {
          loadConversationsForWebSocket();
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

// window.addEventListener('beforeunload', (e) => {
//   if (!isReloadConfirmed) {
//     e.preventDefault();
//     e.returnValue = '';
//   }
// });

function setupMarkMessagesReadOnClick() {
  const chatContent = document.getElementById('chat-content');
  if (!chatContent) return;

  chatContent.addEventListener('click', async () => {
    if (!currentConversationId) return;

    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      // Lấy tất cả các tin nhắn chưa đọc trong cuộc trò chuyện hiện tại
      const unreadMessages = chatContent.querySelectorAll('.unread-label');
      if (unreadMessages.length === 0) {
        console.log('✅ Không có tin nhắn chưa đọc');
        return;
      }

      // Duyệt qua tất cả tin nhắn chưa đọc và gửi yêu cầu PUT cho từng tin nhắn
      for (const unreadMessage of unreadMessages) {
        const messageDiv = unreadMessage.closest('.message');
        if (!messageDiv) continue;

        const messageId = messageDiv.dataset.messageId;
        if (!messageId) continue;

        // Gửi yêu cầu PUT để đánh dấu tin nhắn là đã đọc
        await fetch(`${config.baseURL}/messages/mark-read/${messageId}`, {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        // Xóa thẻ 'unread-label' trong UI sau khi đánh dấu là đã đọc
        unreadMessage.remove();
      }

      // Đánh dấu cuộc trò chuyện là đã đọc
      await fetch(`${config.baseURL}/conversations/conversations/${currentConversationId}/mark-read`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      // Xóa dấu chấm chưa đọc khỏi cuộc trò chuyện trong danh sách
      const chatItem = document.querySelector(`.chat-item[data-id="${currentConversationId}"]`);
      if (chatItem) {
        const unreadDot = chatItem.querySelector('.unread-dot');
        if (unreadDot) unreadDot.remove();
      }
    } catch (err) {
      console.warn('❌ Lỗi khi đánh dấu tin nhắn đã đọc:', err);
    }
  });
}

// Thêm hàm kiểm tra trạng thái unread cho các toggle
async function checkUnreadStatus() {
  const token = localStorage.getItem('access_token');
  if (!token) return;

  try {
    // Kiểm tra thông báo chưa đọc
    const notiRes = await fetch(`${config.baseURL}/notifications/?unread_only=true`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const unreadNotis = await notiRes.json();
    const bellBtn = document.querySelector('.sidebar-toggle-container button[title="Thông báo"] i');
    if (bellBtn) {
      if (unreadNotis.length > 0) {
        bellBtn.classList.add('has-unread');
      } else {
        bellBtn.classList.remove('has-unread');
      }
    }

    // Kiểm tra yêu cầu kết bạn chưa đọc
    const friendReqRes = await fetch(`${config.baseURL}/friend-requests/received`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const friendReqs = await friendReqRes.json();
    const friendReqBtn = document.querySelector('.sidebar-toggle-container button[title="Yêu cầu kết bạn"] i');
    if (friendReqBtn) {
      if (friendReqs.length > 0) {
        friendReqBtn.classList.add('has-unread');
      } else {
        friendReqBtn.classList.remove('has-unread');
      }
    }

    // Kiểm tra báo cáo chưa xử lý
    const reportRes = await fetch(`${config.baseURL}/reports/?status=pending`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const pendingReports = await reportRes.json();
    const reportBtn = document.querySelector('.sidebar-toggle-container button[title="Báo cáo"] i');
    if (reportBtn) {
      if (pendingReports.length > 0) {
        reportBtn.classList.add('has-unread');
      } else {
        reportBtn.classList.remove('has-unread');
      }
    }
  } catch (error) {
    console.error('Lỗi khi kiểm tra trạng thái unread:', error);
  }
}

// Sửa lại phần khởi tạo khi trang load
document.addEventListener('DOMContentLoaded', () => {
  // Thêm event listener cho input chat
  const chatInput = document.querySelector('.chat-input');
  if (chatInput) {
    chatInput.addEventListener('keydown', function (e) {
      // Kiểm tra nếu nhấn Enter và không nhấn Shift (để cho phép xuống dòng bằng Shift+Enter)
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault(); // Ngăn không cho xuống dòng mặc định
        sendMessage(); // Gọi hàm gửi tin nhắn
      }
    });
  }

  // Kiểm tra xem có conversationId được lưu từ lần reload trước không
  const lastConversationId = localStorage.getItem('lastConversationId');
  if (lastConversationId) {
    currentConversationId = lastConversationId;
    localStorage.removeItem('lastConversationId');
  }

  loadConversations();
  connectWebSocket();
  setupMarkMessagesReadOnClick();

  // Kiểm tra trạng thái unread cho tất cả các toggle
  checkUnreadStatus();
});

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
        const avatarUrl = userData.avatar
          ? userData.avatar.startsWith('http')
            ? userData.avatar
            : `${config.baseURL}/${userData.avatar.replace(/^\/+/, '')}`
          : '../../assets/image/private-chat-default.jpg';

        const modal = document.getElementById('user-info-modal');
        modal.dataset.username = userData.username;
        modal.dataset.userId = userData.user_id;

        const avatarImg = document.getElementById('user-avatar');
        avatarImg.src = avatarUrl;
        avatarImg.onerror = () => {
          avatarImg.src = '../../assets/image/private-chat-default.jpg';
        };

        document.getElementById('user-username').textContent = `${userData.username}`;
        document.getElementById('user-nickname').textContent = userData.nickname || 'string';
        document.getElementById('user-email').textContent = userData.email || 'user@example.com';

        // Lấy danh sách bạn chung
        const mutualFriends = await getMutualFriends(username);
        const mutualCount = mutualFriends.length;

        // Hiển thị thông tin bạn chung
        const mutualFriendsContainer = document.getElementById('mutual-friends-container');
        mutualFriendsContainer.innerHTML = '';

        if (mutualCount > 0) {
          const mutualTitle = document.createElement('h3');
          mutualTitle.textContent = `${mutualCount} bạn chung`;
          mutualFriendsContainer.appendChild(mutualTitle);

          const mutualList = document.createElement('div');
          mutualList.className = 'mutual-friends-list';

          mutualFriends.forEach((friend) => {
            const friendItem = document.createElement('div');
            friendItem.className = 'mutual-friend-item';

            const friendAvatar = document.createElement('img');
            friendAvatar.src = friend.avatar
              ? `${config.baseURL}/${friend.avatar.replace(/^\/+/, '')}`
              : '../../assets/image/private-chat-default.jpg';
            friendAvatar.alt = 'avatar';
            friendAvatar.className = 'mutual-friend-avatar';
            friendAvatar.onerror = () => {
              friendAvatar.src = '../../assets/image/private-chat-default.jpg';
            };

            const friendName = document.createElement('span');
            friendName.className = 'mutual-friend-name';
            friendName.textContent = friend.nickname || friend.username;

            friendItem.appendChild(friendAvatar);
            friendItem.appendChild(friendName);
            mutualList.appendChild(friendItem);
          });

          mutualFriendsContainer.appendChild(mutualList);
        } else {
          mutualFriendsContainer.innerHTML = '<p class="no-mutual-friends">Không có bạn chung</p>';
        }

        // Thêm nút thêm bạn nếu chưa kết bạn
        const addFriendBtn = document.getElementById('add-friend-btn');
        if (userData.status === 'Chưa kết bạn') {
          addFriendBtn.style.display = 'block';
          addFriendBtn.onclick = () => addFriend(username);
        } else {
          addFriendBtn.style.display = 'none';
        }

        // Thêm nút hủy kết bạn nếu đã là bạn
        const unfriendBtn = document.getElementById('unfriend-btn');
        if (userData.status === 'Bạn bè') {
          unfriendBtn.style.display = 'block';
          unfriendBtn.onclick = () => unfriend(username);
        } else {
          unfriendBtn.style.display = 'none';
        }

        // Sử dụng flex để căn giữa modal
        modal.style.display = 'flex';
      }
    }
  } catch (error) {
    console.error('Lỗi khi lấy thông tin người dùng:', error);
    toast({
      title: 'Lỗi',
      message: 'Không thể tải thông tin người dùng',
      type: 'error',
    });
  }
}

// Thêm vào window để có thể gọi từ HTML
window.closeUserInfoModal = closeUserInfoModal;

const chatContainer = document.getElementById('chat-content'); // container hiển thị tin nhắn
const scrollBtn = document.getElementById('scrollToBottomBtn');

// Kiểm tra xem người dùng có đang ở gần đáy không
function isUserAtBottom() {
  return chatContainer.scrollHeight - chatContainer.scrollTop <= chatContainer.clientHeight + 50;
}

// Hiện hoặc ẩn nút
function showScrollButton() {
  scrollBtn.style.opacity = '1';
  scrollBtn.style.pointerEvents = 'auto';
}

function hideScrollButton() {
  scrollBtn.style.opacity = '0';
  scrollBtn.style.pointerEvents = 'none';
}

// Gắn sự kiện khi người dùng cuộn
chatContainer.addEventListener('scroll', () => {
  if (!isUserAtBottom()) {
    showScrollButton();
  } else {
    hideScrollButton();
  }
});

// Khi người dùng bấm nút
scrollBtn.addEventListener('click', () => {
  chatContainer.scrollTo({
    top: chatContainer.scrollHeight,
    behavior: 'smooth',
  });
});

function toggleChatList() {
  const chatList = document.getElementById('conversation-list');
  const notiList = document.getElementById('noti-list');
  const friendList = document.getElementById('friend-list');
  const requestList = document.getElementById('friend-request-list');
  const reportList = document.getElementById('reports-list');
  if (!chatList) return;

  const currentDisplay = window.getComputedStyle(chatList).display;

  if (currentDisplay === 'none') {
    // Ẩn 3 panel còn lại
    [notiList, friendList, requestList, reportList].forEach((el) => {
      el.classList.add('hiding');
      setTimeout(() => (el.style.display = 'none'), 300);
    });

    // Hiện cuộc trò chuyện
    chatList.style.display = 'flex';
    void chatList.offsetHeight;
    chatList.classList.remove('hiding');
  } else {
    chatList.classList.add('hiding');
    setTimeout(() => {
      chatList.style.display = 'none';
    }, 300);
  }
}

async function toggleNotiList() {
  const notiList = document.getElementById('noti-list');
  const friendList = document.getElementById('friend-list');
  const chatList = document.getElementById('conversation-list');
  const requestList = document.getElementById('friend-request-list');
  const reportList = document.getElementById('reports-list');

  if (!notiList) return;

  const currentDisplay = window.getComputedStyle(notiList).display;

  if (currentDisplay === 'none') {
    // Ẩn 3 panel còn lại
    [chatList, friendList, requestList, reportList].forEach((el) => {
      el.classList.add('hiding');
      setTimeout(() => (el.style.display = 'none'), 300);
    });
    await loadNotifications();
    // Hiện noti
    notiList.style.display = 'flex';
    void notiList.offsetHeight;
    notiList.classList.remove('hiding');

    // Xóa class has-unread khi mở danh sách thông báo
    const bellBtn = document.querySelector('.sidebar-toggle-container button[title="Thông báo"] i');
    if (bellBtn) {
      bellBtn.classList.remove('has-unread');
    }
  } else {
    notiList.classList.add('hiding');
    setTimeout(() => {
      notiList.style.display = 'none';
    }, 300);
  }
}

function toggleFriendsList() {
  const friendList = document.getElementById('friend-list');
  const notiList = document.getElementById('noti-list');
  const chatList = document.getElementById('conversation-list');
  const requestList = document.getElementById('friend-request-list');
  const reportList = document.getElementById('reports-list');

  if (!friendList) return;

  const currentDisplay = window.getComputedStyle(friendList).display;

  if (currentDisplay === 'none') {
    // Ẩn các panel còn lại
    [notiList, chatList, requestList, reportList].forEach((el) => {
      el.classList.add('hiding');
      setTimeout(() => (el.style.display = 'none'), 300);
    });

    // Hiện friend-list
    friendList.style.display = 'flex';
    void friendList.offsetHeight;
    friendList.classList.remove('hiding');

    // Gọi input event để hiển thị danh sách bạn bè mặc định
    const friendSearchInput = document.querySelector('#friend-list .search');
    friendSearchInput.dispatchEvent(new Event('input'));
  } else {
    friendList.classList.add('hiding');
    setTimeout(() => {
      friendList.style.display = 'none';
    }, 300);
  }
}

async function toggleFriendRequestsList() {
  const requestList = document.getElementById('friend-request-list');
  const friendList = document.getElementById('friend-list');
  const notiList = document.getElementById('noti-list');
  const chatList = document.getElementById('conversation-list');
  const reportList = document.getElementById('reports-list');

  if (!requestList) return;

  const currentDisplay = window.getComputedStyle(requestList).display;

  if (currentDisplay === 'none') {
    // Ẩn ba panel còn lại
    chatList.classList.add('hiding');
    friendList.classList.add('hiding');
    notiList.classList.add('hiding');
    reportList.classList.add('hiding');
    setTimeout(() => {
      chatList.style.display = 'none';
      friendList.style.display = 'none';
      notiList.style.display = 'none';
      reportList.style.display = 'none';
    }, 300);

    // Hiện request list
    requestList.style.display = 'flex';
    void requestList.offsetHeight;
    requestList.classList.remove('hiding');

    await loadFriendRequests();

    // Xóa class has-unread khi mở danh sách yêu cầu kết bạn
    const friendReqBtn = document.querySelector('.sidebar-toggle-container button[title="Yêu cầu kết bạn"] i');
    if (friendReqBtn) {
      friendReqBtn.classList.remove('has-unread');
    }
  } else {
    requestList.classList.add('hiding');
    setTimeout(() => {
      requestList.style.display = 'none';
    }, 300);
  }
}

// Tạo conversation

let currentConversationType = 'private'; // "private" hoặc "group"

function openCreateModal(type) {
  currentConversationType = type;
  document.getElementById('create-modal-title').textContent = type === 'group' ? 'Tạo nhóm trò chuyện' : 'Tạo cuộc trò chuyện';

  // Hiện hoặc ẩn ô nhập tên nhóm
  document.getElementById('conversation-group-name').style.display = type === 'group' ? 'block' : 'none';

  document.getElementById('conversation-username').placeholder = type === 'group' ? 'Danh sách bạn bè' : 'Tên bạn bè';

  // Xoá dữ liệu cũ
  document.getElementById('conversation-username').value = '';
  document.getElementById('conversation-group-name').value = '';

  document.getElementById('create-conversation-modal').style.display = 'flex';

  document.getElementById('create-conversation-modal').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault(); // Ngăn chặn hành vi mặc định của Enter
      submitCreateConversation(); // Gọi hàm gửi
    } else if (event.key === 'Escape') {
      closeCreateModal(); // Gọi hàm hủy
    }
  });
}

function closeCreateModal() {
  document.getElementById('create-conversation-modal').style.display = 'none';
}

async function submitCreateConversation() {
  const token = localStorage.getItem('access_token');
  if (!token) {
    toast({
      title: 'Lỗi',
      message: 'Bạn chưa đăng nhập.',
      type: 'error',
    });
    return;
  }

  const usernamesInput = document.getElementById('conversation-username').value.trim();
  const groupName = document.getElementById('conversation-group-name').value.trim();

  if (currentConversationType === 'private' && !usernamesInput) {
    toast({
      title: 'Lỗi',
      message: 'Vui lòng nhập tên người dùng.',
      type: 'error',
    });
    return;
  }

  const query = new URLSearchParams();
  query.append('type', currentConversationType);

  if (currentConversationType === 'group') {
    const members = usernamesInput
      ? usernamesInput
          .split(',')
          .map((u) => u.trim())
          .filter(Boolean)
      : [];

    if (members.length > 0) {
      members.forEach((username) => query.append('username', username));
    }

    if (groupName) {
      query.append('name', groupName);
    }
  } else if (currentConversationType === 'private') {
    query.append('username', usernamesInput);
  }

  try {
    const response = await fetch(`${config.baseURL}/conversations/?${query.toString()}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
      },
    });

    const result = await response.json();

    if (!response.ok) {
      toast({
        title: 'Lỗi',
        message: result.detail || 'Có lỗi xảy ra.',
        type: 'error',
      });
      return;
    }

    closeCreateModal();
    toast({
      title: 'Thành công',
      message: currentConversationType === 'group' ? 'Đã tạo nhóm!' : 'Đã tạo cuộc trò chuyện!',
      type: 'success',
    });

    // Tải cuộc trò chuyện mới
    currentConversationId = result.id; // Lưu ID cuộc trò chuyện mới

    // Thêm cuộc trò chuyện mới vào đầu danh sách
    const chatList = document.querySelector('.chat-list');
    const li = document.createElement('li');
    li.className = 'chat-item';
    li.dataset.id = currentConversationId;
    li.dataset.conversationId = currentConversationId;

    // Thiết lập tên cuộc trò chuyện
    const conversationName = currentConversationType === 'private' ? `test & ${usernamesInput}` : groupName;
    li.dataset.conversationName = conversationName;

    // Thêm dấu chấm nếu cuộc trò chuyện chưa đọc
    const unreadDot = createUnreadIndicator();
    li.appendChild(unreadDot);

    li.onclick = async () => {
      currentConversationId = currentConversationId; // Cập nhật ID cuộc trò chuyện
      loadMessages(currentConversationId, conversationName, true);
    };

    const avatar = document.createElement('img');
    avatar.className = 'avatar';
    avatar.src = currentConversationType === 'group' ? '../../assets/image/group-chat-default.jpg' : '../../assets/image/private-chat-default.jpg';
    avatar.alt = 'avatar';

    const nameContainer = document.createElement('span');
    nameContainer.className = 'chat-name';
    const nameText = document.createTextNode(' ' + conversationName);
    nameContainer.appendChild(nameText);

    li.appendChild(avatar);
    li.appendChild(nameContainer);
    chatList.insertBefore(li, chatList.firstChild); // Thêm vào đầu danh sách

    loadMessages(currentConversationId, conversationName, true);
  } catch (error) {
    console.error('Lỗi khi fetch:', error);
    toast({
      title: 'Lỗi',
      message: 'Không thể kết nối đến máy chủ hoặc lỗi không xác định.',
      type: 'error',
    });
  }
}

// Gắn sự kiện tìm kiếm cho thanh input trong friend-list
const friendSearchInput = document.querySelector('#friend-list .search');
const friendListContainer = document.querySelector('.friend-items');
const searchToggle = document.getElementById('search-by-nickname');
const searchLabel = document.getElementById('search-label');

searchToggle.addEventListener('change', () => {
  const isNickname = searchToggle.checked;
  searchLabel.textContent = isNickname ? 'Nickname' : 'Username';
  friendSearchInput.dispatchEvent(new Event('input')); // Gọi lại tìm kiếm
});

// Hàm lấy danh sách bạn chung
async function getMutualFriends(username) {
  const token = localStorage.getItem('access_token');
  if (!token) return [];

  try {
    const response = await fetch(`${config.baseURL}/friends/mutual?username=${username}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Không thể lấy danh sách bạn chung');
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Lỗi khi lấy danh sách bạn chung:', error);
    return [];
  }
}

// Hàm hủy kết bạn
async function unfriend(username) {
  const token = localStorage.getItem('access_token');
  if (!token) {
    toast({
      title: 'Lỗi',
      message: 'Bạn chưa đăng nhập',
      type: 'error',
    });
    return;
  }

  try {
    const response = await fetch(`${config.baseURL}/friends/friends/${username}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      const result = await response.json();
      toast({
        title: 'Lỗi',
        message: result.detail || 'Không thể hủy kết bạn',
        type: 'error',
      });
      return;
    }

    toast({
      title: 'Thành công',
      message: 'Đã hủy kết bạn',
      type: 'success',
    });

    // Đóng modal thông tin người dùng nếu đang mở
    closeUserInfoModal();

    // Cập nhật lại danh sách bạn bè
    loadFriendList();
  } catch (error) {
    console.error('Lỗi khi hủy kết bạn:', error);
    toast({
      title: 'Lỗi',
      message: 'Không thể kết nối đến máy chủ',
      type: 'error',
    });
  }
}

// Cập nhật hàm hiển thị danh sách bạn bè
friendSearchInput.addEventListener('input', async function (e) {
  console.log('test');
  const query = e.target.value.trim();
  const token = localStorage.getItem('access_token');
  if (!token) return;

  friendListContainer.innerHTML = '';

  try {
    if (!query) {
      // Gọi API lấy tất cả bạn bè
      const res = await fetch(`${config.baseURL}/friends/friends`, {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
        },
      });

      const friends = await res.json();
      if (friends.length === 0) {
        friendListContainer.innerHTML = '<li style="text-align:center; color:#999">Không có bạn nào.</li>';
        return;
      }

      for (const user of friends) {
        const li = document.createElement('li');
        li.className = 'friend-item';

        // Thêm sự kiện click để hiển thị modal thông tin
        li.onclick = () => showUserInfo(user.username);

        const avatar = document.createElement('img');
        avatar.src = user.avatar ? `${config.baseURL}/${user.avatar.replace(/^\/+/, '')}` : '../../assets/image/private-chat-default.jpg';
        avatar.alt = 'avatar';
        avatar.className = 'avatar';

        const info = document.createElement('div');
        info.className = 'friend-info';

        const name = document.createElement('div');
        name.className = 'friend-name';
        name.textContent = `${user.nickname || 'Không có nickname'} (@${user.username})`;

        // Lấy danh sách bạn chung
        const mutualFriends = await getMutualFriends(user.username);
        const mutualCount = mutualFriends.length;

        const actions = document.createElement('div');
        actions.className = 'friend-actions';

        // Nút hủy kết bạn
        const unfriendBtn = document.createElement('button');
        unfriendBtn.innerHTML = '<i class="fas fa-user-minus"></i>';
        unfriendBtn.className = 'unfriend-btn';
        unfriendBtn.title = 'Hủy kết bạn';
        unfriendBtn.onclick = (e) => {
          e.stopPropagation(); // Ngăn sự kiện click lan ra phần tử cha
          unfriend(user.username);
        };

        info.appendChild(name);
        // Chỉ hiển thị số bạn chung nếu có
        if (mutualCount > 0) {
          const mutualInfo = document.createElement('div');
          mutualInfo.className = 'mutual-friends';
          mutualInfo.textContent = `${mutualCount} bạn chung`;
          info.appendChild(mutualInfo);
        }

        li.appendChild(avatar);
        li.appendChild(info);
        li.appendChild(actions);
        actions.appendChild(unfriendBtn);
        friendListContainer.appendChild(li);
      }
    } else {
      // Tìm kiếm người dùng
      const searchByNickname = searchToggle.checked;
      const res = await fetch(`${config.baseURL}/users/search?query=${encodeURIComponent(query)}&search_by_nickname=${searchByNickname}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
        },
      });

      const users = await res.json();
      if (!users || users.length === 0) {
        friendListContainer.innerHTML = '<li style="text-align:center; color:#999">Không tìm thấy người dùng.</li>';
        return;
      }

      for (const user of users) {
        const li = document.createElement('li');
        li.className = 'friend-item';

        // Thêm sự kiện click để hiển thị modal thông tin
        li.onclick = () => showUserInfo(user.username);

        const avatar = document.createElement('img');
        avatar.src = user.avatar ? `${config.baseURL}/${user.avatar.replace(/^\/+/, '')}` : '../../assets/image/private-chat-default.jpg';
        avatar.alt = 'avatar';
        avatar.className = 'avatar';

        const info = document.createElement('div');
        info.className = 'friend-info';

        const name = document.createElement('div');
        name.className = 'friend-name';
        name.textContent = `${user.nickname || 'Không có nickname'} (@${user.username})`;

        // Lấy danh sách bạn chung cho kết quả tìm kiếm
        const mutualFriends = await getMutualFriends(user.username);
        const mutualCount = mutualFriends.length;

        const status = document.createElement('div');
        status.className = 'friend-status';
        status.textContent = user.status;

        const addBtn = document.createElement('button');
        addBtn.className = 'add-friend-btn';
        addBtn.title = 'Thêm bạn';
        addBtn.innerHTML = '<i class="fas fa-user-plus"></i>';
        addBtn.disabled = user.status !== 'Chưa kết bạn';
        if (addBtn.disabled) addBtn.style.opacity = '0.4';

        addBtn.onclick = (e) => {
          e.stopPropagation(); // Ngăn sự kiện click lan ra phần tử cha
          if (!addBtn.disabled) addFriend(user.username);
        };

        info.appendChild(name);
        info.appendChild(status);
        // Chỉ hiển thị số bạn chung nếu có
        if (mutualCount > 0) {
          const mutualInfo = document.createElement('div');
          mutualInfo.className = 'mutual-friends';
          mutualInfo.textContent = `${mutualCount} bạn chung`;
          info.appendChild(mutualInfo);
        }

        li.appendChild(avatar);
        li.appendChild(info);
        li.appendChild(addBtn);
        friendListContainer.appendChild(li);
      }
    }
  } catch (error) {
    console.error('Lỗi khi tải danh sách bạn bè:', error);
    toast({ title: 'Lỗi', message: 'Không thể tải danh sách.', type: 'error' });
  }
});

// Gọi thủ công khi mở danh sách bạn bè
async function loadFriendList() {
  console.log('Load friend list');
  const friendList = document.querySelector('.friend-items');
  friendList.innerHTML = '';

  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      console.error('Không tìm thấy token');
      return;
    }

    const response = await fetch('http://127.0.0.1:8000/friends/friends', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Lỗi khi tải danh sách bạn bè');
    }

    const friends = await response.json();

    for (const friend of friends) {
      const friendItem = document.createElement('li');
      friendItem.className = 'friend-item';
      friendItem.onclick = () => showUserInfo(friend.username);

      const friendInfo = document.createElement('div');
      friendInfo.className = 'friend-info';

      const avatar = document.createElement('img');
      avatar.src = friend.avatar || '../../assets/image/private-chat-default.jpg';
      avatar.alt = 'avatar';
      avatar.className = 'avatar';

      const info = document.createElement('div');
      info.className = 'info';

      const name = document.createElement('div');
      name.className = 'name';
      name.textContent = friend.nickname || friend.username;

      const mutualFriends = await getMutualFriends(friend.username);
      const mutualCount = mutualFriends.length;

      info.appendChild(name);
      if (mutualCount > 0) {
        const mutualInfo = document.createElement('div');
        mutualInfo.className = 'mutual-friends';
        mutualInfo.textContent = `${mutualCount} bạn chung`;
        info.appendChild(mutualInfo);
      }

      friendInfo.appendChild(avatar);
      friendInfo.appendChild(info);
      friendItem.appendChild(friendInfo);

      const unfriendBtn = document.createElement('button');
      unfriendBtn.className = 'unfriend-btn';
      unfriendBtn.innerHTML = '<i class="fas fa-user-minus"></i>';
      unfriendBtn.onclick = (e) => {
        e.stopPropagation();
        unfriend(friend.username);
      };

      friendItem.appendChild(unfriendBtn);
      friendList.appendChild(friendItem);
    }
  } catch (error) {
    console.error('Lỗi khi tải danh sách bạn bè:', error);
    showToast('Có lỗi xảy ra khi tải danh sách bạn bè', 'error');
  }
}

// Hàm gọi API thêm bạn
async function addFriend(username) {
  const token = localStorage.getItem('access_token');
  if (!token) {
    toast({
      title: 'Lỗi',
      message: 'Bạn chưa đăng nhập.',
      type: 'error',
    });
    return;
  }

  try {
    const res = await fetch(`${config.baseURL}/friend-requests/?receiver_username=${username}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
      },
    });

    const result = await res.json();

    if (res.ok) {
      toast({
        title: 'Thành công',
        message: `Đã gửi lời mời kết bạn đến @${username}`,
        type: 'success',
      });

      // Đóng modal thông tin người dùng nếu đang mở
      closeUserInfoModal();

      friendSearchInput.dispatchEvent(new Event('input'));
    } else {
      toast({
        title: 'Lỗi',
        message: result.detail || 'Không thể gửi lời mời kết bạn.',
        type: 'error',
      });
    }
  } catch (error) {
    console.error('Lỗi khi gửi lời mời kết bạn:', error);
    toast({
      title: 'Lỗi',
      message: 'Không thể kết nối đến máy chủ.',
      type: 'error',
    });
  }
}

async function deleteFriendRequest(requestId) {
  const token = localStorage.getItem('access_token');
  if (!token) {
    toast({ title: 'Lỗi', message: 'Bạn chưa đăng nhập.', type: 'error' });
    return;
  }

  createModal({
    title: 'Xác nhận hủy yêu cầu',
    message: 'Bạn có chắc chắn muốn hủy yêu cầu kết bạn này không?',
    primaryButtonText: 'Hủy yêu cầu',
    secondaryButtonText: 'Đóng',
    showSecondaryButton: true,
    onPrimary: async () => {
      try {
        const res = await fetch(`${config.baseURL}/friend-requests/${requestId}`, {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: 'application/json',
          },
        });

        if (res.ok) {
          toast({ title: 'Thành công', message: 'Đã hủy yêu cầu kết bạn.', type: 'success' });
          await loadFriendRequests(); // Refresh lại danh sách
        } else {
          const data = await res.json();
          toast({ title: 'Lỗi', message: data.detail || 'Không thể hủy yêu cầu.', type: 'error' });
        }
      } catch (err) {
        console.error('Lỗi khi hủy yêu cầu:', err);
        toast({ title: 'Lỗi', message: 'Có lỗi xảy ra khi hủy yêu cầu.', type: 'error' });
      }
    },
  });
}

// Hàm xử lí yêu cầu kết bạn
async function loadFriendRequests() {
  const token = localStorage.getItem('access_token');
  if (!token) {
    toast({ title: 'Lỗi', message: 'Bạn chưa đăng nhập.', type: 'error' });
    return;
  }

  const receivedList = document.getElementById('received-requests');
  const sentList = document.getElementById('sent-requests');
  receivedList.innerHTML = '';
  sentList.innerHTML = '';

  try {
    // Fetch received requests
    const receivedRes = await fetch(`${config.baseURL}/friend-requests/received`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const received = await receivedRes.json();

    if (received.length === 0) {
      receivedList.innerHTML = `<li style="text-align:center; color:#999">Không có yêu cầu nào.</li>`;
    } else {
      received.forEach((req) => {
        const li = document.createElement('li');
        li.className = 'request-item';

        const info = document.createElement('div');
        info.className = 'username';
        info.textContent = `${req.sender_nickname || req.sender_username} (@${req.sender_username})`;

        const actions = document.createElement('div');
        actions.className = 'actions';

        const acceptBtn = document.createElement('button');
        acceptBtn.innerHTML = '<i class="fas fa-check" style="color:green"></i>';
        acceptBtn.title = 'Chấp nhận yêu cầu';
        acceptBtn.onclick = () => respondFriendRequest(req.id, true);

        const rejectBtn = document.createElement('button');
        rejectBtn.innerHTML = '<i class="fas fa-times" style="color:red"></i>';
        rejectBtn.title = 'Từ chối yêu cầu';
        rejectBtn.onclick = () => respondFriendRequest(req.id, false);

        actions.appendChild(acceptBtn);
        actions.appendChild(rejectBtn);
        li.appendChild(info);
        li.appendChild(actions);
        receivedList.appendChild(li);
      });
    }

    // Fetch sent requests
    const sentRes = await fetch(`${config.baseURL}/friend-requests/sent`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const sent = await sentRes.json();

    if (sent.length === 0) {
      sentList.innerHTML = `<li style="text-align:center; color:#999">Không có yêu cầu nào.</li>`;
    } else {
      sent.forEach((req) => {
        const li = document.createElement('li');
        li.className = 'request-item';

        const info = document.createElement('div');
        info.className = 'username';
        info.textContent = `${req.receiver_nickname || req.receiver_username} (@${req.receiver_username})`;

        const actions = document.createElement('div');
        actions.className = 'actions';

        const cancelBtn = document.createElement('button');
        cancelBtn.innerHTML = '<i class="fas fa-trash-alt" style="color:gray"></i>';
        cancelBtn.title = 'Hủy yêu cầu';
        cancelBtn.onclick = () => deleteFriendRequest(req.id);

        actions.appendChild(cancelBtn);

        li.appendChild(info);
        li.appendChild(actions);
        sentList.appendChild(li);
      });
    }
  } catch (err) {
    console.error('Lỗi khi tải yêu cầu:', err);
    toast({ title: 'Lỗi', message: 'Không thể tải yêu cầu kết bạn.', type: 'error' });
  }
}

async function respondFriendRequest(requestId, accept = true) {
  const token = localStorage.getItem('access_token');
  if (!token) {
    toast({ title: 'Lỗi', message: 'Bạn chưa đăng nhập.', type: 'error' });
    return;
  }

  const action = accept ? 'accept' : 'reject';

  try {
    const res = await fetch(`${config.baseURL}/friend-requests/${requestId}/${action}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
      },
    });

    if (!res.ok) {
      const err = await res.json();
      toast({ title: 'Lỗi', message: err.detail || 'Thao tác không thành công.', type: 'error' });
      return;
    }

    toast({
      title: 'Thành công',
      message: accept ? 'Đã chấp nhận lời mời!' : 'Đã từ chối lời mời!',
      type: 'success',
    });

    loadFriendRequests(); // Refresh lại danh sách
  } catch (error) {
    console.error('Lỗi khi phản hồi lời mời:', error);
    toast({
      title: 'Lỗi',
      message: 'Không thể kết nối đến máy chủ.',
      type: 'error',
    });
  }
}

async function loadNotifications(filters = {}) {
  const token = localStorage.getItem('access_token');
  if (!token) return;

  try {
    const params = new URLSearchParams({
      unread_only: filters.unread_only ?? false,
      from_system: filters.from_system ?? false,
      newest_first: filters.newest_first ?? true,
    });

    const res = await fetch(`${config.baseURL}/notifications/?${params.toString()}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
      },
    });

    const data = await res.json();

    const notifications = Array.isArray(data) ? data : data.notifications;
    renderNotifications(notifications);
  } catch (err) {
    console.error('Lỗi khi tải thông báo:', err);
    toast({ title: 'Lỗi', message: 'Không thể tải thông báo', type: 'error' });
  }
}

function renderNotifications(notiList) {
  const container = document.getElementById('noti-items');
  container.innerHTML = '';

  if (!notiList || notiList.length === 0) {
    container.innerHTML = `<li class="noti-item">Không có thông báo nào.</li>`;
    return;
  }

  notiList.forEach((noti) => {
    const li = document.createElement('li');
    li.className = 'noti-item';
    if (!noti.is_read) li.classList.add('unread');
    li.dataset.notiId = noti.id;

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'noti-checkbox';

    const content = document.createElement('div');
    content.className = 'noti-message';
    content.textContent = noti.message;
    content.style.cursor = 'pointer';

    content.onclick = () => onClickNotification(noti);

    li.appendChild(checkbox);
    li.appendChild(content);
    container.appendChild(li);
  });
}

document.getElementById('select-all-noti').addEventListener('change', function () {
  const checkboxes = document.querySelectorAll('.noti-checkbox');
  checkboxes.forEach((cb) => (cb.checked = this.checked));
});

function getSelectedNotificationIds() {
  return Array.from(document.querySelectorAll('.noti-item'))
    .filter((item) => item.querySelector('.noti-checkbox')?.checked)
    .map((item) => item.dataset.notiId);
}

function setCurrentConversation(conversationId) {
  currentConversationId = conversationId;

  // Tìm element trong danh sách chat để kích hoạt
  const chatItem = document.querySelector(`.chat-item[data-id="${conversationId}"]`);

  if (chatItem) {
    chatItem.click();
  } else {
    loadConversations(() => {
      const newItem = document.querySelector(`.chat-item[data-id="${conversationId}"]`);
      if (newItem) newItem.click();
    });
  }

  toggleChatList(); // Mở panel chat
}

async function onClickNotification(noti) {
  const token = localStorage.getItem('access_token');
  if (!token) return;

  try {
    // 1. Gửi API đánh dấu đã đọc
    await fetch(`${config.baseURL}/notifications/${noti.id}/read`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
      },
    });

    // 2. Điều hướng theo loại thông báo
    console.log('noti', noti);
    const table = noti.type;
    const targetId = noti.related_id;
    console.log('table', table, 'targetId', targetId);
    if (table === 'conversations') {
      setCurrentConversation(targetId); // Tự động vào cuộc trò chuyện
    } else if (table === 'friend_request') {
      toggleFriendRequestsList();
    } else if (table === 'friends') {
      toggleFriendsList();
    } else if (table === 'friend_accept') {
      toggleFriendsList();
    } else if (table === 'report') {
      toggleReportsList();
    }
    // Làm mới lại thông báo (ẩn chấm đỏ nếu cần)
    await loadNotifications();
  } catch (err) {
    console.error('Lỗi khi xử lý thông báo:', err);
    toast({ title: 'Lỗi', message: 'Không thể xử lý thông báo', type: 'error' });
  }
}

async function markSelectedNoti(status) {
  const ids = getSelectedNotificationIds();
  const token = localStorage.getItem('access_token');
  if (!ids.length || !token) return;

  for (const id of ids) {
    await fetch(`${config.baseURL}/notifications/${id}/${status}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
      },
    });
  }

  toast({ title: 'Thành công', message: `Đã đánh dấu ${status === 'read' ? 'đã đọc' : 'chưa đọc'}`, type: 'success' });
  await loadNotifications();
  document.getElementById('select-all-noti').checked = false;
}

async function deleteSelectedNoti() {
  const ids = getSelectedNotificationIds();
  const token = localStorage.getItem('access_token');
  if (!ids.length || !token) return;

  for (const id of ids) {
    await fetch(`${config.baseURL}/notifications/${id}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
      },
    });
  }

  toast({ title: 'Thành công', message: `Đã xoá ${ids.length} thông báo`, type: 'success' });
  await loadNotifications();
  document.getElementById('select-all-noti').checked = false;
}

async function checkUnreadNotifications() {
  const token = localStorage.getItem('access_token');
  if (!token) return;

  const res = await fetch(`${config.baseURL}/notifications/?unread_only=true`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const unread = await res.json();
  const bellBtn = document.querySelector('.sidebar-toggle-container button[title="Thông báo"] i');

  if (unread.length > 0) {
    bellBtn.classList.add('has-unread');
  } else {
    bellBtn.classList.remove('has-unread');
  }

  document.getElementById('select-all-noti').checked = false;
}

document.getElementById('apply-filters').addEventListener('click', () => {
  const filterValue = document.getElementById('filter-select').value;

  // Mặc định các giá trị
  const filters = {
    unread_only: false,
    from_system: false,
    newest_first: true,
  };

  switch (filterValue) {
    case 'oldest':
      filters.newest_first = false;
      break;
    case 'unread':
      filters.unread_only = true;
      break;
    case 'system':
      filters.from_system = true;
      break;
    default:
      // 'newest' hoặc không xác định
      break;
  }

  loadNotifications(filters);
});

function toggleConversationInfo() {
  const sidebar = document.getElementById('conversation-info-sidebar');

  if (sidebar.style.display === 'none' || sidebar.classList.contains('hiding')) {
    sidebar.classList.remove('hiding');
    sidebar.style.display = 'flex';
    // Tải thông tin cuộc trò chuyện khi mở sidebar
    if (currentConversationId) {
      loadConversationInfo();
    }
  } else {
    sidebar.classList.add('hiding');
    setTimeout(() => {
      sidebar.style.display = 'none';
      sidebar.classList.remove('hiding');
    }, 300);
  }
}

// Hàm lấy thông tin cuộc trò chuyện và danh sách thành viên
async function loadConversationInfo() {
  const token = localStorage.getItem('access_token');
  if (!token) return;

  // Lấy ID từ thuộc tính data-id của chat-header
  const chatHeader = document.getElementById('chat-header');
  const conversationId = chatHeader.dataset.id;

  try {
    const response = await fetch(`${config.baseURL}/conversations/${conversationId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Không thể tải thông tin cuộc trò chuyện');
    }

    const conversation = await response.json();

    // Thêm conversation ID vào data attribute của sidebar
    const sidebar = document.getElementById('conversation-info-sidebar');
    sidebar.dataset.conversationId = conversationId;

    // Ẩn nút thêm thành viên nếu là cuộc trò chuyện private
    const addMemberBtn = document.querySelector('.member-actions');

    if (addMemberBtn) {
      addMemberBtn.style.display = conversation.type === 'private' ? 'none' : 'block';
    }

    // Kiểm tra xem người dùng hiện tại có phải là admin không
    const currentUser = getCurrentUser();
    const isAdmin = conversation.group_members?.find((m) => m.username === currentUser.username)?.role === 'admin';

    // Ẩn nút xóa group nếu không phải admin
    const deleteBtn = document.querySelector('.conversation-actions .danger-btn');
    if (deleteBtn) {
      deleteBtn.style.display = isAdmin ? 'block' : 'none';
    }

    // Cập nhật UI với thông tin cuộc trò chuyện
    document.getElementById('conversation-title').textContent = `${conversation.name}`;
    document.getElementById('conversation-avatar').src = conversation.avatar_url
      ? `${config.baseURL}/${conversation.avatar_url.replace(/^\/+/, '')}`
      : '../../assets/image/group-chat-default.jpg';

    // Render danh sách thành viên
    const memberList = document.getElementById('conversation-members');
    memberList.innerHTML = '';

    if (conversation.group_members) {
      // Sắp xếp thành viên: admin trước, sau đó đến thành viên thường
      const sortedMembers = [...conversation.group_members].sort((a, b) => {
        if (a.role === 'admin' && b.role !== 'admin') return -1;
        if (a.role !== 'admin' && b.role === 'admin') return 1;
        return 0;
      });

      sortedMembers.forEach((member) => {
        const li = document.createElement('li');
        li.className = 'member-item';
        li.style.cursor = 'pointer';

        const memberInfo = document.createElement('div');
        memberInfo.className = 'member-info';

        const isCurrentUser = member.username === currentUser.username;
        const displayName = isCurrentUser ? `${member.nickname || member.username} (Tôi)` : member.nickname || member.username;

        memberInfo.innerHTML = `
          <span>${displayName}</span>
          <small>${member.role === 'admin' ? '(Quản trị viên)' : ''}</small>
        `;

        li.appendChild(memberInfo);

        // Thêm sự kiện click để hiển thị modal thông tin người dùng
        li.addEventListener('click', async () => {
          if (isCurrentUser) {
            // Nếu là bản thân, gọi API lấy thông tin
            const token = localStorage.getItem('access_token');
            try {
              const response = await fetch(`${config.baseURL}/users/`, {
                headers: {
                  Authorization: `Bearer ${token}`,
                },
              });

              if (response.ok) {
                const userData = await response.json();
                // Hiển thị modal với thông tin bản thân
                const modal = document.getElementById('user-info-modal');
                modal.dataset.username = userData.username;
                modal.dataset.userId = userData.user_id;

                const avatarImg = document.getElementById('user-avatar');
                avatarImg.src = userData.avatar
                  ? `${config.baseURL}/${userData.avatar.replace(/^\/+/, '')}`
                  : '../../assets/image/private-chat-default.jpg';
                avatarImg.onerror = () => {
                  avatarImg.src = '../../assets/image/private-chat-default.jpg';
                };

                document.getElementById('user-username').textContent = userData.username;
                document.getElementById('user-nickname').textContent = userData.nickname || 'string';
                document.getElementById('user-email').textContent = userData.email || 'user@example.com';

                // Ẩn các nút không cần thiết
                document.getElementById('add-friend-btn').style.display = 'none';
                document.getElementById('unfriend-btn').style.display = 'none';
                document.getElementById('report-user-btn').style.display = 'none';

                // Hiển thị modal
                modal.style.display = 'flex';
              }
            } catch (error) {
              console.error('Lỗi khi lấy thông tin người dùng:', error);
              toast({
                title: 'Lỗi',
                message: 'Không thể tải thông tin người dùng',
                type: 'error',
              });
            }
          } else {
            // Nếu là thành viên khác, hiển thị modal thông tin
            showUserInfo(member.username);
          }
        });

        // Nếu người dùng là admin, hiển thị các nút quản lý
        if (isAdmin && member.role !== 'admin') {
          const actions = document.createElement('div');
          actions.className = 'member-actions';

          // Nút chỉ định làm admin
          const makeAdminBtn = document.createElement('button');
          makeAdminBtn.innerHTML = '<i class="fas fa-crown"></i>';
          makeAdminBtn.className = 'make-admin-btn';
          makeAdminBtn.title = 'Chỉ định làm admin';
          makeAdminBtn.onclick = () => makeAdmin(conversationId, member.username);
          actions.appendChild(makeAdminBtn);

          // Nút xóa thành viên
          const removeBtn = document.createElement('button');
          removeBtn.innerHTML = '<i class="fas fa-times"></i>';
          removeBtn.className = 'remove-member-btn';
          removeBtn.title = 'Xóa thành viên';
          removeBtn.onclick = () => removeMember(conversationId, member.username);
          actions.appendChild(removeBtn);

          li.appendChild(actions);
        }

        memberList.appendChild(li);
      });
    }
  } catch (error) {
    console.error('Lỗi khi tải thông tin cuộc trò chuyện:', error);
    toast({
      title: 'Lỗi',
      message: 'Không thể tải thông tin cuộc trò chuyện',
      type: 'error',
    });
  }
}

// Hàm chỉ định thành viên làm admin
async function makeAdmin(conversationId, username) {
  createModal({
    title: 'Xác nhận chỉ định admin',
    message: `Bạn có chắc chắn muốn chỉ định ${username} làm quản trị viên không?`,
    primaryButtonText: 'Xác nhận',
    secondaryButtonText: 'Hủy',
    showSecondaryButton: true,
    onPrimary: async () => {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      try {
        const response = await fetch(`${config.baseURL}/conversations/${conversationId}/members/${username}/admin`, {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: 'application/json',
          },
        });

        if (!response.ok) {
          const result = await response.json();
          toast({
            title: 'Lỗi',
            message: result.detail || 'Không thể chỉ định admin',
            type: 'error',
          });
          return;
        }

        toast({
          title: 'Thành công',
          message: 'Đã chỉ định admin thành công',
          type: 'success',
        });

        // Cập nhật lại danh sách thành viên
        loadConversationInfo();
      } catch (error) {
        console.error('Lỗi khi chỉ định admin:', error);
        toast({
          title: 'Lỗi',
          message: 'Không thể kết nối đến máy chủ',
          type: 'error',
        });
      }
    },
  });
}

// Hàm thêm thành viên mới
async function addMember(conversationId, username) {
  const token = localStorage.getItem('access_token');
  if (!token) return;

  try {
    const response = await fetch(`${config.baseURL}/conversations/${conversationId}/members?new_member_username=${username}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
      },
    });

    const result = await response.json();

    if (!response.ok) {
      toast({
        title: 'Lỗi',
        message: result.detail || 'Không thể thêm thành viên vào nhóm',
        type: 'error',
      });
      return;
    }

    toast({
      title: 'Thành công',
      message: 'Đã thêm thành viên vào nhóm',
      type: 'success',
    });

    // Cập nhật lại danh sách thành viên
    loadConversationInfo();
  } catch (error) {
    console.error('Lỗi khi thêm thành viên:', error);
    toast({
      title: 'Lỗi',
      message: 'Không thể kết nối đến máy chủ',
      type: 'error',
    });
  }
}

// Hàm xóa thành viên
async function removeMember(conversationId, username) {
  createModal({
    title: 'Xác nhận xóa thành viên',
    message: `Bạn có chắc chắn muốn xóa ${username} khỏi nhóm không?`,
    primaryButtonText: 'Xóa',
    secondaryButtonText: 'Hủy',
    showSecondaryButton: true,
    onPrimary: async () => {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      try {
        const response = await fetch(`${config.baseURL}/conversations/${conversationId}/members/${username}`, {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: 'application/json',
          },
        });

        if (!response.ok) {
          const result = await response.json();
          toast({
            title: 'Lỗi',
            message: result.detail || 'Không thể xóa thành viên khỏi nhóm',
            type: 'error',
          });
          return;
        }

        toast({
          title: 'Thành công',
          message: 'Đã xóa thành viên khỏi nhóm',
          type: 'success',
        });

        // Cập nhật lại danh sách thành viên
        loadConversationInfo();
      } catch (error) {
        console.error('Lỗi khi xóa thành viên:', error);
        toast({
          title: 'Lỗi',
          message: 'Không thể kết nối đến máy chủ',
          type: 'error',
        });
      }
    },
  });
}

// Hàm xóa cuộc trò chuyện
async function deleteConversation(conversationId) {
  createModal({
    title: 'Xác nhận xóa cuộc trò chuyện',
    message: 'Bạn có chắc chắn muốn xóa cuộc trò chuyện này không? Hành động này không thể hoàn tác.',
    primaryButtonText: 'Xóa',
    secondaryButtonText: 'Hủy',
    showSecondaryButton: true,
    onPrimary: async () => {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      try {
        const response = await fetch(`${config.baseURL}/conversations/${conversationId}`, {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: 'application/json',
          },
        });

        if (!response.ok) {
          const result = await response.json();
          toast({
            title: 'Lỗi',
            message: result.detail || 'Không thể xóa cuộc trò chuyện',
            type: 'error',
          });
          return;
        }

        toast({
          title: 'Thành công',
          message: 'Đã xóa cuộc trò chuyện',
          type: 'success',
        });

        // Đóng sidebar thông tin
        toggleConversationInfo();

        // Cập nhật lại danh sách cuộc trò chuyện
        loadConversations();
      } catch (error) {
        console.error('Lỗi khi xóa cuộc trò chuyện:', error);
        toast({
          title: 'Lỗi',
          message: 'Không thể kết nối đến máy chủ',
          type: 'error',
        });
      }
    },
  });
}

// Hàm mở modal thêm thành viên
function openAddMemberModal() {
  createModal({
    title: 'Thêm thành viên',
    message: 'Nhập tên người dùng cần thêm:',
    primaryButtonText: 'Thêm',
    secondaryButtonText: 'Hủy',
    showInput: true,
    inputPlaceholder: 'Tên người dùng',
    onPrimary: (username) => {
      if (username.trim()) {
        addMember(currentConversationId, username.trim());
      }
    },
  });
}

// Thêm vào window để có thể gọi từ HTML
window.logout = logout;
window.sendMessage = sendMessage;
window.sendImage = sendImage;
window.sendFile = sendFile;
window.toggleChatList = toggleChatList;
window.toggleNotiList = toggleNotiList;
window.toggleFriendsList = toggleFriendsList;
window.openCreateModal = openCreateModal;
window.closeCreateModal = closeCreateModal;
window.submitCreateConversation = submitCreateConversation;
window.toggleFriendRequestsList = toggleFriendRequestsList;
window.loadFriendRequests = loadFriendRequests;
window.markSelectedNoti = markSelectedNoti;
window.deleteSelectedNoti = deleteSelectedNoti;
window.checkUnreadNotifications = checkUnreadNotifications;
window.toggleConversationInfo = toggleConversationInfo;
window.openAddMemberModal = openAddMemberModal;
window.confirmDeleteConversation = deleteConversation;
window.makeAdmin = makeAdmin;

// Hàm tìm kiếm cuộc hội thoại
function searchConversations() {
  const searchInput = document.querySelector('#conversation-list .search');
  const filter = searchInput.value.toLowerCase();
  const chatList = document.querySelector('.chat-list');
  const chatItems = chatList.querySelectorAll('.chat-item');

  let hasResults = false; // Biến để kiểm tra có kết quả hay không

  chatItems.forEach((item) => {
    const conversationName = item.dataset.conversationName.toLowerCase();
    if (conversationName.includes(filter)) {
      item.style.display = ''; // Hiện cuộc hội thoại
      hasResults = true; // Có ít nhất một kết quả
    } else {
      item.style.display = 'none'; // Ẩn cuộc hội thoại
    }
  });

  // Hiển thị thông báo nếu không tìm thấy cuộc hội thoại nào
  const noResultItem = chatList.querySelector('.no-results');
  if (noResultItem) {
    noResultItem.style.display = hasResults ? 'none' : 'block';
  }
}

// Gắn sự kiện cho ô tìm kiếm
document.querySelector('#conversation-list .search').addEventListener('input', searchConversations);
