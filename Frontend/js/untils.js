export function toast({ title = '', message = '', type = 'info', duration = 3000 }) {
  const main = document.getElementById('toast');
  if (main) {
    const toast = document.createElement('div');
    const autoRemoveID = setTimeout(() => {
      main.removeChild(toast);
    }, duration + 1000);

    toast.onclick = (e) => {
      if (e.target.closest('.toast__close')) {
        main.removeChild(toast);
        clearTimeout(autoRemoveID);
      }
    };

    const icons = {
      info: 'fa-solid fa-circle-info',
      success: 'fa-solid fa-circle-check',
      warning: 'fa-solid fa-triangle-exclamation',
      error: 'fa-solid fa-circle-xmark',
    };

    const icon = icons[type];
    const delay = (duration / 1000).toFixed(2);
    toast.classList.add('toast', `toast--${type}`);
    toast.style.animation = `slideInLeft ease 0.3s, fadeOut linear 1s ${delay}s forwards`;
    toast.innerHTML = `
      <div class="toast__icon">
        <i class="${icon}"></i>
      </div>
      <div class="toast__body">
        <h3 class="toast__title">${title}</h3>
        <p class="toast__msg">${message}</p>
      </div>
      <div class="toast__close">
        <i class="fa-solid fa-xmark"></i>
      </div>
    `;
    main.appendChild(toast);
  }
}

export function createModal({
  title = 'Thông báo',
  message = '',
  primaryButtonText = 'OK',
  onPrimary = null,
  secondaryButtonText = 'Hủy',
  onSecondary = null,
  onClose = null,
  showSecondaryButton = false,
}) {
  const existing = document.querySelector('.modal-overlay');
  if (existing) existing.remove();

  const modalHTML = `
    <div class="modal-overlay show">
      <div class="modal">
        <div class="close-btn"><i class="fa-solid fa-xmark"></i></div>
        <div class="modal-header">
          <h3>${title}</h3>
        </div>
        <div class="modal-content">
          <p>${message}</p>
        </div>
        <div class="modal-buttons">
          ${showSecondaryButton ? `<button class="btn btn-secondary btn-secondary-action">${secondaryButtonText}</button>` : ''}
          <button class="btn btn-primary btn-primary-action">${primaryButtonText}</button>
        </div>
      </div>
    </div>
  `;

  const wrapper = document.createElement('div');
  wrapper.innerHTML = modalHTML.trim();
  const modalEl = wrapper.firstElementChild;
  document.body.appendChild(modalEl);

  // Nút đóng (X)
  modalEl.querySelector('.close-btn').onclick = () => {
    modalEl.remove();
    if (typeof onClose === 'function') onClose();
  };

  // Nút chính
  modalEl.querySelector('.btn-primary-action').onclick = () => {
    modalEl.remove();
    if (typeof onPrimary === 'function') onPrimary();
  };

  // Nút phụ nếu có
  if (showSecondaryButton) {
    modalEl.querySelector('.btn-secondary-action').onclick = () => {
      modalEl.remove();
      if (typeof onSecondary === 'function') onSecondary();
    };
  }
}

export function formatVNTime(timestamp) {
  const date = new Date(timestamp);
  const formatter = new Intl.DateTimeFormat('vi-VN', {
    timeZone: 'Asia/Ho_Chi_Minh',
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
  });

  return formatter.format(date);
}
