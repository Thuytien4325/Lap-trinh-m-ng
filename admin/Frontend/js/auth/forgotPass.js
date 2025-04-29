import { toast } from '../untils.js';
import config from '../config.js';

document.addEventListener('DOMContentLoaded', () => {
  const forgotForm = document.querySelector('form');
  const emailField = document.getElementById('email');
  const forgotError = document.getElementById('forgotError');

  let canSubmit = true;
  let submitAttempts = 0;
  const maxSubmitAttempts = 2;
  const attemptTimeFrame = 5000;

  if (forgotForm) {
    forgotForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const submitButton = document.querySelector('.submit-btn');

      if (submitAttempts >= maxSubmitAttempts) {
        toast({
          title: 'Quá tải',
          message: 'Bạn đã nhấn quá nhiều lần. Vui lòng thử lại sau.',
          type: 'warning',
        });
        return;
      }

      if (!canSubmit) return;
      canSubmit = false;
      submitAttempts++;
      submitButton.disabled = true;

      const email = emailField.value.trim();

      if (!email) {
        forgotError.textContent = 'Vui lòng nhập email!';
        canSubmit = true;
        submitButton.disabled = false;
        return;
      }

      try {
        console.log('Base URL:', config.baseURL);
        console.log(
          'Gửi tới:',
          `${config.baseURL}/auth/password/reset-request?email=${encodeURIComponent(email)}&base_url=${encodeURIComponent(config.baseURL)}`
        );

        const response = await fetch(
          `${config.baseURL}/auth/password/reset-request?email=${encodeURIComponent(email)}&base_url=${encodeURIComponent(config.baseURL)}`,
          {
            method: 'POST',
            headers: {
              Accept: 'application/json',
            },
            body: '',
          }
        );

        const result = await response.json();

        if (response.ok && result.message) {
          toast({
            title: 'Thành công',
            message: result.message,
            type: 'success',
          });
        } else {
          forgotError.textContent = result.detail || 'Có lỗi xảy ra.';
          toast({
            title: 'Lỗi',
            message: result.detail || 'Có lỗi xảy ra. Thử lại sau.',
            type: 'error',
          });
        }
      } catch (error) {
        forgotError.textContent = 'Không thể kết nối đến máy chủ. Thử lại sau.';
        toast({
          title: 'Lỗi',
          message: 'Không thể kết nối đến máy chủ. Thử lại sau.',
          type: 'error',
        });
      }

      setTimeout(() => {
        canSubmit = true;
        submitButton.disabled = false;
      }, 1000);

      setTimeout(() => {
        submitAttempts = 0;
      }, attemptTimeFrame);
    });
  }
});
