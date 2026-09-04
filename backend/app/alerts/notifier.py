"""
Owner: Integration (alert delivery)

Goal:
Consume `alert` messages (docs/schema.md) and deliver them:
  - SMS via Twilio (TWILIO_* env vars)
  - Email via SendGrid (SENDGRID_API_KEY, ALERT_EMAIL_* env vars)
"""
from __future__ import annotations

import logging
import os

from app import config

logger = logging.getLogger("ibvap.alerts")


def send_alert(alert: dict) -> None:
    """
    Args:
        alert: an `alert` message dict matching docs/schema.md
    """
    severity = alert.get("severity", "medium").upper()
    obj_class = alert.get("class", "object")
    location = alert.get("location", "Perimeter")
    timestamp = alert.get("timestamp", "")
    message_text = alert.get("message", f"{obj_class.capitalize()} detected at {location}")

    formatted_sms = f"[IBVAP ALERT] {severity} - {obj_class} detected at {location}, {timestamp}"
    logger.info("Triggered alert dispatch: %s", formatted_sms)

    # 1. Twilio SMS
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from = os.getenv("TWILIO_FROM_NUMBER")
    alert_to = os.getenv("ALERT_SMS_TO")

    if twilio_sid and twilio_token and twilio_from and alert_to:
        try:
            from twilio.rest import Client
            client = Client(twilio_sid, twilio_token)
            client.messages.create(body=formatted_sms, from_=twilio_from, to=alert_to)
            logger.info("Twilio SMS sent to %s", alert_to)
        except Exception as e:
            logger.error("Failed to send Twilio SMS: %s", e)
    else:
        logger.debug("Twilio SMS credentials not configured. Skipping SMS.")

    # 2. SendGrid Email
    sendgrid_key = os.getenv("SENDGRID_API_KEY")
    email_from = os.getenv("ALERT_EMAIL_FROM")
    email_to = os.getenv("ALERT_EMAIL_TO")

    if sendgrid_key and email_from and email_to:
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            email = Mail(
                from_email=email_from,
                to_emails=email_to,
                subject=f"[IBVAP ALERT] {severity} Perimeter Breach",
                html_content=f"<strong>{formatted_sms}</strong><p>{message_text}</p>",
            )
            sg = SendGridAPIClient(sendgrid_key)
            sg.send(email)
            logger.info("SendGrid Email sent to %s", email_to)
        except Exception as e:
            logger.error("Failed to send SendGrid Email: %s", e)
    else:
        logger.debug("SendGrid credentials not configured. Skipping email.")
