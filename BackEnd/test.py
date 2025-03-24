import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_reset_email(to_email: str, reset_link: str):
    subject = "Reset your password"
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg["Subject"] = subject

    email_content = f"""
    <html>
    <body>
        <h2>Password Reset</h2>
        <p>Click the link below to reset your password:</p>
        <a href="{reset_link}">{reset_link}</a>
    </body>
    </html>
    """
    msg.attach(MIMEText(email_content, "html"))

    try:
        print("📨 Đang kết nối SMTP...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.set_debuglevel(1)  # Hiển thị log debug
            server.starttls()
            print("✅ Kết nối thành công, đang đăng nhập...")

            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            print("✅ Đăng nhập SMTP thành công!")

            server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
            print(f"📧 Email đã gửi đến {to_email}")

    except Exception as e:
        print("❌ Lỗi khi gửi email:", e)

# ---- GỌI HÀM TEST ----
test_email = "mmy48531@jioso.com"
test_reset_link = "https://yourapp.com/reset-password?token=123456"

send_reset_email(test_email, test_reset_link)
