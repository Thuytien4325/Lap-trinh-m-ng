// Lấy các phần tử từ HTML
const messageInput = document.querySelector('.form-control'); // Ô nhập tin nhắn
const sendButton = document.querySelector('.send-icon'); // Nút gửi
const msgPage = document.querySelector('.msg-page'); // Khu vực hiển thị tin nhắn

// Hàm để lấy thời gian hiện tại (định dạng: HH:MM PM | Month Day)
function getCurrentTime() {
    const now = new Date();
    const hours = now.getHours() % 12 || 12; // Chuyển sang định dạng 12 giờ
    const minutes = now.getMinutes().toString().padStart(2, '0'); // Thêm số 0 nếu phút < 10
    const ampm = now.getHours() >= 12 ? 'PM' : 'AM';
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const month = monthNames[now.getMonth()];
    const day = now.getDate();
    return `${hours}:${minutes} ${ampm} | ${month} ${day}`;
}

// Hàm để thêm tin nhắn đi (outgoing)
function addNewMessage() {
    // Lấy nội dung từ ô nhập
    const messageText = messageInput.value.trim();

    // Kiểm tra nếu ô nhập không rỗng
    if (messageText !== '') {
        // Tạo một div cho tin nhắn đi
        const outgoingChat = document.createElement('div');
        outgoingChat.classList.add('outgoing-chats');

        // Tạo div cho ảnh đại diện
        const outgoingChatImg = document.createElement('div');
        outgoingChatImg.classList.add('outgoing-chats-img');
        outgoingChatImg.innerHTML = '<img src="https://via.placeholder.com/50/FF0000/FFFFFF?text=U1">';

        // Tạo div cho nội dung tin nhắn
        const outgoingMsg = document.createElement('div');
        outgoingMsg.classList.add('outgoing-msg');

        const outgoingChatsMsg = document.createElement('div');
        outgoingChatsMsg.classList.add('outgoing-chats-msg');
        outgoingChatsMsg.innerHTML = `
            <p>${messageText}</p>
            <span class="time">${getCurrentTime()}</span>
        `;

        // Gắn các phần tử vào nhau
        outgoingMsg.appendChild(outgoingChatsMsg);
        outgoingChat.appendChild(outgoingChatImg);
        outgoingChat.appendChild(outgoingMsg);

        // Thêm tin nhắn mới vào khu vực msg-page
        msgPage.appendChild(outgoingChat);

        // Xóa nội dung trong ô nhập
        messageInput.value = '';

        // Tự động cuộn xuống tin nhắn mới nhất
        msgPage.scrollTop = msgPage.scrollHeight;

        // Giả lập tin nhắn đến sau 1 giây
        setTimeout(addReceivedMessage, 1000);
    }
}

// Hàm giả lập tin nhắn đến (received)
function addReceivedMessage() {
    const receivedChat = document.createElement('div');
    receivedChat.classList.add('received-chats');

    const receivedChatImg = document.createElement('div');
    receivedChatImg.classList.add('received-chats-img');
    receivedChatImg.innerHTML = '<img src="https://via.placeholder.com/50/00FF00/FFFFFF?text=U2">';

    const receivedMsg = document.createElement('div');
    receivedMsg.classList.add('received-msg');

    const receivedMsgInbox = document.createElement('div');
    receivedMsgInbox.classList.add('received-msg-inbox');
    receivedMsgInbox.innerHTML = `
        <p>Hi! This is an auto-reply.</p>
        <span class="time">${getCurrentTime()}</span>
    `;

    receivedMsg.appendChild(receivedMsgInbox);
    receivedChat.appendChild(receivedChatImg);
    receivedChat.appendChild(receivedMsg);

    msgPage.appendChild(receivedChat);

    // Tự động cuộn xuống tin nhắn mới nhất
    msgPage.scrollTop = msgPage.scrollHeight;
}

// Thêm sự kiện khi nhấn nút gửi
sendButton.addEventListener('click', addNewMessage);

// Thêm sự kiện khi nhấn phím Enter
messageInput.addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        addNewMessage();
    }
});