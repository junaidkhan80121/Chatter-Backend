"""
Notification background tasks.
"""
from app.tasks.celery_app import celery_app


@celery_app.task(name="tasks.send_notification")
def send_notification(user_id: str, notification_type: str, title: str, body: str, data: dict = None):
    """Send a push notification to a user (stub for future integration)."""
    print(f"[Celery] Sending notification to {user_id}: {title}")
    # TODO: Integrate with Firebase FCM or similar
    return {"status": "sent", "user_id": user_id}


@celery_app.task(name="tasks.send_email")
def send_email(to: str, subject: str, body: str):
    """Send an email notification."""
    import smtplib
    from email.message import EmailMessage
    from app.core.config import settings

    if not settings.SMTP_USER:
        print(f"[Celery] Email skipped (no SMTP config): {to}")
        return {"status": "skipped"}

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return {"status": "sent", "to": to}
    except Exception as e:
        print(f"[Celery] Email error: {e}")
        return {"status": "error", "error": str(e)}
