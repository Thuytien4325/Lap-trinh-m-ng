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
  showInput = false,
  inputPlaceholder = '',
}) {
  const existing = document.querySelector('.modal-overlay');
  if (existing) existing.remove();

  const modalOverlay = document.createElement('div');
  modalOverlay.className = 'modal-overlay';

  const modalContent = document.createElement('div');
  modalContent.className = 'modal';

  const closeBtn = document.createElement('div');
  closeBtn.className = 'close-btn';
  closeBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';

  const modalHeader = document.createElement('div');
  modalHeader.className = 'modal-header';

  const modalTitle = document.createElement('h3');
  modalTitle.textContent = title;

  const modalMessage = document.createElement('p');
  modalMessage.textContent = message;

  const buttonContainer = document.createElement('div');
  buttonContainer.className = 'modal-buttons';

  let inputElement = null;
  if (showInput) {
    inputElement = document.createElement('input');
    inputElement.type = 'text';
    inputElement.className = 'modal-input';
    inputElement.placeholder = inputPlaceholder;
  }

  const primaryButton = document.createElement('button');
  primaryButton.className = 'btn btn-primary btn-primary-action';
  primaryButton.textContent = primaryButtonText;
  primaryButton.onclick = () => {
    if (showInput) {
      onPrimary(inputElement.value);
    } else {
      onPrimary();
    }
    modalOverlay.remove();
  };

  if (showSecondaryButton && secondaryButtonText) {
    const secondaryButton = document.createElement('button');
    secondaryButton.className = 'btn btn-secondary btn-secondary-action';
    secondaryButton.textContent = secondaryButtonText;
    secondaryButton.onclick = () => {
      if (onSecondary) onSecondary();
      modalOverlay.remove();
    };
    buttonContainer.appendChild(secondaryButton);
  }

  buttonContainer.appendChild(primaryButton);
  modalContent.appendChild(closeBtn);
  modalContent.appendChild(modalHeader);
  modalContent.appendChild(modalMessage);

  if (showInput) {
    modalContent.appendChild(inputElement);
  }

  modalContent.appendChild(buttonContainer);
  modalOverlay.appendChild(modalContent);
  document.body.appendChild(modalOverlay);

  // Nút đóng (X)
  closeBtn.onclick = () => {
    modalOverlay.remove();
    if (typeof onClose === 'function') onClose();
  };

  // Focus vào input nếu có
  if (inputElement) {
    setTimeout(() => inputElement.focus(), 0);
  }
}

// Định dạng thời gian theo yêu cầu: phút:giờ (12 giờ)
export const formatDate = (date) => {
  const minutes = date.getMinutes().toString().padStart(2, '0');
  let hours = date.getHours();
  const ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12;
  hours = hours ? hours : 12; // Nếu là 0 giờ thì hiển thị là 12
  const day = date.getDate().toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const year = date.getFullYear(); // Lấy đầy đủ 4 chữ số của năm
  return `${hours}:${minutes} ${ampm} <br>${day}/${month}/${year}`;
};

// Định dạng thời gian theo yêu cầu: phút:giờ (12 giờ)
export const formatDateToMessage = (date) => {
  const minutes = date.getMinutes().toString().padStart(2, '0');
  let hours = date.getHours();
  const ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12;
  hours = hours ? hours : 12; // Nếu là 0 giờ thì hiển thị là 12
  return `${hours}:${minutes} ${ampm}`;
};
