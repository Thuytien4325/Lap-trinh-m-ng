import { toast, createModal } from "../untils.js";
import config from "../config.js";
import initContextMenu from "../context-menu.js";
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
  const userStr = localStorage.getItem("user");
  if (!userStr) return null;

  try {
    return JSON.parse(userStr);
  } catch (e) {
    console.error("Lỗi khi parse user từ localStorage:", e);
    return null;
  }
}

// Load cuộc trò chuyện
async function loadConversations() {
  const token = localStorage.getItem("access_token");
  if (!token) {
    console.error("Không có token đăng nhập");
    return;
  }

  try {
    const response = await fetch(`${config.baseURL}/conversations/`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      console.error("Lỗi khi gọi API:", response.status);
      return;
    }

    const conversations = await response.json();

    conversations.sort((a, b) => {
      const timeA = a.last_message_time
        ? new Date(a.last_message_time)
        : new Date(0);
      const timeB = b.last_message_time
        ? new Date(b.last_message_time)
        : new Date(0);
      return timeB - timeA;
    });

    const chatList = document.querySelector(".chat-list");
    chatList.innerHTML = "";

    if (conversations.length > 0) {
      conversations.forEach((conv) => {
        const li = document.createElement("li");
        li.className = "chat-item";

        li.dataset.conversationId = conv.conversation_id;
        li.dataset.conversationName =
          conv.name || `Cuộc trò chuyện ${conv.conversation_id}`;

        li.onclick = () => {
          const id = li.dataset.conversationId;
          const name = li.dataset.conversationName;
          currentConversationId = id;
          loadMessages(id, name, true);
        };

        const avatar = document.createElement("img");
        avatar.className = "avatar";

        const fixedAvatarUrl = conv.avatar_url
          ? conv.avatar_url.startsWith("http")
            ? conv.avatar_url
            : `${config.baseURL}${conv.avatar_url.replace(/^\/+/, "")}`
          : conv.type === "group"
          ? "../../assets/image/group-chat-default.jpg"
          : "../../assets/image/private-chat-default.jpg";

        avatar.src = fixedAvatarUrl;
        avatar.alt = "avatar";

        const nameContainer = document.createElement("span");
        nameContainer.className = "chat-name";

        const typeIcon = document.createElement("i");
        typeIcon.className =
          "type-icon fas " + (conv.type === "group" ? "fa-users" : "fa-user");

        const nameText = document.createTextNode(
          " " + (conv.name || `Cuộc trò chuyện ${conv.conversation_id}`)
        );

        nameContainer.appendChild(typeIcon);
        nameContainer.appendChild(nameText);

        li.appendChild(avatar);
        li.appendChild(nameContainer);
        chatList.appendChild(li);
      });

      const latestConversation = conversations[0];
      currentConversationId = latestConversation.conversation_id;
      loadMessages(
        latestConversation.conversation_id,
        latestConversation.name ||
          `Cuộc trò chuyện ${latestConversation.conversation_id}`,
        true
      );
    }
  } catch (error) {
    console.error("Lỗi khi fetch:", error);
  }
}

// Load tin nhắn
async function loadMessages(
  conversationId,
  conversationName,
  isInitial = true
) {
  const token = localStorage.getItem("access_token");
  if (!token) return;

  const currentUser = getCurrentUser();
  const chatContent = document.getElementById("chat-content");

  if (isInitial) {
    document.getElementById("conversation-name").textContent = conversationName;
    chatContent.innerHTML = "";
    messageOffset = 0;
  }

  if (isLoadingMessages) return;
  isLoadingMessages = true;

  try {
    const response = await fetch(
      `${config.baseURL}/messages/${conversationId}/messages?limit=${messageLimit}&offset=${messageOffset}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
        },
      }
    );

    if (!response.ok) {
      console.error("Lỗi khi gọi API lấy tin nhắn:", response.status);
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
  } catch (error) {
    console.error("Lỗi khi fetch tin nhắn:", error);
  } finally {
    isLoadingMessages = false;
  }
}

function createAttachmentElement(att) {
  const fixedFileUrl = att.file_url.startsWith("http")
    ? att.file_url
    : `${config.baseURL}/${att.file_url.replace(/^\/+/, "")}`;

  const isImage = /\.(jpg|jpeg|png|gif)$/i.test(fixedFileUrl);

  // Nếu là ảnh
  if (isImage) {
    const img = document.createElement("img");
    img.src = fixedFileUrl;
    img.className = "attachment-img has-context";
    img.alt = "Ảnh đính kèm";
    img.setAttribute("data-url", fixedFileUrl);

    img.onerror = () => {
      const fileWrapper = document.createElement("div");
      fileWrapper.className = "file-wrapper";
      fileWrapper.setAttribute("data-url", fixedFileUrl);

      const fallbackIcon = document.createElement("i");
      fallbackIcon.className = "fas fa-exclamation-circle file-icon";

      const fallbackText = document.createElement("span");
      fallbackText.className = "file-fallback-text";
      fallbackText.textContent = "Ảnh không còn tồn tại!";

      fileWrapper.appendChild(fallbackIcon);
      fileWrapper.appendChild(fallbackText);

      img.replaceWith(fileWrapper);
    };

    return img;
  }

  // Nếu là file khác
  const fileWrapper = document.createElement("div");
  fileWrapper.className = "file-wrapper";
  fileWrapper.setAttribute("data-url", fixedFileUrl);
  fileWrapper.classList.add("has-context");

  const fileIcon = document.createElement("i");
  let iconClass = "fa-file-alt";

  if (/\.(pdf)$/i.test(fixedFileUrl)) {
    iconClass = "fa-file-pdf";
  } else if (/\.(mp4)$/i.test(fixedFileUrl)) {
    iconClass = "fa-file-video";
  } else if (/\.(mp3)$/i.test(fixedFileUrl)) {
    iconClass = "fa-file-audio";
  }

  fileIcon.className = `fas ${iconClass} file-icon`;
  fileWrapper.appendChild(fileIcon);

  const fileLink = document.createElement("a");
  fileLink.href = fixedFileUrl;
  fileLink.target = "_blank";
  fileLink.className = "attachment-file";
  fileLink.textContent = "";

  fileWrapper.appendChild(fileLink);

  // Gửi HEAD request để kiểm tra file tồn tại
  fetch(fixedFileUrl, { method: "HEAD" })
    .then((res) => {
      if (!res.ok) throw new Error("File not found");
    })
    .catch(() => {
      fileWrapper.classList.remove("has-context");
      fileWrapper.innerHTML = "";

      const errorIcon = document.createElement("i");
      errorIcon.className = "fas fa-exclamation-circle file-icon";

      const errorText = document.createElement("span");
      errorText.className = "file-fallback-text";
      errorText.textContent = "File không còn tồn tại!";

      fileWrapper.appendChild(errorIcon);
      fileWrapper.appendChild(errorText);
    });

  return fileWrapper;
}

// Thêm hàm này để hiển thị tin nhắn mới từ WebSocket
function appendMessageToUI(msg) {
  const currentUser = getCurrentUser();
  const chatContent = document.getElementById("chat-content");

  const isCurrentUser = msg.sender_id === currentUser.user_id;
  const messageDiv = document.createElement("div");
  messageDiv.classList.add("message", isCurrentUser ? "sent" : "received");

  if (!isCurrentUser) {
    const senderName = document.createElement("div");
    senderName.className = "sender-name";
    senderName.textContent = msg.sender_nickname;
    senderName.dataset.username = msg.sender_username;
    senderName.style.cursor = "pointer";
    senderName.onclick = () => showUserInfo(msg.sender_username);
    messageDiv.appendChild(senderName);
  }

  const textDiv = document.createElement("div");
  textDiv.className = "message-text";
  textDiv.innerHTML = msg.content;
  messageDiv.appendChild(textDiv);

  if (msg.attachments && msg.attachments.length > 0) {
    const attContainer = document.createElement("div");
    attContainer.className = "attachments";

    msg.attachments.forEach((att) => {
      const attachmentEl = createAttachmentElement(att);
      attContainer.appendChild(attachmentEl);
    });

    messageDiv.appendChild(attContainer);
  }

  const time = document.createElement("span");
  time.className = "timestamp";
  const date = new Date(msg.timestamp);
  const vnTime = new Date(date.getTime() + 7 * 60 * 60 * 1000); // Cộng thêm 7 tiếng
  const hours = vnTime.getHours().toString().padStart(2, "0");
  const minutes = vnTime.getMinutes().toString().padStart(2, "0");
  const day = vnTime.getDate().toString().padStart(2, "0");
  const month = (vnTime.getMonth() + 1).toString().padStart(2, "0");
  time.textContent = `${hours}:${minutes} ${day}/${month}`;
  messageDiv.appendChild(time);

  chatContent.appendChild(messageDiv);
  chatContent.scrollTop = chatContent.scrollHeight;
}

// Phục vụ loadMessages: thêm tin nhắn lên đầu khi cuộn
function appendMessageToTop(msg, currentUser) {
  const chatContent = document.getElementById("chat-content");

  const isCurrentUser = msg.sender_id === currentUser.user_id;
  const messageDiv = document.createElement("div");
  messageDiv.classList.add("message", isCurrentUser ? "sent" : "received");

  if (!isCurrentUser) {
    const senderName = document.createElement("div");
    senderName.className = "sender-name";
    senderName.textContent = msg.sender_nickname;
    senderName.dataset.username = msg.sender_username;
    senderName.style.cursor = "pointer";
    senderName.onclick = () => showUserInfo(msg.sender_username);
    messageDiv.appendChild(senderName);
  }

  const textDiv = document.createElement("div");
  textDiv.className = "message-text";
  textDiv.innerHTML = msg.content;
  messageDiv.appendChild(textDiv);

  if (msg.attachments && msg.attachments.length > 0) {
    const attContainer = document.createElement("div");
    attContainer.className = "attachments";

    msg.attachments.forEach((att) => {
      const attachmentEl = createAttachmentElement(att);
      attContainer.appendChild(attachmentEl);
    });

    messageDiv.appendChild(attContainer);
  }

  const time = document.createElement("span");
  time.className = "timestamp";
  const date = new Date(msg.timestamp);
  const vnTime = new Date(date.getTime() + 7 * 60 * 60 * 1000);
  const hours = vnTime.getHours().toString().padStart(2, "0");
  const minutes = vnTime.getMinutes().toString().padStart(2, "0");
  const day = vnTime.getDate().toString().padStart(2, "0");
  const month = (vnTime.getMonth() + 1).toString().padStart(2, "0");
  time.textContent = `${hours}:${minutes} ${day}/${month}`;
  messageDiv.appendChild(time);

  chatContent.insertBefore(messageDiv, chatContent.firstChild);
}

function logout() {
  createModal({
    title: "Xác nhận đăng xuất",
    message: "Bạn có chắc chắn muốn đăng xuất không?",
    primaryButtonText: "Đăng xuất",
    secondaryButtonText: "Hủy",
    showSecondaryButton: true,
    onPrimary: () => {
      localStorage.clear();
      toast({
        title: "Đăng xuất thành công!",
        message: "Đang đăng xuất...",
        type: "success",
      });
      setTimeout(() => {
        window.location.href = "../auth/login.html";
      }, 1500);
    },
  });
}

document.addEventListener("click", function (e) {
  if (e.target.classList.contains("attachment-img")) {
    const modal = document.getElementById("image-modal");
    const modalImg = document.getElementById("modal-image");
    modal.style.display = "flex";
    modalImg.src = e.target.src;
  }

  if (
    e.target.classList.contains("close-btn") ||
    e.target.id === "image-modal"
  ) {
    document.getElementById("image-modal").style.display = "none";
  }

  const modal = document.getElementById("user-info-modal");
  if (e.target === modal) {
    closeUserInfoModal();
  }
});

async function sendMessage() {
  const token = localStorage.getItem("access_token");
  if (!token || !currentConversationId) {
    console.error("Thiếu token hoặc chưa chọn cuộc trò chuyện");
    return;
  }

  const input = document.querySelector(".chat-input");
  const content = input.value.trim();

  if (!content && selectedFiles.length === 0) {
    return;
  }

  const formData = new FormData();
  selectedFiles.forEach((file) => formData.append("files", file));
  if (selectedFiles.length > 0) {
    isReloadConfirmed = false;
  }
  const query = new URLSearchParams({ conversation_id: currentConversationId });
  if (content) {
    query.append("content", content);
  }

  try {
    const response = await fetch(
      `${config.baseURL}/messages/?${query.toString()}`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
        },
        body: formData,
      }
    );

    if (!response.ok) {
      console.error("Gửi tin nhắn thất bại:", response.status);
      return;
    }
    const sentMessage = await response.json(); // <- giả sử API trả về tin nhắn đã lưu
    appendMessageToUI(sentMessage);
    input.value = "";
    selectedFiles = [];
  } catch (error) {
    console.error("Lỗi khi gửi tin nhắn:", error);
  }
}

function sendImage(event) {
  const file = event.target.files[0];
  if (file) {
    selectedFiles.push(file);
    sendMessage();
    isReloadConfirmed = false;

    const shouldReload = confirm(
      "Bạn vừa gửi tệp đính kèm.\nTải lại trang để cập nhật?"
    );
    if (shouldReload) {
      localStorage.setItem("lastConversationId", currentConversationId);
    } else {
      localStorage.setItem("lastConversationId", currentConversationId);
    }
  }
}

function sendFile(event) {
  const file = event.target.files[0];
  if (file) {
    selectedFiles.push(file);
    sendMessage();
    isReloadConfirmed = false;

    const shouldReload = confirm(
      "Bạn vừa gửi tệp đính kèm.\nTải lại trang để cập nhật?"
    );
    if (shouldReload) {
      localStorage.setItem("lastConversationId", currentConversationId);
    } else {
      localStorage.setItem("lastConversationId", currentConversationId);
    }
  }
}

document.getElementById("chat-content").addEventListener("scroll", function () {
  if (this.scrollTop === 0 && currentConversationId) {
    loadMessages(currentConversationId, "", false);
  }
});

// Thêm hàm kết nối WebSocket
function connectWebSocket() {
  const user = getCurrentUser();
  if (!user) return;

  socket = new WebSocket(`${config.wsUrl}/ws/user/${user.username}`);

  socket.onopen = () => {
    console.log("✅ WebSocket đã kết nối");
  };

  socket.onmessage = async (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log("Tin nhắn từ WebSocket:", data);
      if (data.type === "url_update") {
        const updateEvent = new CustomEvent("url-update", {
          detail: data.data,
        });
        window.dispatchEvent(updateEvent);
      }

      // Xử lý tin nhắn mới
      if (data.type === "new_message") {
        const msg = {
          ...data.message,
          sender_nickname: data.message.sender_nickname || "Người gửi",
          sender_username: data.message.sender_username || "unknown",
        };
        console.log("msg", msg);
        // Nếu tin nhắn thuộc cuộc trò chuyện hiện tại
        if (String(currentConversationId) === String(data.conversation_id)) {
          if (msg.attachments && msg.attachments.length > 0) {
            isReloadConfirmed = false;

            const shouldReload = confirm(
              "Bạn vừa nhận được tệp đính kèm.\nTải lại trang để cập nhật?"
            );
            if (shouldReload) {
              localStorage.setItem("lastConversationId", currentConversationId);
            } else {
              localStorage.setItem("lastConversationId", currentConversationId);
            }
          } else {
            appendMessageToUI(msg);
          }
        } else {
          loadConversations();
        }
      }
    } catch (error) {
      console.error("Lỗi xử lý tin nhắn WebSocket:", error);
    }
  };

  socket.onclose = () => {
    console.log("❌ WebSocket đã đóng, đang kết nối lại...");
    setTimeout(connectWebSocket, 2000);
  };

  socket.onerror = (error) => {
    console.error("⚠️ Lỗi WebSocket:", error);
  };
}

// window.addEventListener("beforeunload", (e) => {
//   if (!isReloadConfirmed) {
//     e.preventDefault();
//     e.returnValue = "";
//   }
// });

// Sửa lại phần khởi tạo khi trang load
document.addEventListener("DOMContentLoaded", () => {
  // Kiểm tra xem có conversationId được lưu từ lần reload trước không
  const lastConversationId = localStorage.getItem("lastConversationId");
  if (lastConversationId) {
    currentConversationId = lastConversationId;
    localStorage.removeItem("lastConversationId"); // Xóa sau khi đã lấy
  }

  loadConversations();
  connectWebSocket();
});

// Thêm hàm đóng modal thông tin người dùng
function closeUserInfoModal() {
  document.getElementById("user-info-modal").style.display = "none";
}

// Thêm hàm lấy và hiển thị thông tin người dùng
async function showUserInfo(username) {
  try {
    const token = localStorage.getItem("access_token");
    const response = await fetch(
      `${config.baseURL}/users/search?query=${username}&search_by_nickname=false`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (response.ok) {
      const users = await response.json();
      const userData = users[0];
      if (userData) {
        const avatarUrl = userData.avatar
          ? userData.avatar.startsWith("http")
            ? userData.avatar
            : `${config.baseURL}/${userData.avatar.replace(/^\/+/, "")}`
          : "../../assets/image/private-chat-default.jpg";

        const avatarImg = document.getElementById("user-avatar");
        avatarImg.src = avatarUrl;
        avatarImg.onerror = () => {
          avatarImg.src = "../../assets/image/private-chat-default.jpg";
        };

        document.getElementById(
          "user-username"
        ).textContent = `${userData.username}`;
        document.getElementById("user-nickname").textContent =
          userData.nickname || "string";
        document.getElementById("user-email").textContent =
          userData.email || "user@example.com";

        // Sử dụng flex để căn giữa modal
        document.getElementById("user-info-modal").style.display = "flex";
      }
    }
  } catch (error) {
    console.error("Lỗi khi lấy thông tin người dùng:", error);
  }
}

// Thêm vào window để có thể gọi từ HTML
window.closeUserInfoModal = closeUserInfoModal;

const chatContainer = document.getElementById("chat-content"); // container hiển thị tin nhắn
const scrollBtn = document.getElementById("scrollToBottomBtn");

// Kiểm tra xem người dùng có đang ở gần đáy không
function isUserAtBottom() {
  return (
    chatContainer.scrollHeight - chatContainer.scrollTop <=
    chatContainer.clientHeight + 50
  );
}

// Hiện hoặc ẩn nút
function showScrollButton() {
  scrollBtn.style.opacity = "1";
  scrollBtn.style.pointerEvents = "auto";
}

function hideScrollButton() {
  scrollBtn.style.opacity = "0";
  scrollBtn.style.pointerEvents = "none";
}

// Gắn sự kiện khi người dùng cuộn
chatContainer.addEventListener("scroll", () => {
  if (!isUserAtBottom()) {
    showScrollButton();
  } else {
    hideScrollButton();
  }
});

// Khi người dùng bấm nút
scrollBtn.addEventListener("click", () => {
  chatContainer.scrollTo({
    top: chatContainer.scrollHeight,
    behavior: "smooth",
  });
});

function toggleChatList() {
  const chatList = document.getElementById("sidebar");
  if (!chatList) return;

  const currentDisplay = window.getComputedStyle(chatList).display;

  if (currentDisplay === "none") {
    chatList.style.display = "flex";
    // Trigger reflow để hiệu ứng hoạt động
    void chatList.offsetHeight;
    chatList.classList.remove("hiding");
  } else {
    chatList.classList.add("hiding");
    setTimeout(() => {
      chatList.style.display = "none";
    }, 300); // khớp với thời gian transition
  }
}

window.logout = logout;
window.sendMessage = sendMessage;
window.sendImage = sendImage;
window.sendFile = sendFile;
window.toggleChatList = toggleChatList;
document.addEventListener("DOMContentLoaded", () => {
  // Kiểm tra xem có conversationId được lưu từ lần reload trước không
  const lastConversationId = localStorage.getItem("lastConversationId");
  if (lastConversationId) {
    currentConversationId = lastConversationId;
    localStorage.removeItem("lastConversationId"); // Xóa sau khi đã lấy
  }

  loadConversations();
  connectWebSocket();

  // Khởi tạo context menu cho file đính kèm
  initContextMenu({
    selector: ".has-context",
    items: [
      { action: "download", label: "Tải xuống" },
      { action: "copy", label: "Sao chép liên kết" },
    ],
    onAction: (action, fileUrl, element) => {
      switch (action) {
        case "download": {
          try {
            const urlParts = new URL(fileUrl).pathname.split("/");
            const conversationIdIndex = urlParts.indexOf("conversations") + 1;
            const conversationId = urlParts[conversationIdIndex];
            const filename = urlParts.pop();
            const isImage = /\.(jpg|jpeg|png|gif)$/i.test(filename);

            const downloadUrl = isImage
              ? `${config.baseURL}/conversations/download/${conversationId}/${filename}`
              : fileUrl;

            const a = document.createElement("a");
            a.href = downloadUrl;
            a.download = filename;
            a.style.display = "none";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

            setTimeout(() => {
              toast({
                title: "Đã gửi yêu cầu tải",
                message: "Nếu trình duyệt hỏi vị trí lưu, vui lòng xác nhận.",
                type: "info",
              });
            }, 300);
          } catch (e) {
            console.error("Tải file thất bại:", e);
            toast({
              title: "Lỗi",
              message: "Không thể tải file",
              type: "error",
            });
          }
          break;
        }

        case "copy":
          navigator.clipboard
            .writeText(fileUrl)
            .then(() => {
              toast({
                title: "Thành công!",
                message: "Đã sao chép liên kết thành công!",
                type: "success",
              });
            })
            .catch(() => {
              toast({ title: "Sao chép thất bại", type: "error" });
            });
          break;
      }
    },
  });

  // Ngăn context menu toàn trang, chỉ cho phép ở .has-context
  // document.addEventListener('contextmenu', function (e) {
  //   if (!e.target.closest('.has-context')) {
  //     e.preventDefault();
  //   }
  // });
});
