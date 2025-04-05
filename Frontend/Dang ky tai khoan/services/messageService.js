//Gửi/nhận tin nhắn
// ✅ Gửi và nhận tin nhắn qua WebSocket
const socket = io("http://localhost:8000"); // Socket.io server

// Nhận tin nhắn mới
socket.on("tin-nhan-moi", (data) => {
  console.log("Tin nhắn đến:", data);
  // TODO: thêm logic hiển thị tin nhắn lên giao diện
  // Ví dụ: appendToChatBox(data)
});

// Gửi tin nhắn
function sendMessage(message) {
  if (message.trim()) {
    socket.emit("gui-tin-nhan", { message });
  }
}


//Hiện thông báo
function showNotification(message) {
  const notification = document.getElementById('notification');
  notification.innerText = message;
  notification.classList.add('show');
  setTimeout(() => {
      notification.classList.remove('show');
  }, 3000);
}

//Phát âm thanh khi có tin nhắn mới
function playSound() {
  const audio = new Audio('/assets/image/thongbao.mp3');
  audio.play();
}

//Thu hồi tin nhắn
function thuHoiTinNhan() {
  const message = document.getElementById('message').value;
  if (!message) return;
  socket.emit('thu-hoi-tin-nhan', message);
  document.getElementById('message').value = '';
}
