// static/script.js
const messageInput = document.querySelector('.form-control');
const sendButton = document.querySelector('.send-icon');
const msgPage = document.querySelector('.msg-page');
const fileInput = document.getElementById("fileInput");

// Địa chỉ server
const SERVER_IP = window.location.hostname; // Dùng hostname để linh hoạt IP
const SERVER_URL = `http://${SERVER_IP}:8000`;
const token = "your_jwt_token_here"; // Thay bằng token thực tế (lấy từ đăng nhập)
const WS_URL = `ws://${SERVER_IP}:8000/messages/ws/1?token=${token}`;
const conversationId = 1;

let socket = null;

// Kết nối WebSocket
function connectWebSocket() {
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        console.log("WebSocket connected successfully");
    };

    socket.onmessage = function(event) {
        let data = JSON.parse(event.data);
        displayMessage(data.sender_id, data.content, data.sent_at, data.message_id, data.file_url);
    };

    socket.onclose = (event) => {
        console.log("WebSocket disconnected:", event.code, event.reason);
        setTimeout(connectWebSocket, 1000); // Thử kết nối lại sau 1 giây
    };

    socket.onerror = (error) => {
        console.error("WebSocket error:", error);
    };
}

// Tải tin nhắn cũ khi mở trang
async function loadMessages() {
    try {
        const response = await fetch(`${SERVER_URL}/messages/${conversationId}`, {
            headers: {
                "Authorization": `Bearer ${token}` // Gửi token cho API HTTP
            }
        });
        if (!response.ok) throw new Error("Lỗi khi lấy tin nhắn");
        const messages = await response.json();
        messages.forEach(msg => {
            displayMessage(msg.sender_id, msg.content, msg.sent_at, msg.message_id, msg.file_url);
        });
    } catch (error) {
        console.error(error);
        alert("Không thể tải tin nhắn!");
    }
}

// Gửi tin nhắn văn bản
sendButton.addEventListener("click", () => {
    sendMessage();
});

messageInput.addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});

function sendMessage() {
    let messageText = messageInput.value.trim();
    if (messageText === "") return;

    let messageData = {
        content: messageText,
        file_url: null
    };

    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(messageData));
        messageInput.value = "";
    } else {
        alert("WebSocket chưa kết nối!");
    }
}

// Gửi file
async function sendFile() {
    let file = fileInput.files[0];
    if (!file) {
        alert("Vui lòng chọn file!");
        return;
    }

    let formData = new FormData();
    formData.append("file", file);

    let response = await fetch(`${SERVER_URL}/messages/upload`, {
        method: "POST",
        body: formData,
        headers: {
            "Authorization": `Bearer ${token}` // Gửi token cho API HTTP
        }
    });

    let result = await response.json();
    if (result.file_url) {
        let fileUrl = result.file_url;
        let messageData = {
            content: "",
            file_url: fileUrl
        };

        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(messageData));
            fileInput.value = "";
        } else {
            alert("WebSocket chưa kết nối!");
        }
    }
}

// Xóa tin nhắn
async function deleteMessage(messageId) {
    try {
        const response = await fetch(`${SERVER_URL}/messages/${messageId}`, {
            method: "DELETE",
            headers: {
                "Authorization": `Bearer ${token}` // Gửi token cho API HTTP
            }
        });
        if (!response.ok) throw new Error("Lỗi khi xóa tin nhắn");
        msgPage.innerHTML = "";
        loadMessages();
    } catch (error) {
        console.error(error);
        alert("Không thể xóa tin nhắn!");
    }
}

// Hiển thị tin nhắn & file
function displayMessage(senderId, content, sentAt, messageId, fileUrl) {
    let msgContainer = document.createElement("div");
    msgContainer.classList.add(senderId === 1 ? "outgoing-chats" : "received-chats");

    let imgDiv = document.createElement("div");
    imgDiv.classList.add(senderId === 1 ? "outgoing-chats-img" : "received-chats-img");
    let img = document.createElement("img");
    img.src = senderId === 1 ? "https://via.placeholder.com/50/FF0000/FFFFFF?text=U1" : "https://via.placeholder.com/50/00FF00/FFFFFF?text=U2";
    imgDiv.appendChild(img);

    let msgBox = document.createElement("div");
    msgBox.classList.add(senderId === 1 ? "outgoing-msg" : "received-msg");

    let msgContent = document.createElement("div");
    msgContent.classList.add(senderId === 1 ? "outgoing-chats-msg" : "received-msg-inbox");

    if (fileUrl) {
        const isImage = fileUrl.match(/\.(jpeg|jpg|png|gif)$/i);
        if (isImage) {
            let img = document.createElement("img");
            img.src = fileUrl;
            img.classList.add("file-img");
            msgContent.appendChild(img);
        } else {
            let fileLink = document.createElement("a");
            fileLink.href = fileUrl;
            fileLink.innerText = "📎 File đính kèm";
            fileLink.target = "_blank";
            msgContent.appendChild(fileLink);
        }
    } else if (content) {
        let msgText = document.createElement("p");
        msgText.innerText = content;
        msgContent.appendChild(msgText);
    }

    let timeSpan = document.createElement("span");
    timeSpan.classList.add("time");
    const sentTime = new Date(sentAt);
    timeSpan.innerText = sentTime.toLocaleTimeString() + " | " + sentTime.toLocaleDateString();
    msgContent.appendChild(timeSpan);

    if (senderId === 1) {
        let deleteBtn = document.createElement("button");
        deleteBtn.classList.add("delete-btn");
        deleteBtn.innerText = "Xóa";
        deleteBtn.onclick = () => deleteMessage(messageId);
        msgContent.appendChild(deleteBtn);
    }

    msgBox.appendChild(msgContent);
    msgContainer.appendChild(imgDiv);
    msgContainer.appendChild(msgBox);
    msgPage.appendChild(msgContainer);

    msgPage.scrollTop = msgPage.scrollHeight;
}

// Tải tin nhắn và kết nối WebSocket khi mở trang
window.onload = () => {
    loadMessages();
    connectWebSocket();
};