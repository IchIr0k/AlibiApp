import smtplib
from email.mime.text import MIMEText

# ============================================
# НАСТРОЙКИ MAIL.RU
# ============================================
SMTP_SERVER = "smtp.mail.ru"
SMTP_PORT = 587
SMTP_USER = "alibi.quest@mail.ru"
SMTP_PASSWORD = "fweKmiKIGYDiYKba1y8p"
FROM_EMAIL = "alibi.quest@mail.ru"
FROM_NAME = "Алиби - Квесты"


def send_booking_confirmation(user_email: str, user_name: str, quest_title: str,
                              booking_date: str, booking_time: str, address: str,
                              prepayment: int, total_price: int):
    """Отправляет подтверждение бронирования на email"""

    print(f"📧 Попытка отправки email на {user_email}...")

    # Максимально простые заголовки
    subject = "Booking confirmation"

    # Текст письма - минимальный
    text_content = f"""Booking confirmation for {quest_title}

Hello {user_name},

Your booking is confirmed.

Date: {booking_date}
Time: {booking_time}
Address: {address}
Prepayment: {prepayment} RUB

Please arrive 15 minutes before start.

Thank you,
Alibi Team
"""

    msg = MIMEText(text_content, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = user_email

    try:
        print(f"🔌 Connecting to {SMTP_SERVER}:{SMTP_PORT}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        print(f"🔐 Logging in as {SMTP_USER}...")
        server.login(SMTP_USER, SMTP_PASSWORD)
        print(f"📤 Sending email to {user_email}...")
        server.sendmail(FROM_EMAIL, [user_email], msg.as_string())
        server.quit()
        print(f"✅ Email sent successfully to {user_email}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def send_booking_cancellation(user_email: str, user_name: str, quest_title: str,
                              booking_date: str, booking_time: str):
    """Отправляет уведомление об отмене бронирования"""

    subject = "Booking cancelled"

    text_content = f"""Booking cancelled for {quest_title}

Hello {user_name},

Your booking has been cancelled.

Date: {booking_date}
Time: {booking_time}

Please contact us if you have any questions.

Thank you,
Alibi Team
"""

    msg = MIMEText(text_content, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = user_email

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(FROM_EMAIL, [user_email], msg.as_string())
        server.quit()
        print(f"✅ Cancellation email sent to {user_email}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

