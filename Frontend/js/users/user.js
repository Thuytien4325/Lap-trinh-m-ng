function loadPage(url) {
  fetch(`../../html/users/${url}`) // sửa đúng đường dẫn tới file HTML
    .then((res) => res.text())
    .then((html) => {
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      const content = doc.querySelector('body').innerHTML;
      document.getElementById('main-content').innerHTML = content;

      // Gọi script tương ứng nếu cần
      if (url === 'chat.html') {
        import('../../js/users/chat.js');
      } else if (url === 'info.html') {
        // Nếu sau này bạn có info.js thì import ở đây
        // import('../../js/users/info.js');
      }
    });
}

window.loadChatPage = () => loadPage('chat.html');
window.loadInfoPage = () => loadPage('info.html');

// Tải mặc định là trang chat
loadChatPage();
